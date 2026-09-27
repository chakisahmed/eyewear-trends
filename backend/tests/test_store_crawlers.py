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
from app.collectors.stores.schemas import ScrapedProduct
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


def test_shipped_config_is_valid_and_empty():
    from app.collectors.stores.config import load_store_configs
    assert load_store_configs() == {}


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
        assert vars(service.sync(source.id, first)) == {"inserted": 2, "updated": 0, "conflicts": 0}

        later = now + timedelta(days=1)
        second = [ScrapedProduct(url=f"{BASE}/p/x", name="X", price=90, currency="TND", rank=1, seen_at=later),
                  ScrapedProduct(url=f"{BASE}/p/x", name="X v2", price=80, currency="TND", rank=1, seen_at=later)]
        assert vars(service.sync(source.id, second)) == {"inserted": 0, "updated": 1, "conflicts": 0}  # in-batch dup: last wins
        x = s.scalar(select(Product).where(Product.url == f"{BASE}/p/x"))
        assert (x.name, x.price) == ("X v2", 80)
        assert x.seen_at.replace(tzinfo=timezone.utc) == later  # SQLite returns naive UTC

        other = Source(name="Other", kind="store", url="https://other.test", lang="fr")
        s.add(other)
        s.flush()
        stolen = [ScrapedProduct(url=f"{BASE}/p/y", name="Hijack", seen_at=later)]
        assert vars(service.sync(other.id, stolen)) == {"inserted": 0, "updated": 0, "conflicts": 1}
        y = s.scalar(select(Product).where(Product.url == f"{BASE}/p/y"))
        assert (y.name, y.source_id) == ("Y", source.id)


# --- architectural boundary ------------------------------------------------------------------------

FORBIDDEN = ("sqlalchemy", "app.db", "app.models", "app.extraction", "app.collectors.base", "anthropic")
ISOLATED = ("schemas.py", "config.py", "parser.py", "base.py", "__init__.py")


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
