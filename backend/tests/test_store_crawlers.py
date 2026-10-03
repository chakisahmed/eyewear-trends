"""Phase 2 store crawling: contract, YAML config, JSON-LD-first parsing, async crawler, sync service.

Offline only: every HTTP call goes through httpx.MockTransport against a fake shop (shop.test).
"""

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select

import app.collectors.stores as stores_pkg
from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import config_for, parse_store_configs
from app.collectors.stores.parser import parse_listing, parse_price, parse_product_page
from app.collectors.stores.schemas import CrawlReport, ScrapedProduct, db_url_of
from app.collectors.stores.service import StoreSyncService
from app.db import SessionLocal, init_db
from app.models import Product, Source

STORES_DIR = Path(stores_pkg.__file__).parent
BASE = "https://www.shop.test"

CONFIG_YAML = """
stores:
  www.shop.test:
    name: Shop Test
    base_url: https://www.shop.test
    lang: fr
    country: TN
    default_currency: TND
    listing:
      urls: ["/lunettes"]
      pagination: {param: page, max_pages: 3}
      product: "li.card"
      link: "a.card-link"
    product_pages: {enabled: true, max_products: 2}
    fields:
      name: {css: ".card-title"}
      brand: {css: ".card-brand"}
      price: {css: ".card-price"}
      image_url: {css: "img", attr: ["data-src", "src"]}
    flags:
      is_bestseller: {css: ".badge-best", exists: true}
      material: {css: ".material", scope: page}
    specs: {rows: ".specs tr", key: "th", value: "td"}
"""


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def cfg():
    return parse_store_configs(CONFIG_YAML)["shop.test"]


def json_ld(data) -> str:
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def card(slug, *, title=None, brand=None, price=None, best=False, img=None) -> str:
    return (
        f'<li class="card"><a class="card-link" href="/p/{slug}">'
        + (f'<img data-src="{img}" src="/placeholder.gif">' if img else "")
        + (f'<h3 class="card-title">{title}</h3>' if title else "")
        + (f'<span class="card-brand">{brand}</span>' if brand else "")
        + (f'<span class="card-price">{price}</span>' if price else "")
        + ('<span class="badge-best">Best-seller</span>' if best else "")
        + "</a></li>"
    )


# --- contract --------------------------------------------------------------------------------------

def test_contract_normalises_and_validates():
    p = ScrapedProduct(url="https://shop.test/p/a", name="  " + "x" * 400, brand="  ", currency="tnd",
                       seen_at=datetime(2026, 9, 1, 12, 0))
    assert len(p.name) == 300 and p.brand is None and p.currency == "TND"
    assert p.seen_at.tzinfo is not None and p.seen_at.utcoffset() == timedelta(0)
    assert p.db_url() == "https://shop.test/p/a"
    for bad in ({"currency": "DINAR"}, {"price": -1}, {"rank": 0}, {"unknown": 1}, {"flags": {"x": object()}},
                {"url": "https://shop.test/" + "a" * 1000}, {"name": "   "}):
        with pytest.raises(ValidationError):
            ScrapedProduct(**{"url": "https://shop.test/p/a", "name": "A", **bad})


# --- config ----------------------------------------------------------------------------------------

def test_config_loads_and_resolves_domains(cfg):
    assert cfg.domain == "shop.test" and cfg.lang == "fr" and cfg.default_currency == "TND"
    configs = parse_store_configs(CONFIG_YAML)
    assert config_for("https://www.shop.test/p/a", configs) is configs["shop.test"]
    assert config_for("shop.test", configs) is configs["shop.test"]
    with pytest.raises(KeyError):
        config_for("other.test", configs)


def test_shipped_config_has_the_fourteen_stores():
    from app.collectors.stores.config import load_store_configs
    configs = load_store_configs()
    assert list(configs) == ["outika-eyewear.tn", "mykenza.tn", "lamode.tn", "etniabarcelona.com", "morel.com", "bartonperreira.com", "cubitts.com", "dita.com", "ebmeyrowitz.com", "anneetvalentin.com", "faceaface-paris.com", "kuboraum.com", "lafont.com", "cutlerandgross.com"]
    assert [c.country for c in configs.values()] == ["TN", "TN", "TN", "ES", "FR", "US", "GB", "US", "GB", "FR", "FR", "DE", "FR", "GB"]  # brand catalogs are not a Tunisian shelf
    outika = configs["outika-eyewear.tn"]
    assert outika.product_pages.enabled and outika.listing.pagination.next  # price is product-page only; path paging
    assert configs["mykenza.tn"].listing.pagination.max_pages == 20         # 10 cut both categories (first live crawl)
    assert all(c.crawl_every_days == 7 for c in configs.values())


def test_default_brand_applies_only_when_no_source_has_one():
    from app.collectors.stores.parser import merge
    assert merge({"brand": "Persol"}, {}, default_brand="Outika")["brand"] == "Persol"
    assert merge({}, {"brand": "Ray-Ban"}, default_brand="Outika")["brand"] == "Ray-Ban"
    assert merge({}, {}, default_brand="Outika")["brand"] == "Outika"
    assert merge({}, {})["brand"] is None


def test_non_positive_price_counts_as_missing():
    from app.collectors.stores.parser import merge
    assert merge({"price": 0.0}, {"price": 45.0})["price"] == 45.0   # JSON-LD 0 falls through to CSS
    assert merge({"price": 0.0}, {})["price"] is None
    assert merge({}, {"price": -5.0})["price"] is None
    assert merge({"price": 49.0}, {"price": 45.0})["price"] == 49.0  # a real JSON-LD price still wins


@pytest.mark.parametrize("patch", [
    ('"li.card"', '"li.card[["'),              # invalid CSS
    ('"li.card"', '"//li[@class=\'card\']"'),  # XPath is refused
    ('"a.card-link"', '"/html/body//a"'),      # XPath is refused
    ("{param: page, max_pages: 3}", "{param: page, next: 'a[rel=next]'}"),  # both pagination modes
    ("    lang: fr", "    lang: fr\n    colour: red"),                       # unknown key
    ("{css: \".card-title\"}", "{css: \".card-title\", regex: \"(unclosed\"}"),  # bad regex
])
def test_config_rejects_bad_rules_at_load_time(patch):
    old, new = patch
    with pytest.raises(ValueError, match="shop.test"):
        parse_store_configs(CONFIG_YAML.replace(old, new, 1))


# --- pure parsing ----------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("1 234,50 DT", (1234.5, "TND")),
    ("89,000 TND", (89.0, "TND")),
    ("189 DT", (189.0, "TND")),
    ("€89.90", (89.9, "EUR")),
    ("1.234,50 €", (1234.5, "EUR")),
    ("1,234.50 USD", (1234.5, "USD")),
    ("1 290,000 DT", (1290.0, "TND")),
    ("Prix sur demande", (None, None)),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_listing_json_ld_wins_and_css_fills_gaps(cfg):
    html = (
        "<ul>"
        + card("a", title="Card title A", brand="Ray-Ban", price="99,000 DT")
        + card("b", title="Monture B", brand="Oakley", price="89,500 DT", best=True, img="/img/b.jpg")
        + "</ul>"
        + json_ld({"@context": "https://schema.org", "@graph": [
            {"@type": "Product", "name": "JSON-LD A", "url": f"{BASE}/p/a",
             "offers": {"@type": "Offer", "price": "120.000", "priceCurrency": "TND"}},
        ]})
    )
    items = {i.url: i for i in parse_listing(html, f"{BASE}/lunettes", cfg, start_rank=1)}
    a, b = items[f"{BASE}/p/a"], items[f"{BASE}/p/b"]
    assert (a.rank, b.rank) == (1, 2)
    assert a.json_ld == {"name": "JSON-LD A", "price": 120.0, "currency": "TND", "url": f"{BASE}/p/a"}
    assert a.css["brand"] == "Ray-Ban" and a.css["price"] == 99.0                 # CSS kept only as a fallback layer
    assert b.json_ld == {} and b.css["image_url"] == f"{BASE}/img/b.jpg"         # data-src before src, made absolute
    assert b.flags == {"is_bestseller": True} and a.flags == {"is_bestseller": False}


def test_product_page_reads_json_ld_specs_and_page_flags(cfg):
    html = (
        json_ld({"@type": ["Product"], "name": "Persol 714", "brand": {"@type": "Brand", "name": "Persol"},
                 "image": [{"@type": "ImageObject", "url": "/img/714.jpg"}],
                 "offers": [{"@type": "AggregateOffer", "lowPrice": 450, "priceCurrency": "EUR"}]})
        + '<p class="material">Acétate</p><table class="specs"><tr><th>Forme</th><td>Pilote</td></tr>'
          '<tr><th>Calibre</th><td>52</td></tr></table>'
    )
    page = parse_product_page(html, f"{BASE}/p/a", cfg)
    assert page.json_ld == {"name": "Persol 714", "brand": "Persol", "price": 450.0, "currency": "EUR",
                            "image_url": f"{BASE}/img/714.jpg"}
    assert page.flags == {"material": "Acétate", "raw_specs": {"Forme": "Pilote", "Calibre": "52"}}


# --- crawler (async, MockTransport) ----------------------------------------------------------------

def fake_shop(requests: list[httpx.Request]) -> httpx.MockTransport:
    pages = {
        "/robots.txt": "User-agent: *\nDisallow: /blocked\n",
        "/lunettes": "<ul>" + card("a", title="Card A", brand="Ray-Ban", price="99,000 DT")
                     + card("b", title="Monture B", brand="Oakley", price="89,500 DT", best=True) + "</ul>"
                     + json_ld({"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": 1, "item": {
                         "@type": "Product", "name": "Listing A", "url": f"{BASE}/p/a",
                         "offers": {"price": 120, "priceCurrency": "TND"}}}]}),
        "/lunettes?page=2": "<ul>" + card("c", title="Monture C", price="75 DT")
                            + '<li class="card"><a class="card-link" href="/blocked/d">'
                              '<h3 class="card-title">Monture D</h3></a></li>'
                            + card("nameless", price="10 DT") + "</ul>",
        "/p/a": json_ld({"@type": "Product", "name": "Persol 714", "brand": {"name": "Persol"},
                         "offers": {"price": "150.000", "priceCurrency": "TND"}}),
        "/p/b": '<p class="material">Métal</p><table class="specs"><tr><th>Forme</th><td>Ronde</td></tr></table>',
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.raw_path.decode()
        if path == "/lunettes?page=3":
            return httpx.Response(500)
        body = pages.get(path)
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_crawl_end_to_end(cfg):
    requests: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=fake_shop(requests), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = await crawler.crawl()

    got = {p.db_url(): p for p in products}
    paths = [r.url.raw_path.decode() for r in requests]
    assert set(got) == {f"{BASE}/p/a", f"{BASE}/p/b", f"{BASE}/p/c", f"{BASE}/blocked/d"}  # nameless card dropped
    assert [got[u].rank for u in (f"{BASE}/p/a", f"{BASE}/p/b", f"{BASE}/p/c", f"{BASE}/blocked/d")] == [1, 2, 3, 4]

    a = got[f"{BASE}/p/a"]  # product-page JSON-LD > listing JSON-LD > CSS
    assert (a.name, a.brand, a.price, a.currency) == ("Persol 714", "Persol", 150.0, "TND")
    b = got[f"{BASE}/p/b"]  # no JSON-LD anywhere: CSS + page flags + specs
    assert (b.name, b.brand, b.price, b.currency) == ("Monture B", "Oakley", 89.5, "TND")
    assert b.flags == {"is_bestseller": True, "material": "Métal", "raw_specs": {"Forme": "Ronde"}}
    assert got[f"{BASE}/p/c"].currency == "TND"

    assert "/blocked/d" not in paths                                      # robots.txt respected
    assert f"{BASE}/p/nameless" in crawler.report.listed                  # validation dropped it, the shelf still lists it
    assert not crawler.report.complete and crawler.report.problems == ["/lunettes page 3: not fetched"]
    assert "/lunettes?page=3" in paths and "/lunettes?page=4" not in paths  # 500 survived, max_pages=3 respected
    assert "/p/c" not in paths                                            # max_products=2
    assert all(r.headers["User-Agent"] == "TestBot/1" for r in requests)


@pytest.mark.anyio
async def test_default_client_sends_project_user_agent(cfg, monkeypatch):
    from app.config import settings
    requests: list[httpx.Request] = []
    transport = fake_shop(requests)
    original = httpx.AsyncClient.__init__

    def with_mock_transport(self, *args, **kwargs):
        kwargs["transport"] = transport
        original(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", with_mock_transport)
    async with BaseStoreCrawler(cfg) as crawler:
        crawler.delay_s = 0
        assert crawler.client.timeout.read == settings.request_timeout
        await crawler.crawl()
    assert requests and all(r.headers["User-Agent"] == settings.user_agent for r in requests)


# --- completeness report -----------------------------------------------------------------------------

NEXT_YAML = CONFIG_YAML.replace("{param: page, max_pages: 3}", '{next: "a.next", max_pages: 3}')


def page(*slugs: str, next_to: str | None = None) -> str:
    link = f'<a class="next" href="{next_to}">Suivant</a>' if next_to else ""
    return "<ul>" + "".join(card(s, title=s.upper()) for s in slugs) + "</ul>" + link


async def crawl_report(yaml: str, pages: dict[str, str | int], robots: str = "") -> tuple[list[ScrapedProduct], CrawlReport]:
    """Crawl a fake shop: a page maps to its HTML, or to an HTTP error status."""
    cfg = parse_store_configs(yaml)["shop.test"]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        if path == "/robots.txt":
            return httpx.Response(200, text=robots)
        body = pages.get(path)
        if isinstance(body, int):
            return httpx.Response(body)
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        return await crawler.crawl(), crawler.report


def listed(report: CrawlReport) -> set[str]:
    return {u.rsplit("/", 1)[-1] for u in report.listed}


@pytest.mark.anyio
async def test_report_next_links_ending_naturally_is_complete():
    products, report = await crawl_report(NEXT_YAML, {"/lunettes": page("a", "b", next_to="/lunettes/2"), "/lunettes/2": page("c")})
    assert report.complete and listed(report) == {"a", "b", "c"} and len(products) == 3
    # a listing that fills exactly max_pages and has no further link is a natural end too
    _, report = await crawl_report(NEXT_YAML, {"/lunettes": page("a", next_to="/lunettes/2"),
                                               "/lunettes/2": page("b", next_to="/lunettes/3"), "/lunettes/3": page("c")})
    assert report.complete and listed(report) == {"a", "b", "c"}


@pytest.mark.anyio
async def test_report_a_failed_page_behind_a_next_link_cuts_the_listing_and_says_so():
    _, report = await crawl_report(NEXT_YAML, {"/lunettes": page("a", next_to="/lunettes/2"), "/lunettes/2": 500})
    assert listed(report) == {"a"} and report.problems == ["/lunettes page 2: not fetched"]


@pytest.mark.anyio
async def test_report_stopping_at_max_pages_with_more_to_list_is_incomplete():
    pages = {"/lunettes": page("a", next_to="/lunettes/2"), "/lunettes/2": page("b", next_to="/lunettes/3"),
             "/lunettes/3": page("c", next_to="/lunettes/4")}
    _, report = await crawl_report(NEXT_YAML, pages)
    assert listed(report) == {"a", "b", "c"} and report.problems == ["/lunettes: stopped at max_pages (3) with more to list"]
    # ?page= pagination has no link to check: a listing that fills max_pages counts as cut off
    full = {"/lunettes": page("a"), "/lunettes?page=2": page("b"), "/lunettes?page=3": page("c")}
    _, report = await crawl_report(CONFIG_YAML, full)
    assert report.problems == ["/lunettes: stopped at max_pages (3) with more to list"]
    _, report = await crawl_report(CONFIG_YAML, {"/lunettes": page("a"), "/lunettes?page=2": page("b"),
                                                 "/lunettes?page=3": "<ul></ul>"})   # ...but an empty page ends it
    assert report.complete and listed(report) == {"a", "b"}


@pytest.mark.anyio
async def test_report_empty_pages_are_soft_blocks_unless_they_end_a_param_listing():
    _, report = await crawl_report(NEXT_YAML, {"/lunettes": "<ul></ul>"})
    assert report.problems == ["/lunettes: first page listed nothing"] and not report.listed
    _, report = await crawl_report(NEXT_YAML, {"/lunettes": page("a", next_to="/lunettes/2"), "/lunettes/2": "<ul></ul>"})
    assert report.problems == ["/lunettes page 2: listed nothing"] and listed(report) == {"a"}


@pytest.mark.anyio
async def test_report_a_listing_refused_by_robots_txt_is_incomplete():
    _, report = await crawl_report(NEXT_YAML, {"/lunettes": page("a")}, robots="User-agent: *\nDisallow: /lunettes\n")
    assert report.problems == ["/lunettes page 1: not fetched"] and not report.listed


def test_db_url_of_is_the_stored_form_of_a_product_url():
    for url in ("https://Shop.Test", "https://SHOP.test/p/a?x=1", "https://shop.test/p/é à", "https://shop.test/p/a b"):
        assert db_url_of(url) == ScrapedProduct(url=url, name="A").db_url(), url
    assert db_url_of("https://shop.test/" + "a" * 1000) is None and db_url_of("not a url") is None


# --- retries ------------------------------------------------------------------------------------------

async def fetch_page(responses: list, *, robots: str = "", sleeps: list | None = None, monkeypatch=None, cfg=None):
    """crawler.fetch("/p/a") against a shop answering `responses` in order (an int status, a text, or an exception)."""
    requests: list[str] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        requests.append(request.url.path)
        answer = queue.pop(0) if queue else 200
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, tuple):
            return httpx.Response(answer[0], headers=answer[1])
        return httpx.Response(answer, text="<html>ok</html>") if isinstance(answer, int) else httpx.Response(200, text=answer)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        if sleeps is not None:
            async def record(seconds):
                sleeps.append(seconds)
            monkeypatch.setattr("app.collectors.stores.base.asyncio.sleep", record)
        return await crawler.fetch(f"{BASE}/p/a"), requests


@pytest.mark.anyio
async def test_a_transient_failure_is_retried_and_a_page_that_recovers_is_returned(cfg):
    html, requests = await fetch_page([503, 200], cfg=cfg)
    assert html == "<html>ok</html>" and requests == ["/p/a", "/p/a"]
    html, requests = await fetch_page([httpx.ReadTimeout("slow"), httpx.ConnectError("reset"), 200], cfg=cfg)
    assert html == "<html>ok</html>" and len(requests) == 3                  # timeouts and connection errors count too
    for status in (429, 500, 502, 504):
        assert (await fetch_page([status, 200], cfg=cfg))[0] == "<html>ok</html>", status


@pytest.mark.anyio
async def test_retries_stop_after_two_and_the_page_is_reported_missing(cfg):
    html, requests = await fetch_page([503, 503, 503, 200], cfg=cfg)
    assert html is None and len(requests) == 3                                # the first try and two retries, no more


@pytest.mark.anyio
async def test_a_real_answer_is_never_retried(cfg):
    for status in (404, 403, 401, 410):
        html, requests = await fetch_page([status, 200], cfg=cfg)
        assert html is None and len(requests) == 1, status
    html, requests = await fetch_page([200], robots="User-agent: *\nDisallow: /p/\n", cfg=cfg)
    assert html is None and requests == []                                     # robots.txt: not even a first request


@pytest.mark.anyio
async def test_waits_follow_the_delays_and_a_retry_after_header_wins_but_is_capped(cfg, monkeypatch):
    monkeypatch.setattr(BaseStoreCrawler, "RETRY_DELAYS", (5.0, 15.0))
    sleeps: list[float] = []
    await fetch_page([503, 503, 200], sleeps=sleeps, monkeypatch=monkeypatch, cfg=cfg)
    assert sleeps == [5.0, 15.0]
    sleeps.clear()
    await fetch_page([(429, {"Retry-After": "2"}), 200], sleeps=sleeps, monkeypatch=monkeypatch, cfg=cfg)
    assert sleeps == [2.0]
    sleeps.clear()
    await fetch_page([(503, {"Retry-After": "500"}), 200], sleeps=sleeps, monkeypatch=monkeypatch, cfg=cfg)
    assert sleeps == [60.0]                                                    # never asked to wait more than a minute
    sleeps.clear()
    await fetch_page([(503, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), 200], sleeps=sleeps, monkeypatch=monkeypatch, cfg=cfg)
    assert sleeps == [5.0]                                                     # a date we do not parse: the normal delay


@pytest.mark.anyio
async def test_the_failure_log_names_the_exception_even_when_it_has_no_message(cfg, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="app.collectors.stores.base"):
        await fetch_page([httpx.ReadTimeout(""), httpx.ReadTimeout(""), httpx.ReadTimeout("")], cfg=cfg)
    text = caplog.text
    assert "ReadTimeout; retry 1/2" in text and "ReadTimeout; retry 2/2" in text
    assert "Fetch failed https://www.shop.test/p/a: ReadTimeout" in text and "Fetch failed https://www.shop.test/p/a: " + "\n" not in text


# --- sync service ----------------------------------------------------------------------------------

def test_sync_inserts_updates_and_refuses_cross_source(cfg):
    init_db()
    now = datetime.now(timezone.utc)
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        assert source.kind == "store" and source.country == "TN"
        first = [ScrapedProduct(url=f"{BASE}/p/x", name="X", price=100, currency="TND", rank=1, seen_at=now),
                 ScrapedProduct(url=f"{BASE}/p/y", name="Y", rank=2, seen_at=now)]
        assert vars(service.sync(source.id, first)) == {"inserted": 2, "updated": 0, "conflicts": 0, "reactivated": 0, "dropped": 0, "drop_skipped": None, "carried": 0}

        later = now + timedelta(days=1)
        second = [ScrapedProduct(url=f"{BASE}/p/x", name="X", price=90, currency="TND", rank=1, seen_at=later),
                  ScrapedProduct(url=f"{BASE}/p/x", name="X v2", price=80, currency="TND", rank=1, seen_at=later)]
        assert vars(service.sync(source.id, second)) == {"inserted": 0, "updated": 1, "conflicts": 0, "reactivated": 0, "dropped": 0, "drop_skipped": None, "carried": 0}  # in-batch dup: last wins
        x = s.scalar(select(Product).where(Product.url == f"{BASE}/p/x"))
        assert (x.name, x.price) == ("X v2", 80)
        assert x.seen_at.replace(tzinfo=timezone.utc) == later  # SQLite returns naive UTC

        other = Source(name="Other", kind="store", url="https://other.test", lang="fr")
        s.add(other)
        s.flush()
        stolen = [ScrapedProduct(url=f"{BASE}/p/y", name="Hijack", seen_at=later)]
        assert vars(service.sync(other.id, stolen)) == {"inserted": 0, "updated": 0, "conflicts": 1, "reactivated": 0, "dropped": 0, "drop_skipped": None, "carried": 0}
        y = s.scalar(select(Product).where(Product.url == f"{BASE}/p/y"))
        assert (y.name, y.source_id) == ("Y", source.id)


# --- architectural boundary ------------------------------------------------------------------------

FORBIDDEN = ("sqlalchemy", "app.db", "app.models", "app.extraction", "app.collectors.base", "anthropic")
ISOLATED = ("schemas.py", "config.py", "parser.py", "base.py", "tagger.py", "__init__.py")


@pytest.mark.parametrize("filename", ISOLATED)
def test_crawling_modules_have_no_db_or_llm_imports(filename):
    tree = ast.parse((STORES_DIR / filename).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:  # relative import inside the package
                module = f"app.collectors.stores.{module}" if module else "app.collectors.stores"
                imported += [module] + [f"{module}.{a.name}" for a in node.names]
            else:
                imported.append(module)
    bad = [m for m in imported for f in FORBIDDEN if m == f or m.startswith(f + ".")]
    bad += [m for m in imported if m.startswith("app.collectors.stores.service")]  # the DB side of the package
    assert not bad, f"{filename} imports {bad}"


# --- Outika: the shipped YAML rules against markup trimmed from the real site (WooCommerce) --------

OUTIKA = "https://www.outika-eyewear.tn"


def outika_card(slug: str, name: str, category: str = "eyeglasses/man-eyeglasses") -> str:
    url = f"{OUTIKA}/shop/{category}/{slug}/"
    return (
        '<div class="grid-sizer product-hover-swap product type-product status-publish instock product-type-variable">'
        '<div class="content-product"><div class="product-image-wrapper hover-effect-swap">'
        f'<a class="product-content-image" href="{url}"><img width="408" height="408" '
        f'src="{OUTIKA}/wp-content/uploads/2025/05/{name}BLK-408x408.jpg" class="attachment-woocommerce_thumbnail"></a>'
        '</div><div class="text-center product-details"><div class="products-page-cats">'
        f'<a href="{OUTIKA}/product-category/eyeglasses/" rel="tag">Eyeglasses</a></div>'
        f'<h2 class="product-title"><a href="{url}">{name}</a></h2></div></div></div>'
    )


def outika_listing(cards: list[str], next_page: str | None) -> str:
    nav = (f'<nav class="woocommerce-pagination"><a class="page-numbers" href="{next_page}">2</a>'
           f'<a class="next page-numbers" href="{next_page}">→</a></nav>') if next_page else ""
    return f'<div class="products row">{"".join(cards)}</div>{nav}'


def outika_product(slug: str, name: str, price: str, material: str | None, category: str = "eyeglasses/man-eyeglasses",
                   fr_cats: str = "Homme, Optique", out_of_stock: bool = False) -> str:
    url = f"{OUTIKA}/shop/{category}/{slug}/"
    meta = "".join(
        f'<div class="product_meta"><div class="products-page-cats"><span class="posted_in">Categories: '
        + ", ".join(f'<a href="{OUTIKA}/product-category/x/" rel="tag">{c}</a>' for c in cats.split(", "))
        + "</span></div></div>"
        for cats in (fr_cats, "Eyeglasses, Man"))
    stock = '<p class="stock out-of-stock">This product is currently out of stock and unavailable.</p>' if out_of_stock else ""
    variations = (
        '<table class="variations" role="presentation"><tbody>'
        '<tr><th class="label"><label for="pa_gender">Gender</label></th><td class="value">'
        '<select id="pa_gender"><option value="">Choose an option</option><option value="men" selected>Men</option></select></td></tr>'
        '<tr><th class="label"><label for="pa_materials">Materials</label></th><td class="value">'
        f'<select id="pa_materials"><option value="">Choose an option</option><option value="x" selected>{material}</option></select></td></tr>'
        '</tbody></table>') if material else ""  # simple (single-colour) products have no variations table
    return (
        json_ld({"@context": "https://schema.org/", "@graph": [{"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "item": {"name": "Home", "@id": OUTIKA}}]}]})
        + json_ld({"@context": "https://schema.org/", "@type": "Product", "@id": f"{url}#product", "name": name,
                   "url": url, "image": f"{OUTIKA}/wp-content/uploads/2025/05/{name}C1-1.jpg", "sku": 13446,
                   "offers": [{"@type": "Offer", "price": price, "priceValidUntil": "2027-12-31",
                               "priceSpecification": {"price": price, "priceCurrency": "TND"},
                               "priceCurrency": "TND", "availability": "http://schema.org/InStock", "url": url,
                               "seller": {"@type": "Organization", "name": "Outika"}}]})
        + f'<div class="summary"><h1 class="product_title entry-title">{name}</h1><p class="price"></p>'
        f'<form class="variations_form cart">{variations}<div>{stock}</div></form>{meta}</div>'
    )


@pytest.mark.anyio
async def test_outika_rules_on_recorded_markup():
    from app.collectors.stores.config import load_store_configs
    cfg = load_store_configs()["outika-eyewear.tn"]
    variant = f"{OUTIKA}/shop/eyeglasses/man-eyeglasses/evan-2/?attribute_pa_color=evanc2"  # robots: Disallow /*?
    pages = {
        "/robots.txt": "User-agent: *\nDisallow: /wp-admin\nDisallow: /*?\nAllow: /wp-content/uploads/\n",
        "/product-category/eyeglasses/": outika_listing(
            [outika_card("adonia", "ADONIA"), outika_card("evan-2", "EVAN")],
            f"{OUTIKA}/product-category/eyeglasses/page/2/"),
        "/product-category/eyeglasses/page/2/": outika_listing([
            outika_card("zoe", "ZOE", "eyeglasses/woman-eyeglasses"),
            outika_card("evan-2", "EVAN"),  # listed again: de-duplicated, keeps rank 2
            outika_card("evan-2", "EVAN").replace(f'{OUTIKA}/shop/eyeglasses/man-eyeglasses/evan-2/"', f'{variant}"'),
        ], None),
        "/product-category/sunglasses/": outika_listing([outika_card("dido", "DIDO", "sunglasses/man-sunglasses")], None),
        "/shop/eyeglasses/man-eyeglasses/adonia/": outika_product("adonia", "ADONIA", "45.00", "Acetate"),
        "/shop/eyeglasses/man-eyeglasses/evan-2/": outika_product("evan-2", "EVAN", "49.00", "Metal"),
        "/shop/eyeglasses/woman-eyeglasses/zoe/": outika_product("zoe", "ZOE", "0.00", None, "eyeglasses/woman-eyeglasses",
                                                                 fr_cats="Femme, Optique", out_of_stock=True),
        "/shop/sunglasses/man-sunglasses/dido/": outika_product("dido", "DIDO", "65.00", "Acetate", "sunglasses/man-sunglasses"),
    }
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        requested.append(path)
        return httpx.Response(200, text=pages[path]) if path in pages else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url(): p for p in await crawler.crawl()}

    adonia = products[f"{OUTIKA}/shop/eyeglasses/man-eyeglasses/adonia/"]
    assert (adonia.name, adonia.brand, adonia.price, adonia.currency, adonia.rank) == ("ADONIA", "Outika", 45.0, "TND", 1)
    assert adonia.flags == {"raw_specs": {"Gender": "Men", "Materials": "Acetate"},
                            "categories": "Homme, Optique", "out_of_stock": False}  # first (French) category block
    assert str(adonia.image_url).endswith("ADONIAC1-1.jpg")                     # JSON-LD image over the card thumbnail
    shop = f"{OUTIKA}/shop"
    assert {u: p.rank for u, p in products.items()} == {
        f"{shop}/eyeglasses/man-eyeglasses/adonia/": 1, f"{shop}/eyeglasses/man-eyeglasses/evan-2/": 2,
        f"{shop}/eyeglasses/woman-eyeglasses/zoe/": 3, variant: 4, f"{shop}/sunglasses/man-sunglasses/dido/": 5}
    assert products[f"{shop}/eyeglasses/man-eyeglasses/evan-2/"].flags["raw_specs"]["Materials"] == "Metal"
    assert products[variant].price is None and products[variant].currency == "TND"  # listed, page never fetched
    zoe = products[f"{shop}/eyeglasses/woman-eyeglasses/zoe/"]          # JSON-LD says 0.00 and "InStock"
    assert zoe.price is None                                              # 0.00 is not a price
    assert zoe.flags == {"categories": "Femme, Optique", "out_of_stock": True}  # the DOM wins on stock; no specs
    assert not any("?" in p for p in requested)                                  # robots.txt Disallow: /*? respected
    assert "/product-category/eyeglasses/page/2/" in requested                   # followed the "next" link


@pytest.mark.anyio
async def test_crawl_logs_progress(cfg, caplog):
    caplog.set_level("INFO", logger="app.collectors.stores.base")
    async with httpx.AsyncClient(transport=fake_shop([])) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        await crawler.crawl()
    lines = [r.getMessage() for r in caplog.records]
    assert "Shop Test: listing /lunettes page 1 (max 3), 2 products so far" in lines
    assert "Shop Test: 5 products listed, opening 2 product pages (~1 min)" in lines
    assert "Shop Test: product pages 2/2" in lines
    assert "Shop Test: 4 valid products, 1 dropped" in lines


def test_sync_stores_empty_flags_as_sql_null(cfg):
    from sqlalchemy import text
    init_db()
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        service.sync(source.id, [
            ScrapedProduct(url=f"{BASE}/p/null-none", name="No flags"),
            ScrapedProduct(url=f"{BASE}/p/null-empty", name="Empty flags", flags={}),
            ScrapedProduct(url=f"{BASE}/p/null-set", name="Flags", flags={"out_of_stock": True}),
        ])
        raw = dict(s.execute(text("SELECT url, flags IS NULL FROM products WHERE url LIKE :u"), {"u": f"{BASE}/p/null-%"}).all())
        assert raw == {f"{BASE}/p/null-none": 1, f"{BASE}/p/null-empty": 1, f"{BASE}/p/null-set": 0}
        assert s.scalar(select(Product.flags).where(Product.url == f"{BASE}/p/null-set")) == {"out_of_stock": True}


def test_sync_tags_products_and_retag_is_idempotent(cfg):
    from app.models import ProductTag
    init_db()
    tagged = lambda s, url: {(t.dimension, t.code, t.field) for t in s.scalar(select(Product).where(Product.url == url)).tags}
    url = f"{BASE}/p/tagged"
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        service.sync(source.id, [ScrapedProduct(url=url, name="Monture ronde",
                                                flags={"raw_specs": {"Materials": "Acetate"}, "categories": "Femme, Optique"})])
        assert tagged(s, url) == {("shape", "round", "name"), ("material", "acetate", "spec:Materials"),
                                  ("audience", "women", "categories"), ("product_type", "optical", "categories")}

        # re-sync: material changed, shape kept -> no duplicate (unique constraint) and no stale tag
        service.sync(source.id, [ScrapedProduct(url=url, name="Monture ronde", flags={"raw_specs": {"Materials": "Métal"}})])
        assert tagged(s, url) == {("shape", "round", "name"), ("material", "metal", "spec:Materials")}

        before = s.query(ProductTag).count()
        assert service.retag_all(source.id) >= 1 and service.retag_all(source.id) >= 1
        assert s.query(ProductTag).count() == before                    # idempotent
        assert service.tag_counts(source.id)["shape"] >= 1

        product = s.scalar(select(Product).where(Product.url == url))
        s.delete(product)
        s.commit()
        assert s.query(ProductTag).filter_by(product_id=product.id).count() == 0  # cascade


# --- step 4: generic parser additions ------------------------------------------------------------

def test_json_ld_price_from_price_specification_ignores_list_price():
    from app.collectors.stores.parser import json_ld_fields
    node = {"@type": "Product", "name": "X", "offers": [{"@type": "Offer", "priceSpecification": [
        {"@type": "UnitPriceSpecification", "price": "900", "priceCurrency": "TND", "priceType": "https://schema.org/ListPrice"},
        {"@type": "UnitPriceSpecification", "price": "630", "priceCurrency": "TND", "validThrough": "2026-09-28"}]}]}
    fields = json_ld_fields(node, BASE)
    assert (fields["price"], fields["currency"]) == (630.0, "TND")
    single = {"offers": {"priceSpecification": {"price": "45.000", "priceCurrency": "TND"}}}
    assert json_ld_fields(single, BASE)["price"] == 45.0
    plain = {"offers": {"price": "10", "priceCurrency": "EUR", "priceSpecification": {"price": "99"}}}
    assert json_ld_fields(plain, BASE)["price"] == 10.0  # offers.price still wins


def test_json_ld_id_references_are_resolved_across_scripts():
    from app.collectors.stores.parser import _tree, extract_json_ld_products, json_ld_fields
    page = (json_ld({"@graph": [{"@type": "ImageObject", "@id": "#img", "contentUrl": "/big.jpg"},
                                {"@type": "Product", "name": "P", "image": {"@id": "#img"}, "brand": {"@id": "#brand"}}]})
            + json_ld({"@type": "Brand", "@id": "#brand", "name": "Loewe"}))
    (node,) = extract_json_ld_products(_tree(page))
    fields = json_ld_fields(node, f"{BASE}/p/a")
    assert (fields["image_url"], fields["brand"]) == (f"{BASE}/big.jpg", "Loewe")  # contentUrl, made absolute
    dangling = extract_json_ld_products(_tree(json_ld({"@type": "Product", "name": "P", "image": {"@id": "#missing"}})))
    assert "image_url" not in json_ld_fields(dangling[0], BASE)  # unresolved reference: no image, no crash


def test_description_specs_become_raw_specs():
    from app.collectors.stores.parser import description_specs
    text = ("Lunette de soleil pour Femme de la Marque : Loewe – Référence : LW40128I 01A – Forme : Oeil de Chat – "
            "Style : Tendance – Matière du cadre : Plastique – Indice de protection : 100% UV – Livré avec étui")
    assert description_specs(text) == {  # the 41-char "…de la Marque" lead-in is over the 40-char label limit: skipped
        "Référence": "LW40128I 01A", "Forme": "Oeil de Chat",
        "Style": "Tendance", "Matière du cadre": "Plastique", "Indice de protection": "100% UV"}
    assert description_specs("Forme: Ronde | Couleur : Noir\nMatériau : Métal • sans deux-points") == {
        "Forme": "Ronde", "Couleur": "Noir", "Matériau": "Métal"}
    assert description_specs(None) == {} and description_specs("") == {}


def test_table_specs_win_over_description_specs():
    from app.collectors.stores.config import parse_store_configs
    from app.collectors.stores.parser import parse_product_page
    yaml_text = CONFIG_YAML.replace("    default_currency: TND\n", "    default_currency: TND\n    description_specs: true\n", 1)
    shop = parse_store_configs(yaml_text)["shop.test"]
    html = (json_ld({"@type": "Product", "name": "P", "url": f"{BASE}/p/a",
                     "description": "Forme : Ronde – Couleur : Noir"})
            + '<table class="specs"><tr><th>Forme</th><td>Pilote</td></tr></table>')
    assert parse_product_page(html, f"{BASE}/p/a", shop).flags["raw_specs"] == {"Forme": "Pilote", "Couleur": "Noir"}
    assert "raw_specs" not in parse_product_page(json_ld({"@type": "Product", "name": "P", "description": "Forme : Ronde"}),
                                                 f"{BASE}/p/a", parse_store_configs(CONFIG_YAML)["shop.test"]).flags  # opt-in


def test_data_uri_image_is_ignored_and_product_survives(cfg):
    html = ('<ul><li class="card"><a class="card-link" href="/p/lazy">'
            '<img data-src="data:image/svg+xml,%3Csvg%3E" src="data:image/svg+xml,%3Csvg%3E">'
            '<h3 class="card-title">Lazy</h3></a></li></ul>')
    (item,) = parse_listing(html, f"{BASE}/lunettes", cfg)
    assert "image_url" not in item.css
    assert ScrapedProduct(url=item.url, name=item.css["name"]).image_url is None


# --- mykenza.tn: the shipped YAML rules against markup trimmed from the real site (WooCommerce) --------

KENZA = "https://www.mykenza.tn"
KENZA_CAT = "/categorie-produit/lunettes-cadres/lunettes"
LAZY_PLACEHOLDER = "data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27%3E%3C/svg%3E"


def kenza_card(slug: str, title: str, sale: str, regular: str, *, stock: str = "instock") -> str:
    url = f"{KENZA}/produit/{slug}/"
    return (
        f'<li class="product type-product post-1 status-publish {stock} product_cat-lunettes has-post-thumbnail sale">'
        f'<a href="{url}" class="woocommerce-LoopProduct-link woocommerce-loop-product__link">'
        '<span class="onsale">Spray Offert - 50%</span>'
        f'<img class="attachment-full perfmatters-lazy" src="{LAZY_PLACEHOLDER}" '
        f'data-src="https://media.mykenza.tn/uploads/2026/05/{slug}-300x300.jpg">'
        f'<h2 class="woocommerce-loop-product__title">{title}</h2>'
        f'<span class="price"><ins>{sale} DT</ins> <del>{regular} DT</del></span></a></li>'  # real order: sale first
    )


def kenza_listing(cards: list[str], next_page: str | None, tiles: bool = False) -> str:
    tile = ('<li class="product-category product first"><a title="Lunettes de soleil Homme" '
            f'href="{KENZA}{KENZA_CAT}/lunettes-homme/"><h2 class="woocommerce-loop-category__title">'
            'Lunettes de soleil Homme <mark class="count">(535)</mark></h2></a></li>') if tiles else ""
    nav = (f'<nav class="woocommerce-pagination"><a class="page-numbers" href="{next_page}">2</a>'
           f'<a class="next page-numbers" href="{next_page}">→</a></nav>') if next_page else ""
    return f'<ul class="products">{tile}{"".join(cards)}</ul>{nav}'


def kenza_product(slug: str, name: str, brand: str, sale: str, regular: str, forme: str) -> str:
    url = f"{KENZA}/produit/{slug}/"
    return json_ld({"@context": "https://schema.org", "@graph": [  # Yoast: the image is an @id reference
        {"@type": "WebPage", "@id": url, "primaryImageOfPage": {"@id": f"{url}#primaryimage"}},
        {"@type": "ImageObject", "@id": f"{url}#primaryimage", "url": f"https://media.mykenza.tn/uploads/2026/05/{slug}.jpg",
         "contentUrl": f"https://media.mykenza.tn/uploads/2026/05/{slug}.jpg", "width": 1000, "height": 1000},
        {"@type": "Product", "@id": f"{url}#product", "name": name, "url": url, "sku": "X1",
         "brand": {"@type": "Brand", "name": brand},
         "image": {"@id": f"{url}#primaryimage"},
         "description": (f"Lunette de soleil pour Femme de la Marque : {brand} – Référence : X1 – Forme : {forme} – "
                         "Style : Tendance – Matière du cadre : Plastique – Indice de protection : 100% UV – Livré avec étui"),
         "offers": [{"@type": "Offer", "priceSpecification": [
             {"@type": "UnitPriceSpecification", "price": sale, "priceCurrency": "TND", "validThrough": "2026-09-28"},
             {"@type": "UnitPriceSpecification", "price": regular, "priceCurrency": "TND", "priceType": "https://schema.org/ListPrice"}],
             "availability": "https://schema.org/InStock", "url": url}]}]})


@pytest.mark.anyio
async def test_mykenza_rules_on_recorded_markup():
    from app.collectors.stores.config import load_store_configs
    from app.collectors.stores.tagger import tag_product
    cfg = load_store_configs()["mykenza.tn"]
    men, women = f"{KENZA_CAT}/lunettes-homme/", f"{KENZA_CAT}/lunettes-femme/"
    loewe_title, square_title = "Lunette de Soleil Femme Loewe LW40128I 01A", "Lunette de Soleil Femme Ray-Ban SQUARE RB1971 9149/3F"
    pages = {
        "/robots.txt": "User-agent: *\nDisallow: /wp-admin/\nDisallow: /*?\nDisallow: /*.php$\n",
        men: kenza_listing([kenza_card("loewe-lw40128i-01a", loewe_title, "630", "900"),
                            kenza_card("ray-ban-square-rb1971", square_title, "249", "499")],
                           f"{KENZA}{men}page/2/", tiles=True),
        f"{men}page/2/": kenza_listing([kenza_card("ray-ban-elon-rb3958", "Lunette de Soleil Ray-Ban Elon RB3958 9196/57",
                                                   "249", "499", stock="outofstock")], None),
        women: kenza_listing([kenza_card("loewe-lw40128i-01a", loewe_title, "630", "900")], None),  # unisex duplicate
        "/produit/loewe-lw40128i-01a/": kenza_product("loewe-lw40128i-01a", loewe_title, "Loewe", "630", "900", "Oeil de Chat"),
        "/produit/ray-ban-square-rb1971/": kenza_product("ray-ban-square-rb1971", square_title, "Ray ban", "249", "499", "Carrée"),
        # ray-ban-elon's product page 404s: its listing card alone must still give a valid product
    }
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        requested.append(path)
        return httpx.Response(200, text=pages[path]) if path in pages else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().rstrip("/").rsplit("/", 1)[-1]: p for p in await crawler.crawl()}

    assert set(products) == {"loewe-lw40128i-01a", "ray-ban-square-rb1971", "ray-ban-elon-rb3958"}  # tile ignored, dup merged
    loewe = products["loewe-lw40128i-01a"]
    assert (loewe.name, loewe.brand, loewe.price, loewe.currency, loewe.rank) == (loewe_title, "Loewe", 630.0, "TND", 1)
    assert str(loewe.image_url) == "https://media.mykenza.tn/uploads/2026/05/loewe-lw40128i-01a.jpg"  # JSON-LD ImageObject
    assert loewe.flags["raw_specs"]["Forme"] == "Oeil de Chat" and loewe.flags["out_of_stock"] is False
    assert loewe.flags["categories"] == "Lunette de Soleil Femme"
    assert {(t.dimension, t.code) for t in tag_product(loewe.name, loewe.flags)} >= {
        ("shape", "cat_eye"), ("audience", "women"), ("product_type", "sun")}

    assert loewe.list_price == 900.0                                          # JSON-LD ListPrice: -30 %
    elon = products["ray-ban-elon-rb3958"]  # listing card only: no promo text, sale price, lazy image, stock class
    assert (elon.name, elon.price, elon.currency) == ("Lunette de Soleil Ray-Ban Elon RB3958 9196/57", 249.0, "TND")
    assert elon.list_price == 499.0                                           # card <del>: -50 %
    assert str(elon.image_url).endswith("ray-ban-elon-rb3958-300x300.jpg") and elon.flags["out_of_stock"] is True
    assert elon.flags["categories"] == "Lunette de Soleil"

    square = products["ray-ban-square-rb1971"]
    assert square.price == 249.0 and ("shape", "square") in {(t.dimension, t.code) for t in tag_product(square.name, square.flags)}
    assert not any("?" in p for p in requested) and f"{men}page/2/" in requested


# --- discount signal: list_price -----------------------------------------------------------------

def test_contract_keeps_list_price_only_as_a_real_markdown():
    assert ScrapedProduct(url=f"{BASE}/p/a", name="A", price=70, list_price=100).list_price == 100
    assert ScrapedProduct(url=f"{BASE}/p/a", name="A", price=70, list_price=70).list_price is None   # no markdown
    assert ScrapedProduct(url=f"{BASE}/p/a", name="A", price=70, list_price=50).list_price is None   # nonsense
    assert ScrapedProduct(url=f"{BASE}/p/a", name="A", list_price=100).list_price is None            # no price


def test_json_ld_list_price_from_price_specification():
    from app.collectors.stores.parser import json_ld_fields
    node = {"offers": [{"priceSpecification": [
        {"price": "630", "priceCurrency": "TND"},
        {"price": "900", "priceCurrency": "TND", "priceType": "https://schema.org/ListPrice"}]}]}
    fields = json_ld_fields(node, BASE)
    assert (fields["price"], fields["list_price"]) == (630.0, 900.0)
    plain = {"offers": {"price": "45", "priceSpecification": {"price": "60", "priceType": "StrikethroughPrice"}}}
    assert (json_ld_fields(plain, BASE)["price"], json_ld_fields(plain, BASE)["list_price"]) == (45.0, 60.0)


def test_list_price_comes_from_the_same_source_as_the_price():
    from app.collectors.stores.parser import merge
    assert (lambda m: (m["price"], m["list_price"]))(merge({"price": 630.0, "list_price": 900.0}, {"price": 249.0, "list_price": 499.0})) == (630.0, 900.0)
    # JSON-LD gives the price but no list price: never pair it with a CSS list price from elsewhere on the page
    assert merge({"price": 630.0}, {"price": 249.0, "list_price": 499.0})["list_price"] is None
    assert merge({}, {"price": 249.0, "list_price": 499.0})["list_price"] == 499.0


# --- lamode.tn: optical frames, the shipped YAML rules against markup mirrored from the real site (PrestaShop)

LAMODE = "https://www.lamode.tn"
LAMODE_CAT = "/36-cadres-optiques"


def lamode_card(pid: int, slug: str, brand: str, title: str, price: str, regular: str | None = None) -> str:
    url = f"{LAMODE}/optique-lunettes-de-soleil-lunettes-de-vue-et-lentilles/{pid}-{slug}.html"
    reg = f'<span class="regular-price" aria-label="Prix de base">{regular}</span>' if regular else ""
    return (
        f'<article class="product-miniature js-product-miniature" data-id-product="{pid}"><div class="thumbnail-container">'
        f'<div class="thumbnail-top"><a href="{url}" class="thumbnail product-thumbnail"><picture>'
        f'<img src="{LAMODE}/{pid}-large_default/{slug}.webp" alt="{title} - {brand}" loading="lazy"></picture></a>'
        f'<a class="btn btn-primary buy-now" href="{url}" data-link-action="quickview"> Voir produit </a></div>'
        f'<div class="product-description"><p class="product-manufacturer-title text-uppercase">{brand}</p>'
        f'<h3 class="product-name"><a href="{url}" content="{url}">{title}</a></h3>'
        f'<div class="product-price-and-shipping">{reg}<span class="price" aria-label="Prix"> {price} </span></div>'
        '</div></div></article>'
    )


def lamode_product(pid: int, slug: str, brand: str, title: str, price: str, forme: str, genre: str = "Femmes") -> str:
    url = f"{LAMODE}/optique-lunettes-de-soleil-lunettes-de-vue-et-lentilles/{pid}-{slug}.html"
    rows = [("Forme Lunette", forme), ("Saison", "Toutes saisons"), ("Genre", genre), ("VISAGE", "Ovale"),
            ("VISAGE", "Rond"), ("Magasin", "Magasin Centre X")]
    features = "".join(f'<div class="row"><div class="col-xs-6 mb-1"><strong>{k}</strong></div>'
                       f'<div class="col-xs-6"><span>{v}</span></div></div>' for k, v in rows)
    return (
        json_ld({"@context": "https://schema.org/", "@type": "Product", "name": title.replace(f"{brand.upper()} ", f"{brand.upper()}  "),
                 "brand": {"@type": "Brand", "name": brand}, "image": f"{LAMODE}/{pid}-home_default/{slug}.webp",
                 "offers": {"@type": "Offer", "priceCurrency": "TND", "price": price,
                            "url": f"{url.replace(f'{pid}-', f'{pid}-22062-')}#/325-couleur-bordeaux",
                            "availability": "https://schema.org/InStock"}})
        + '<div class="product-information"><div id="product-accordion"><div id="product-features-tab" class="collapse">'
        + f'<div class="card-body">{features}</div></div></div></div>'
    )


@pytest.mark.anyio
async def test_lamode_rules_on_recorded_markup():
    from app.collectors.stores.config import load_store_configs
    from app.collectors.stores.tagger import tag_product
    cfg = load_store_configs()["lamode.tn"]
    gucci_t, bal_t, dior_t = ("Lunettes de Vue Femme GUCCI GG1003OA", "Lunettes de Vue Femme BALENCIAGA BB0273-O",
                              "Lunettes de Vue Homme DIOR 245G")
    pages = {
        "/robots.txt": "User-agent: *\nDisallow: /*?q=\nDisallow: /*?order=\nDisallow: /*?search_query=\n",
        LAMODE_CAT: (lamode_card(16506, "lunettes-de-vue-femme-balenciaga-bb0273-o", "BALENCIAGA", bal_t, "910 DT")
                     + lamode_card(15101, "lunettes-de-vue-femme-gucci-gg1003oa", "GUCCI", gucci_t, "1 420 DT", regular="1 775 DT")
                     + f'<nav class="pagination"><a rel="next" href="{LAMODE}{LAMODE_CAT}?page=2" class="next js-search-link">Suivant</a></nav>'),
        f"{LAMODE_CAT}?page=2": lamode_card(14000, "lunettes-de-vue-homme-dior-245g", "DIOR", dior_t, "1 099 DT"),
        "/optique-lunettes-de-soleil-lunettes-de-vue-et-lentilles/16506-lunettes-de-vue-femme-balenciaga-bb0273-o.html":
            lamode_product(16506, "lunettes-de-vue-femme-balenciaga-bb0273-o", "BALENCIAGA", bal_t, "910", "Cat-Eye"),
        "/optique-lunettes-de-soleil-lunettes-de-vue-et-lentilles/15101-lunettes-de-vue-femme-gucci-gg1003oa.html":
            lamode_product(15101, "lunettes-de-vue-femme-gucci-gg1003oa", "Gucci", gucci_t, "1420", "Carrée"),
        # the Dior page 404s: its listing card alone must still give a valid product
    }
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        requested.append(path)
        return httpx.Response(200, text=pages[path]) if path in pages else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().rsplit("/", 1)[-1].split("-", 1)[0]: p for p in await crawler.crawl()}

    assert set(products) == {"16506", "15101", "14000"} and f"{LAMODE_CAT}?page=2" in requested
    bal, gucci, dior = products["16506"], products["15101"], products["14000"]
    assert (bal.name, bal.brand, bal.price, bal.currency, bal.rank) == (bal_t, "BALENCIAGA", 910.0, "TND", 1)  # "  " collapsed
    assert bal.flags["raw_specs"]["Forme Lunette"] == "Cat-Eye" and bal.flags["categories"] == "Lunettes de Vue Femme"
    assert {(t.dimension, t.code) for t in tag_product(bal.name, bal.flags)} == {
        ("shape", "cat_eye"), ("audience", "women"), ("product_type", "optical")}   # VISAGE Ovale/Rond ignored
    assert gucci.price == 1420.0 and gucci.list_price is None     # JSON-LD price never paired with a CSS list price
    assert (dior.name, dior.brand, dior.price) == (dior_t, "DIOR", 1099.0)          # listing card only
    assert {(t.dimension, t.code) for t in tag_product(dior.name, dior.flags)} == {("audience", "men"), ("product_type", "optical")}
