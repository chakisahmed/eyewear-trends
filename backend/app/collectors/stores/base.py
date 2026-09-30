"""Generic, config-driven store crawler: fetch listing (and optionally product) pages, return products.

One class for every retailer: what to extract comes from store_configs.yaml, never from per-store
code. The crawler has no database and no LLM access; it only returns list[ScrapedProduct], which
StoreSyncService (service.py) persists. `crawler.report` (a CrawlReport) says what the listings returned and
whether they may be incomplete, which is what lets the sync tell "gone from the catalog" from "not seen this time".
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any
from urllib import robotparser
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from app.collectors.stores.config import Facet, ListingUrl, ScraperConfig
from app.collectors.stores.parser import (
    ListingItem, facet_values, merge, model_key, next_page_url, parse_listing, parse_product_page,
)
from app.collectors.stores.schemas import CrawlReport, FacetGap, ScrapedProduct, db_url_of
from app.config import settings

log = logging.getLogger(__name__)


def with_query(url: str, **params: Any) -> str:
    """url with params set. Spaces become %20, never "+": robots.txt files forbid "+" in collection URLs (Shopify)."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query)) | {k: str(v) for k, v in params.items()}
    return urlunsplit(parts._replace(query=urlencode(query, quote_via=quote)))


def add_label(target: dict[str, Any], key: str, label: str) -> None:
    """target[key] = label, or ", "-joined onto the labels already there ("Man, Woman"), without repeats."""
    have = target.get(key)
    if not have:
        target[key] = label
    elif label not in have.split(", "):
        target[key] = f"{have}, {label}"


class BaseStoreCrawler:
    """Crawl one store as described by its ScraperConfig.

    Use as `async with BaseStoreCrawler(cfg) as crawler: products = await crawler.crawl()`. An injected
    client (tests, shared pools) is used as-is and not closed; the default one is created with the
    project User-Agent and timeout and closed on exit.

    A page that fails for a transient reason (a timeout or connection error, HTTP 429, 500, 502, 503, 504) is retried
    RETRIES times after RETRY_DELAYS seconds (a Retry-After header wins, capped): stores have slow moments. A real
    answer (404, 403, a robots.txt refusal) is never retried.
    """

    RETRIES = 2
    RETRY_DELAYS = (5.0, 15.0)
    RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
    MAX_RETRY_AFTER = 60.0

    def __init__(self, config: ScraperConfig, client: httpx.AsyncClient | None = None):
        self.config = config
        self.delay_s = config.delay_s
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=httpx.Timeout(settings.request_timeout),
            follow_redirects=True,
        )
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}
        self._requests = 0
        self.report = CrawlReport()

    async def __aenter__(self) -> BaseStoreCrawler:
        return self

    async def __aexit__(self, *exc) -> None:
        if self._owns_client:
            await self.client.aclose()

    # --- HTTP ----------------------------------------------------------------------------------------

    async def allowed(self, url: str) -> bool:
        """robots.txt check, cached per origin. Same rules as collectors/base.allowed_by_robots:
        a missing (4xx) or unreachable robots.txt allows crawling."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            rp: robotparser.RobotFileParser | None = None
            try:
                r = await self.client.get(f"{origin}/robots.txt")
                if r.status_code < 400:
                    rp = robotparser.RobotFileParser()
                    rp.parse(r.text.splitlines())
            except httpx.HTTPError:
                rp = None
            self._robots[origin] = rp
        rp = self._robots[origin]
        return rp is None or rp.can_fetch(self.client.headers.get("User-Agent", settings.user_agent), url)

    def _retry_wait(self, e: httpx.HTTPError, attempt: int) -> float | None:
        """Seconds to wait before retrying after `e`, or None when it is not worth retrying (or retries are used up)."""
        if attempt >= self.RETRIES:
            return None
        delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)] if self.RETRY_DELAYS else 0.0
        if isinstance(e, httpx.TransportError):
            return delay
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in self.RETRY_STATUSES:
            try:  # a store that says how long to wait is asked politely
                return min(float(e.response.headers["Retry-After"]), self.MAX_RETRY_AFTER)
            except (KeyError, ValueError):
                return delay
        return None

    async def fetch(self, url: str) -> str | None:
        """GET a page if robots.txt allows it. None if blocked or failed for good (logged, never raised)."""
        if not await self.allowed(url):
            log.info("robots.txt disallows %s", url)
            return None
        if self._requests and self.delay_s:
            await asyncio.sleep(self.delay_s)
        self._requests += 1
        attempt = 0
        while True:
            try:
                r = await self.client.get(url)
                r.raise_for_status()
                return r.text
            except httpx.HTTPError as e:
                what = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__  # httpx timeouts have no message
                wait = self._retry_wait(e, attempt)
                if wait is None:
                    log.info("Fetch failed %s: %s", url, what)
                    return None
                attempt += 1
                log.info("Fetch failed %s: %s; retry %d/%d in %.0f s", url, what, attempt, self.RETRIES, wait)
                await asyncio.sleep(wait)

    # --- crawl ---------------------------------------------------------------------------------------

    async def listing_pages(self, first_url: str) -> AsyncIterator[tuple[int, str, str | None]]:
        """(page number, url, html or None if blocked / failed) for each listing page, following the pagination."""
        pagination = self.config.listing.pagination
        max_pages = pagination.max_pages if pagination else 1
        url = first_url
        for page in range(1, max_pages + 1):
            html = await self.fetch(url)
            yield page, url, html
            if not pagination or page == max_pages:
                return
            if pagination.param:
                url = with_query(first_url, **{pagination.param: page + 1})
            else:
                url = next_page_url(html, url, pagination.next) if html is not None else None
                if url is None:
                    return

    async def listing_items(self) -> list[ListingItem]:
        cfg, items, report = self.config, [], self.report
        by_url: dict[str, ListingItem] = {}
        seen_models: set[str] = set()  # model keys kept so far (ListingRule.model_regex)
        pagination = cfg.listing.pagination
        max_pages = pagination.max_pages if pagination else 1
        via_next = pagination is not None and pagination.param is None  # pages are reached by following links
        flag_listings = [u for u in cfg.listing.urls if isinstance(u, ListingUrl) and u.flag]
        for entry in (u for u in cfg.listing.urls if u not in flag_listings):
            start, category = (entry.url, entry.categories) if isinstance(entry, ListingUrl) else (entry, None)
            first_url, first_html, listed = urljoin(str(cfg.base_url), start), None, set()
            last: tuple[int, str, str, int] | None = None  # page, url, html, products found: the last page read
            async with aclosing(self.listing_pages(first_url)) as pages:
                async for page, url, html in pages:
                    if html is None:
                        report.problems.append(f"{start} page {page}: not fetched")
                    else:
                        first_html = first_html or (html if page == 1 else None)
                        found = parse_listing(html, url, cfg, start_rank=len(items) + 1)
                        if not found and page > 1:
                            if via_next:  # a link led here: an empty page is a soft block or a changed layout
                                report.problems.append(f"{start} page {page}: listed nothing")
                            break  # past the last page
                        if not found:
                            report.problems.append(f"{start}: first page listed nothing")
                        last = (page, url, html, len(found))
                        for item in found:
                            if stored := db_url_of(item.url):
                                report.listed.add(stored)  # on the shelf, kept or not
                            key = model_key(item.url, cfg.listing.model_regex)
                            if key is not None and item.url not in by_url and key in seen_models:
                                continue  # another size of a model already kept: not fetched, not stored, never dropped
                            if key is not None:
                                seen_models.add(key)
                            listed.add(item.url)
                            if item.url not in by_url:
                                by_url[item.url] = item
                                item.rank = len(items) + 1
                                items.append(item)
                            if category:
                                add_label(by_url[item.url].flags, "categories", category)
                    log.info("%s: listing %s page %d (max %d), %d products so far", cfg.name, start, page, max_pages, len(items))
            # The last allowed page still lists products and more may follow: the catalog may be longer than we read.
            # (With ?param= pagination there is no link to check, so a listing that fills max_pages counts as cut off.)
            if last and pagination and last[0] == max_pages and last[3] and (
                    pagination.param or (pagination.next and next_page_url(last[2], last[1], pagination.next))):
                report.problems.append(f"{start}: stopped at max_pages ({max_pages}) with more to list")
            for facet in cfg.listing.facets if first_html is not None else ():
                await self.facet_pass(facet, first_url, first_html, by_url, listed)
        for entry in flag_listings:  # after the main listings: they only flag what those found
            await self.flag_pass(entry, by_url)
        return items

    async def flag_pass(self, entry: ListingUrl, by_url: dict[str, ListingItem]) -> None:
        """Set flags[entry.flag] = True on every product the listing shares with the main ones. Enrichment only: a
        product found only here is ignored (no product, not on the shelf), so nothing depends on it for presence. A page
        that cannot be fetched is a FacetGap: the crawl is retried and the sync keeps the flags it already had."""
        cfg = self.config
        first_url, failed_url = urljoin(str(cfg.base_url), entry.url), None
        async with aclosing(self.listing_pages(first_url)) as pages:
            async for page, url, html in pages:
                if html is None:
                    failed_url = failed_url or url
                    continue
                found = parse_listing(html, url, cfg)
                if not found and page > 1:
                    break
                for item in found:
                    if item.url in by_url:
                        by_url[item.url].flags[entry.flag] = True
        if failed_url:
            self.report.gaps.append(FacetGap(entry.flag, "list", entry.flag, False, failed_url))
        log.info("%s: flag listing %s: %s set on %d products", cfg.name, entry.url, entry.flag,
                 sum(1 for i in by_url.values() if i.flags.get(entry.flag)))

    async def facet_pass(self, facet: Facet, first_url: str, first_html: str, by_url: dict[str, ListingItem],
                         listed: set[str]) -> None:
        """List the collection once per value of one store filter and record the value's label in the raw_specs of
        every product listed under it, or with `facet.flag` set that flag (e.g. is_bestseller). One filter per
        request, never combined. Products the plain listing did not return are ignored: the listing stays the only
        source of products. `listed`: this collection's products, the only ones a flag pass may mark False."""
        cfg = self.config
        flagged, complete = set(), True
        for value, label in facet_values(first_html, facet.param):
            if facet.only is not None and label not in facet.only:
                continue  # never requested
            matched, failed_url = 0, None
            async with aclosing(self.listing_pages(with_query(first_url, **{facet.param: value}))) as pages:
                async for page, url, html in pages:
                    if html is None:
                        complete = False  # blocked or failed: products not listed here are unknown, not "no"
                        failed_url = failed_url or url
                    found = parse_listing(html, url, cfg) if html is not None else []
                    if not found and page > 1:
                        break
                    for item in found:
                        if item.url not in by_url:
                            continue
                        matched += 1
                        if facet.flag:
                            by_url[item.url].flags[facet.flag] = True
                            flagged.add(item.url)
                        else:
                            add_label(by_url[item.url].flags.setdefault("raw_specs", {}), facet.name, label)
                        if facet.per_variant and item.variant_id:  # the variant this label matched
                            by_url[item.url].flags.setdefault("variant_colors", {}).setdefault(item.variant_id, label)
            if failed_url:  # the crawl is incomplete for this label: the sync keeps what it knew, the run is retried
                self.report.gaps.append(FacetGap(facet.name, label, facet.flag, facet.per_variant, failed_url))
            log.info("%s: facet %s = %s, %d products", cfg.name, facet.name, label, matched)
        if facet.flag and complete:
            for url in listed - flagged:
                by_url[url].flags.setdefault(facet.flag, False)
        elif facet.flag:
            log.info("%s: facet %s incomplete, %s left unset on unlisted products", cfg.name, facet.name, facet.flag)

    def postprocess(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Hook for the rare store that needs a code tweak; the default does nothing."""
        return fields

    async def crawl(self) -> list[ScrapedProduct]:
        cfg = self.config
        self.report = CrawlReport()
        items = await self.listing_items()
        pages = {}
        if cfg.product_pages.enabled:
            todo = items[: cfg.product_pages.max_products]
            log.info("%s: %d products listed, opening %d product pages (~%d min)",
                     cfg.name, len(items), len(todo), round(len(todo) * self.delay_s / 60) or 1)
            for n, item in enumerate(todo, start=1):
                html = await self.fetch(item.url)
                if html is not None:
                    pages[item.url] = parse_product_page(html, item.url, cfg)
                if n % 10 == 0 or n == len(todo):
                    log.info("%s: product pages %d/%d", cfg.name, n, len(todo))
        products = []
        for item in items:
            page = pages.get(item.url)
            layers = [page.json_ld, item.json_ld, page.css, item.css] if page else [item.json_ld, item.css]
            fields = merge(*layers, default_currency=cfg.default_currency, default_brand=cfg.default_brand)
            flags = item.flags | (page.flags if page else {})
            # raw_specs from the listing (facets) and from the product page are merged, the page winning per label
            specs = item.flags.get("raw_specs", {}) | (page.flags.get("raw_specs", {}) if page else {})
            if specs:
                flags["raw_specs"] = specs
            # per-variant labels from a variant-level filter reach the variant with that id; the join map is dropped
            variant_colors = flags.pop("variant_colors", None) or {}
            if variant_colors and isinstance(flags.get("variants"), list):
                flags["variants"] = [v | {"color": variant_colors[str(v["id"])]}
                                     if isinstance(v, dict) and "color" not in v and str(v.get("id")) in variant_colors else v
                                     for v in flags["variants"]]
            if cfg.name_strip and fields.get("name"):
                fields["name"] = re.sub(cfg.name_strip, "", fields["name"]).strip() or fields["name"]
            fields = self.postprocess({**fields, "url": item.url, "rank": item.rank, "flags": flags or None})
            try:
                products.append(ScrapedProduct(**fields))
            except ValidationError as e:
                log.info("%s: dropped %s (%d errors: %s)", cfg.domain, item.url, e.error_count(),
                         "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()))
        log.info("%s: %d valid products, %d dropped", cfg.name, len(products), len(items) - len(products))
        return products
