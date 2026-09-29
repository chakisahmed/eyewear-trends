"""Generic, config-driven store crawler: fetch listing (and optionally product) pages, return products.

One class for every retailer: what to extract comes from store_configs.yaml, never from per-store
code. The crawler has no database and no LLM access; it only returns list[ScrapedProduct], which
StoreSyncService (service.py) persists.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any
from urllib import robotparser
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from app.collectors.stores.config import Facet, ListingUrl, ScraperConfig
from app.collectors.stores.parser import (
    ListingItem, facet_values, merge, next_page_url, parse_listing, parse_product_page,
)
from app.collectors.stores.schemas import ScrapedProduct
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
    """

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

    async def fetch(self, url: str) -> str | None:
        """GET a page if robots.txt allows it. None if blocked or failed (logged, never raised)."""
        if not await self.allowed(url):
            log.info("robots.txt disallows %s", url)
            return None
        if self._requests and self.delay_s:
            await asyncio.sleep(self.delay_s)
        self._requests += 1
        try:
            r = await self.client.get(url)
            r.raise_for_status()
        except httpx.HTTPError as e:
            log.info("Fetch failed %s: %s", url, e)
            return None
        return r.text

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
        cfg, items = self.config, []
        by_url: dict[str, ListingItem] = {}
        max_pages = cfg.listing.pagination.max_pages if cfg.listing.pagination else 1
        for entry in cfg.listing.urls:
            start, category = (entry.url, entry.categories) if isinstance(entry, ListingUrl) else (entry, None)
            first_url, first_html, listed = urljoin(str(cfg.base_url), start), None, set()
            async with aclosing(self.listing_pages(first_url)) as pages:
                async for page, url, html in pages:
                    if html is not None:
                        first_html = first_html or (html if page == 1 else None)
                        found = parse_listing(html, url, cfg, start_rank=len(items) + 1)
                        if not found and page > 1:
                            break  # past the last page
                        for item in found:
                            listed.add(item.url)
                            if item.url not in by_url:
                                by_url[item.url] = item
                                item.rank = len(items) + 1
                                items.append(item)
                            if category:
                                add_label(by_url[item.url].flags, "categories", category)
                    log.info("%s: listing %s page %d (max %d), %d products so far", cfg.name, start, page, max_pages, len(items))
            for facet in cfg.listing.facets if first_html is not None else ():
                await self.facet_pass(facet, first_url, first_html, by_url, listed)
        return items

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
            matched = 0
            async with aclosing(self.listing_pages(with_query(first_url, **{facet.param: value}))) as pages:
                async for page, url, html in pages:
                    if html is None:
                        complete = False  # blocked or failed: products not listed here are unknown, not "no"
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
            fields = self.postprocess({**fields, "url": item.url, "rank": item.rank, "flags": flags or None})
            try:
                products.append(ScrapedProduct(**fields))
            except ValidationError as e:
                log.info("%s: dropped %s (%d errors: %s)", cfg.domain, item.url, e.error_count(),
                         "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()))
        log.info("%s: %d valid products, %d dropped", cfg.name, len(products), len(items) - len(products))
        return products
