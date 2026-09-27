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


def active_products(session: Session) -> list[tuple[Product, str]]:
    """(product, store name) for every product still on its store's shelf."""
    latest = dict(session.execute(select(Product.source_id, func.max(Product.seen_at)).group_by(Product.source_id)).all())
    rows = session.execute(select(Product, Source.name).join(Source, Source.id == Product.source_id)).all()
    return [(p, store) for p, store in rows if p.seen_at >= latest[p.source_id] - timedelta(days=ACTIVE_DAYS)]


def shelf_by_attribute(session: Session) -> dict:
    """{"stores": [{name, products, updated}], "dimensions": {dim: {"tagged": n, "items": {code: {sku, share, avg_price}}}}}."""
    active = active_products(session)
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
                           "avg_price": {cur: round(mean(v), 2) for cur, v in prices.items()}}
        dimensions[dim] = {"tagged": tagged, "with_value": with_value[dim], "unmapped": unmapped[dim], "items": items}
    return {"stores": sorted(stores.values(), key=lambda s: s["name"]), "dimensions": dimensions}


def unmapped_share(data: dict) -> float:
    return data["unmapped"] / data["with_value"] if data["with_value"] else 0.0


def comparable(data: dict) -> bool:
    """Enough tagged products, and the stores' vocabulary for this dimension is mostly understood."""
    return data["tagged"] >= MIN_TAGGED and unmapped_share(data) <= MAX_UNMAPPED


def shelf_gaps(session: Session, week: date, shelf: dict | None = None) -> dict:
    """Press status of the week vs shelf share: {"opportunities", "risks", "skipped_dimensions"}."""
    shelf = shelf or shelf_by_attribute(session)
    tax = load_taxonomy()
    covered = {d for d in DIMENSIONS if comparable(shelf["dimensions"][d])}
    opportunities, risks = [], []
    for snap in session.scalars(select(TrendSnapshot).where(TrendSnapshot.week == week, TrendSnapshot.dimension.in_(covered))):
        item = shelf["dimensions"][snap.dimension]["items"].get(snap.code, {"sku": 0, "share": 0.0, "avg_price": {}})
        gap = {"dimension": snap.dimension, "code": snap.code, "label": tax.label(snap.dimension, snap.code),
               "hex": tax.get(snap.dimension, snap.code).hex,
               "status": snap.status, "momentum": snap.momentum, **item}
        if snap.status in RISING and item["share"] < OPPORTUNITY_SHARE:
            opportunities.append(gap)
        elif snap.status == "en_baisse" and item["share"] >= RISK_SHARE:
            risks.append(gap)
    return {
        "opportunities": sorted(opportunities, key=lambda g: -g["momentum"]),
        "risks": sorted(risks, key=lambda g: -g["share"]),
        "skipped_dimensions": [d for d in DIMENSIONS if d not in covered],
    }
