"""Anne & Valentin (France, custom CMS, presence-only creator brand): 19 concept collection hubs,
editorial descriptions with opening architectural shape terms, clean specs (Dimensions, Matière, Fabrication),
and inline variant swatches with supplier codes (data-c) and dual acetate hex layers.
Offline: markup trimmed from real site pages (2026-10-01), served by httpx.MockTransport."""

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

AEV = "https://anneetvalentin.com"
ROBOTS = """User-agent: *
Allow: /
"""

FRAMES = {
    "/fr/optique/krafties/veliska": {
        "name": "VELISKA",
        "category": "Optique",
        "desc": "Octogonale. Douce. Tonique. Graphique. Présente. Démultiplication des facettes. Encadre le regard. Personnalité en acier trempé.",
        "specs": [("Dimensions :", "Calibre : 46 mm Nez : 24 mm Branche : 145 mm"), ("Matière :", "Acétate"), ("Fabrication :", "France")],
        "variants": [("26A40", "VELISKA 26A40", "#A890BA", "#D1392C"), ("26A41", "VELISKA 26A41", "#4B1D18", "#732A1E")],
        "img": "https://img.anneetvalentin.com/photos/side/VELISKA_26A41-side.jpg",
    },
    "/fr/optique/krafties/vassia": {
        "name": "VASSIA",
        "category": "Optique",
        "desc": "Petite ovale. Plus cute que cute. Éternelle étudiante au regard étiré.",
        "specs": [("Dimensions :", "Calibre : 44 mm Nez : 22 mm Branche : 145 mm"), ("Matière :", "Acétate"), ("Fabrication :", "France")],
        "variants": [("26A30", "VASSIA 26A30", "#397388", "#397388")],
        "img": "https://img.anneetvalentin.com/photos/side/VASSIA_26A30-side.jpg",
    },
    "/fr/optique/simplecut/jereflechis": {
        "name": "JEREFLECHIS",
        "category": "Optique",
        "desc": "Grande pantos (mais moins grande qu’elle le croit). Des lignes tendues par les découpes de reprise.",
        "specs": [("Dimensions :", "Calibre : 46 mm Nez : 23 mm Branche : 150 mm"), ("Matière :", "Acétate"), ("Fabrication :", "France")],
        "variants": [("26A01", "JEREFLECHIS 26A01", "#397388", "#397388"), ("26A02", "JEREFLECHIS 26A02", "#B87337", "#B87337")],
        "img": "https://img.anneetvalentin.com/photos/side/JEREFLECHIS_26A02-side.jpg",
    },
    "/fr/solaire/juxtapoz/sharper": {
        "name": "SHARPER",
        "category": "Solaire",
        "desc": "SHARPER. Rectangle très adouci, classique et décontracté. Pont haut perché et droit.",
        "specs": [("Dimensions :", "Calibre : 51 mm Nez : 20 mm Branche : 145 mm"), ("Matière :", "Acétate"), ("Fabrication :", "France")],
        "variants": [("25D35", "SHARPER 25D35", "#245549", "#9BBE92")],
        "img": "https://img.anneetvalentin.com/photos/side/SHARPER_25D35-side.jpg",
    },
}


def card_html(path: str, data: dict) -> str:
    return (f'<li><a href="{path}">'
            f'<picture><img src="{data["img"]}" alt="Anne &amp; Valentin {data["name"]}" loading="lazy"></picture>'
            f'<i>{data["name"]}</i></a></li>')


def concept_listing_html(concept_path: str) -> str:
    matching = [card_html(p, d) for p, d in FRAMES.items() if p.startswith(concept_path + "/")]
    return f'<html><body><main><ul>{"".join(matching)}</ul></main></body></html>'


def product_html(path: str, data: dict) -> str:
    swatches = "".join(
        f'<li data-a="{label}" data-c="{data["name"]}_{code}"><i style="background:{hex1}"></i><i style="background:{hex2}"></i></li>'
        for code, label, hex1, hex2 in data["variants"]
    )
    specs = "".join(f'<dl><dt>{k}</dt><dd>{v}</dd></dl>' for k, v in data["specs"])
    return (f'<!DOCTYPE html><html><head><title>Lunettes {data["name"]} – Anne &amp; Valentin</title>'
            f'<link rel="canonical" href="{AEV}{path}"></head><body>'
            f'<article><h1>{data["name"]}</h1>'
            f'<p>{data["desc"]}</p>'
            f'<ul id="cou">{swatches}</ul>'
            f'{specs}'
            f'<figure id="visu"><img src="{data["img"]}" alt=""></figure>'
            f'</article></body></html>')


def site_pages() -> dict[str, str]:
    cfg = load_store_configs()["anneetvalentin.com"]
    pages = {"/robots.txt": ROBOTS}
    # All 19 configured listing URLs
    for entry in cfg.listing.urls:
        url = entry.url if hasattr(entry, "url") else str(entry)
        concept = url.split("/")[-1]
        has_real = any(p.startswith(url + "/") for p in FRAMES)
        if has_real:
            pages[url] = concept_listing_html(url)
        else:
            dummy_path = f"{url}/{concept}-model"
            pages[url] = f'<html><body><main><ul><li><a href="{dummy_path}"><picture><img src=""></picture><i>{concept.upper()}</i></a></li></ul></main></body></html>'
            pages[dummy_path] = f'<!DOCTYPE html><html><body><article><h1>{concept.upper()}</h1><p>Ovale classique.</p><ul id="cou"><li data-a="C1" data-c="C1"></li></ul><dl><dt>Matière :</dt><dd>Acétate</dd></dl></article></body></html>'
    # Real sampled product pages
    for path, data in FRAMES.items():
        pages[path] = product_html(path, data)
    return pages


async def crawl_aev():
    cfg = load_store_configs()["anneetvalentin.com"]
    pages, requested = site_pages(), []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url)
        path = request.url.raw_path.decode()
        return httpx.Response(200, text=pages[path]) if path in pages else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().replace(AEV, ""): p for p in await crawler.crawl()}
    return products, requested, crawler.report


@pytest.fixture
def anyio_backend():
    return "asyncio"


def tags_set(p: ScrapedProduct) -> set[tuple[str, str, str | None]]:
    return {(t.dimension, t.code, t.supplier_code) for t in tag_product(p.name, p.flags)}


@pytest.mark.anyio
async def test_anne_et_valentin_concept_hubs_and_products_crawled_offline():
    products, requested, report = await crawl_aev()
    assert report.complete
    assert report.problems == []
    assert report.gaps == []
    assert set(FRAMES) <= set(products)

    veliska = products["/fr/optique/krafties/veliska"]
    assert veliska.name == "VELISKA"
    assert veliska.brand == "Anne & Valentin"
    assert veliska.price is None  # presence-only creator brand
    assert veliska.currency == "EUR"
    assert str(veliska.image_url) == "https://img.anneetvalentin.com/photos/side/VELISKA_26A41-side.jpg"
    assert veliska.flags["categories"] == "Optique"

    sharper = products["/fr/solaire/juxtapoz/sharper"]
    assert sharper.name == "SHARPER"
    assert sharper.flags["categories"] == "Solaire"


@pytest.mark.anyio
async def test_specs_and_editorial_shape_extraction():
    products, _, _ = await crawl_aev()

    veliska = products["/fr/optique/krafties/veliska"]
    t_veliska = tags_set(veliska)
    # Shape is extracted from editorial description ("Octogonale...")
    assert ("shape", "geometric", None) in t_veliska
    # Material is extracted from specs ("Matière : Acétate")
    assert ("material", "acetate", None) in t_veliska
    # Product type is from listing category
    assert ("product_type", "optical", None) in t_veliska
    # Metaphorical phrase "Personnalité en acier trempé" must NOT tag material: metal
    assert ("material", "metal", None) not in t_veliska

    jereflechis = products["/fr/optique/simplecut/jereflechis"]
    t_jereflechis = tags_set(jereflechis)
    # "Grande pantos..." maps to round (panto)
    assert ("shape", "round", None) in t_jereflechis
    assert ("material", "acetate", None) in t_jereflechis

    vassia = products["/fr/optique/krafties/vassia"]
    t_vassia = tags_set(vassia)
    # "Petite ovale..." maps to oval
    assert ("shape", "oval", None) in t_vassia

    sharper = products["/fr/solaire/juxtapoz/sharper"]
    t_sharper = tags_set(sharper)
    # "Rectangle très adouci..." maps to rectangle
    assert ("shape", "rectangle", None) in t_sharper
    assert ("product_type", "sun", None) in t_sharper


@pytest.mark.anyio
async def test_variants_and_supplier_codes():
    products, _, _ = await crawl_aev()

    veliska = products["/fr/optique/krafties/veliska"]
    variant_codes = [v["code"] for v in veliska.flags.get("variants", [])]
    assert variant_codes == ["26A40", "26A41"]

    jereflechis = products["/fr/optique/simplecut/jereflechis"]
    variant_codes_j = [v["code"] for v in jereflechis.flags.get("variants", [])]
    assert variant_codes_j == ["26A01", "26A02"]


def test_tagger_papillon_alias_and_description():
    flags = {
        "description": "Belle monture papillon avec biseautages affirmés.",
        "raw_specs": {"Matière :": "Acétate"},
    }
    tags = {(t.dimension, t.code, t.field) for t in tag_product("CHLOE", flags)}
    assert ("shape", "butterfly", "description") in tags
    assert ("material", "acetate", "spec:Matière :") in tags
