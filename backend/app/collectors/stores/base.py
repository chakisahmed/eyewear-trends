"""Generic, config-driven store crawler: fetch listing (and optionally product) pages, return products.

One class for every retailer: what to extract comes from store_configs.yaml, never from per-store
code. The crawler has no database and no LLM access; it only returns list[ScrapedProduct], which
StoreSyncService (service.py) persists.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib import robotparser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from app.collectors.stores.config import ScraperConfig
from app.collectors.stores.parser import ListingItem, merge, next_page_url, parse_listing, parse_product_page
from app.collectors.stores.schemas import ScrapedProduct
from app.config import settings

log = logging.getLogger(__name__)


def with_query(url: str, **params: Any) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query)) | {k: str(v) for k, v in params.items()}
    return urlunsplit(parts._replace(query=urlencode(query)))


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

    async def listing_items(self) -> list[ListingItem]:
        cfg, items, seen = self.config, [], set()
        pagination = cfg.listing.pagination
        max_pages = pagination.max_pages if pagination else 1
        for start in cfg.listing.urls:
            url: str | None = urljoin(str(cfg.base_url), start)
            first_url = url
            for page in range(1, max_pages + 1):
                html = await self.fetch(url)
                if html is not None:
                    found = parse_listing(html, url, cfg, start_rank=len(items) + 1)
                    if not found and page > 1:
                        break  # past the last page
                    for item in found:
                        if item.url not in seen:
                            seen.add(item.url)
                            item.rank = len(items) + 1
                            items.append(item)
                if not pagination or page == max_pages:
                    break
                if pagination.param:
                    url = with_query(first_url, **{pagination.param: page + 1})
                else:
                    url = next_page_url(html, url, pagination.next) if html is not None else None
                    if url is None:
                        break
        return items

    def postprocess(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Hook for the rare store that needs a code tweak; the default does nothing."""
        return fields

    async def crawl(self) -> list[ScrapedProduct]:
        cfg = self.config
        items = await self.listing_items()
        pages = {}
        if cfg.product_pages.enabled:
            for item in items[: cfg.product_pages.max_products]:
                html = await self.fetch(item.url)
                if html is not None:
                    pages[item.url] = parse_product_page(html, item.url, cfg)
        products = []
        for item in items:
            page = pages.get(item.url)
            layers = [page.json_ld, item.json_ld, page.css, item.css] if page else [item.json_ld, item.css]
            fields = merge(*layers, default_currency=cfg.default_currency)
            flags = item.flags | (page.flags if page else {})
            fields = self.postprocess({**fields, "url": item.url, "rank": item.rank, "flags": flags or None})
            try:
                products.append(ScrapedProduct(**fields))
            except ValidationError as e:
                log.info("%s: dropped %s (%d errors: %s)", cfg.domain, item.url, e.error_count(),
                         "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()))
        return products
