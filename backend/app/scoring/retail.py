"""Tunisian shelf data per attribute, and "Shelf vs. Signal" gaps. Deterministic: no LLM.

The shelf is the tracked stores' active products (store crawlers + rule-based product_tags). The
press signal is the week's trend snapshot. Comparing them flags:
- opportunities: rising (or peaking) in the press, rare on the shelf (< OPPORTUNITY_SHARE);
- stock risks: declining in the press, well stocked (>= RISK_SHARE).
Shares are per dimension (e.g. % of the products tagged with any shape). A dimension is only
compared when the shelf data for it is trustworthy:
- enough products carry it (MIN_TAGGED): Outika, for instance, has no shapes at all;
- the stores' own vocabulary is understood (MAX_UNMAPPED): of the products that state a value for
  it (raw_specs "Style", "Couleur"…), too many untagged ones mean a vocabulary mismatch, not an
  absence. MyKenza's "Style" says Sport / Classique / Tendance, and colours are often SKU codes.

Discount signal (list_price): a product's markdown is 1 - price / list_price. Stores run store-wide
sales (MyKenza: every product -25 to -50 %), so an attribute's markdown is read against its store's
usual markdown (the baseline): relative_depth > 0 means discounted deeper than the rest of the store.
Stores that publish no list price at all are left out of markdown figures, not counted as 0 %.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.stores.tagger import SPEC_DIMENSIONS
from app.models import Product, ProductTag, Source, TrendSnapshot
from app.taxonomy import fold, load_taxonomy

DIMENSIONS = ("shape", "color", "material", "style")
ACTIVE_DAYS = 14  # a product counts if seen within this many days of its store's latest crawl
MIN_TAGGED = 20  # tagged products needed in a dimension before its shelf shares mean anything
OPPORTUNITY_SHARE = 0.05
RISK_SHARE = 0.15
MAX_UNMAPPED = 0.30  # share of stated values the tagger did not recognise, above which a dimension is skipped
RISING = ("en_hausse", "au_pic")
PRODUCT_TYPES = ("optical", "sun")  # separate shelves: the shape mix of prescription frames and sunglasses differs
TYPE_LABELS = {"optical": "optique", "sun": "solaire"}
# Attributes that only exist on sunglasses: their absence from a prescription shelf is normal, not a gap.
SUN_ONLY = {("shape", "shield"), ("color", "tinted_lens")}
CLEARANCE_PTS = 0.10  # relative markdown (vs the store's usual) that marks a declining attribute as being cleared
MARKET_COUNTRY = "TN"  # the "Marché Tunisien" lens: shelf shares and gaps only count stores of this country


def active_products(session: Session, country: str | None = None) -> list[tuple[Product, str]]:
    """(product, store name) for every product still on its store's shelf; country restricts it to one market's
    stores (Source.country)."""
    latest = dict(session.execute(select(Product.source_id, func.max(Product.seen_at)).group_by(Product.source_id)).all())
    query = select(Product, Source.name).join(Source, Source.id == Product.source_id)
    if country:
        query = query.where(Source.country == country)
    return [(p, store) for p, store in session.execute(query).all()
            if p.seen_at >= latest[p.source_id] - timedelta(days=ACTIVE_DAYS)]


def markdown(p: Product) -> float:
    return 1 - p.price / p.list_price if p.price and p.list_price and p.list_price > p.price else 0.0


def store_baselines(active: list[tuple[Product, str]]) -> dict[int, float]:
    """Usual markdown per store (source_id), for stores that publish list prices at all."""
    by_store: dict[int, list[Product]] = defaultdict(list)
    for p, _ in active:
        by_store[p.source_id].append(p)
    return {sid: mean(markdown(p) for p in ps) for sid, ps in by_store.items() if any(p.list_price for p in ps)}


def markdown_stats(products: list[Product], baselines: dict[int, float]) -> dict | None:
    """{compared, discounted, share_discounted, avg_depth, relative_depth}; None if no store publishes list prices."""
    compared = [p for p in products if p.source_id in baselines]
    if not compared:
        return None
    depths = [markdown(p) for p in compared]
    discounted = [d for d in depths if d > 0]
    return {
        "compared": len(compared),
        "discounted": len(discounted),
        "share_discounted": round(len(discounted) / len(compared), 4),
        "avg_depth": round(mean(discounted), 4) if discounted else None,
        "relative_depth": round(mean(markdown(p) - baselines[p.source_id] for p in compared), 4),
    }


def attribute_markdown(session: Session, dimension: str, code: str) -> dict | None:
    active = active_products(session)
    ids = set(session.scalars(select(ProductTag.product_id).where(ProductTag.dimension == dimension, ProductTag.code == code)))
    return markdown_stats([p for p, _ in active if p.id in ids], store_baselines(active))


def of_type(session: Session, active: list[tuple[Product, str]], product_type: str) -> list[tuple[Product, str]]:
    ids = set(session.scalars(select(ProductTag.product_id).where(ProductTag.dimension == "product_type",
                                                                   ProductTag.code == product_type)))
    return [(p, store) for p, store in active if p.id in ids]


def shelf_by_attribute(session: Session, product_type: str | None = None, country: str | None = MARKET_COUNTRY) -> dict:
    """{"stores": [{name, products, updated}], "dimensions": {dim: {"tagged": n, "items": {code: {sku, share, avg_price}}}}}.
    product_type ("optical" / "sun") restricts the shelf; store markdown baselines stay store-wide (a sale covers
    the whole store). The shelf is the Tunisian market's by default: a creator brand's own catalog (Etnia Barcelona,
    Spain) is not a Tunisian shelf, so it never enters these shares or the gaps built on them."""
    everything = active_products(session, country)
    baselines = store_baselines(everything)
    active = of_type(session, everything, product_type) if product_type else everything
    by_id = {p.id: p for p, _ in active}
    stores: dict[str, dict] = {}
    for p, store in active:
        entry = stores.setdefault(store, {"name": store, "products": 0, "updated": p.seen_at})
        entry["products"] += 1
        entry["updated"] = max(entry["updated"], p.seen_at)

    products_by_code: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    if by_id:
        for pid, dim, code in session.execute(
            select(ProductTag.product_id, ProductTag.dimension, ProductTag.code)
            .where(ProductTag.product_id.in_(list(by_id)), ProductTag.dimension.in_(DIMENSIONS))
        ):
            products_by_code[dim][code].add(pid)

    # Products stating a value for a dimension (raw_specs), and those whose value was not recognised
    with_value: dict[str, int] = defaultdict(int)
    unmapped: dict[str, int] = defaultdict(int)
    tagged_ids = {dim: set().union(*codes.values()) if codes else set() for dim, codes in products_by_code.items()}
    for pid, p in by_id.items():
        specs = (p.flags or {}).get("raw_specs") if isinstance(p.flags, dict) else None
        dims_stated = {SPEC_DIMENSIONS.get(fold(str(k))) for k in (specs or {})} & set(DIMENSIONS)
        for dim in dims_stated:
            with_value[dim] += 1
            unmapped[dim] += pid not in tagged_ids.get(dim, set())

    dimensions = {}
    for dim in DIMENSIONS:
        tagged = len(tagged_ids.get(dim, set()))
        items = {}
        for code, ids in products_by_code[dim].items():
            prices: dict[str, list[float]] = defaultdict(list)
            for pid in ids:
                p = by_id[pid]
                if p.price and p.price > 0 and p.currency:
                    prices[p.currency].append(p.price)
            items[code] = {"sku": len(ids), "share": len(ids) / tagged,
                           "avg_price": {cur: round(mean(v), 2) for cur, v in prices.items()},
                           "markdown": markdown_stats([by_id[pid] for pid in ids], baselines)}
        dimensions[dim] = {"tagged": tagged, "with_value": with_value[dim], "unmapped": unmapped[dim], "items": items}
    return {"stores": sorted(stores.values(), key=lambda s: s["name"]), "dimensions": dimensions}


def unmapped_share(data: dict) -> float:
    return data["unmapped"] / data["with_value"] if data["with_value"] else 0.0


def comparable(data: dict) -> bool:
    """Enough tagged products, and the stores' vocabulary for this dimension is mostly understood."""
    return data["tagged"] >= MIN_TAGGED and unmapped_share(data) <= MAX_UNMAPPED


def shelf_gaps(session: Session, week: date, shelf: dict | None = None, product_type: str | None = None) -> dict:
    """Press status of the week vs shelf share: {"opportunities", "risks", "skipped_dimensions"}."""
    shelf = shelf or shelf_by_attribute(session, product_type)
    tax = load_taxonomy()
    covered = {d for d in DIMENSIONS if comparable(shelf["dimensions"][d])}
    opportunities, risks = [], []
    for snap in session.scalars(select(TrendSnapshot).where(TrendSnapshot.week == week, TrendSnapshot.dimension.in_(covered))):
        if product_type == "optical" and (snap.dimension, snap.code) in SUN_ONLY:
            continue
        item = shelf["dimensions"][snap.dimension]["items"].get(snap.code, {"sku": 0, "share": 0.0, "avg_price": {}, "markdown": None})
        md = item["markdown"]
        clearance = bool(md and md["relative_depth"] >= CLEARANCE_PTS)
        gap = {"dimension": snap.dimension, "code": snap.code, "label": tax.label(snap.dimension, snap.code),
               "hex": tax.get(snap.dimension, snap.code).hex,
               "status": snap.status, "momentum": snap.momentum, **item, "clearance": clearance,
               "product_type": product_type}
        if snap.status in RISING and item["share"] < OPPORTUNITY_SHARE:
            opportunities.append(gap)
        elif snap.status == "en_baisse" and (item["share"] >= RISK_SHARE or clearance):
            risks.append(gap)  # well stocked, or being cleared deeper than the store's usual sale
    return {
        "opportunities": sorted(opportunities, key=lambda g: -g["momentum"]),
        "risks": sorted(risks, key=lambda g: -g["share"]),
        "skipped_dimensions": [d for d in DIMENSIONS if d not in covered],
    }


def shelf_gaps_by_type(session: Session, week: date) -> dict:
    """Gaps computed within each product type's shelf, merged: an attribute is an opportunity on the sunglasses
    shelf, the prescription shelf, or both. A type with no (comparable) data is skipped, never read as 'absent'."""
    opportunities, risks, skipped, types, shelves = [], [], {}, {}, {}
    for product_type in PRODUCT_TYPES:
        shelf = shelf_by_attribute(session, product_type)
        gaps = shelf_gaps(session, week, shelf, product_type)
        opportunities += gaps["opportunities"]
        risks += gaps["risks"]
        skipped[product_type] = gaps["skipped_dimensions"]
        types[product_type] = sum(st["products"] for st in shelf["stores"])
        shelves[product_type] = shelf
    return {
        "opportunities": sorted(opportunities, key=lambda g: -g["momentum"]),
        "risks": sorted(risks, key=lambda g: -g["share"]),
        "skipped_dimensions": skipped,
        "types": types,
        "shelves": shelves,
    }


PAIRING_LIMIT = 8  # partner colours shown per colour


def color_pairings(session: Session, code: str) -> dict | None:
    """Frequent pairings of a colour family in acetate laminations (the `lamination` tags, e.g. "blue+tortoiseshell").

    Counts frames (distinct active products), never variants: a frame with three blue/tortoiseshell codes counts once
    per partner. A frame with a three-layer lamination counts once for each of the other two layers. `bestsellers`
    are the frames the store itself flags (frame-level flag, never guessed). None when no active frame carries this
    colour in a lamination."""
    active = {p.id: (p, store) for p, store in active_products(session)}
    known = load_taxonomy().codes("color")
    partners: dict[str, set[int]] = defaultdict(set)
    frames: set[int] = set()
    for product_id, lamination in session.execute(
            select(ProductTag.product_id, ProductTag.code).where(ProductTag.dimension == "lamination")):
        layers = lamination.split("+")
        if product_id not in active or code not in layers:
            continue
        frames.add(product_id)
        for layer in layers:
            if layer != code and layer in known:
                partners[layer].add(product_id)
    if not frames:
        return None

    def bestseller(pid: int) -> bool:
        return bool((active[pid][0].flags or {}).get("is_bestseller"))

    def entry(ids: set[int]) -> dict:
        best = sorted((active[i][0] for i in ids if bestseller(i)), key=lambda p: (p.rank or 10**9, p.name))
        return {"frames": len(ids), "bestsellers": len(best),
                "examples": [{"name": p.name, "url": p.url, "store": active[p.id][1]} for p in best[:2]]}

    ranked = sorted(partners.items(), key=lambda kv: (-len(kv[1]), -sum(bestseller(i) for i in kv[1]), kv[0]))
    return {
        **entry(frames),
        "stores": sorted({active[i][1] for i in frames}),
        "partners": [{"code": partner, **entry(ids)} for partner, ids in ranked[:PAIRING_LIMIT]],
    }
