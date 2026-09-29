"""Catalog history, read side: which frames just arrived, which were retired, and whether the crawls can be trusted.

Deterministic, no LLM. The data comes from the products' history columns (first_seen_at, is_active, dropped_at, kept by
StoreCrawl-logged crawls, see collectors/stores/service.py) and from the store_crawls log.

- History starts at a store's first complete (`ok`) crawl: its `baseline`. Products first seen before it are baseline,
  including those crawled by hand before the log existed, whose real arrival date is unknown. A store with no `ok`
  crawl has no new or retired products at all.
- New: first seen after the baseline, within the last NEW_DAYS. Retired: dropped by a complete crawl within NEW_DAYS and
  not back since (a returning product has dropped_at cleared).
- Creator brands (stores outside retail.MARKET_COUNTRY) are the design signal: a Tunisian retailer's new arrivals are its
  assortment choices. The attribute breakdown and the weekly brief use creator brands only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.stores.config import ScraperConfig
from app.models import Product, ProductTag, Source, StoreCrawl
from app.scoring import retail
from app.taxonomy import load_taxonomy

NEW_DAYS = 30
LATE_FACTOR = 2  # a store is "late" once its last complete crawl is older than this many cadences
MIN_NEW_FOR_SHARES = 10  # under this, only counts: a share of a handful of frames is not a trend
TOP_ATTRIBUTES = 6
ATTRIBUTE_DIMENSIONS = ("shape", "color", "material")


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite returns naive UTC


def baselines(session: Session) -> dict[int, datetime]:
    """{source_id: finished_at of its first complete crawl}: where each store's history starts."""
    rows = session.execute(select(StoreCrawl.source_id, func.min(StoreCrawl.finished_at))
                           .where(StoreCrawl.status == "ok", StoreCrawl.finished_at.is_not(None))
                           .group_by(StoreCrawl.source_id)).all()
    return {sid: aware(t) for sid, t in rows}


def is_new(p: Product, base: dict[int, datetime], now: datetime) -> bool:
    start = base.get(p.source_id)
    seen = aware(p.first_seen_at)
    return start is not None and seen > start and seen >= now - timedelta(days=NEW_DAYS)


def is_retired(p: Product, base: dict[int, datetime], now: datetime) -> bool:
    return (not p.is_active and p.dropped_at is not None and p.source_id in base
            and aware(p.dropped_at) >= now - timedelta(days=NEW_DAYS))


def retired_products(session: Session, now: datetime, base: dict[int, datetime] | None = None) -> list[tuple[Product, str]]:
    """(product, store name) for products a complete crawl dropped within the last NEW_DAYS."""
    base = baselines(session) if base is None else base
    rows = session.execute(select(Product, Source.name).join(Source, Source.id == Product.source_id)
                           .where(Product.is_active.is_(False), Product.dropped_at.is_not(None))).all()
    return [(p, store) for p, store in rows if is_retired(p, base, now)]


def is_creator(country: str | None) -> bool:
    return bool(country) and country != retail.MARKET_COUNTRY


def new_by_attribute(session: Session, now: datetime | None = None) -> dict:
    """What creator-brand catalogs added and dropped in the last NEW_DAYS, and which attributes the new frames lean to.

    {"stores": [{name, new, retired}], "new": n, "catalog": n, "retired": n,
     "items": [{dimension, code, new, share_new, share_catalog}]}  (items by number of new frames, largest first).
    Only creator-brand stores that have a baseline count, for both the new frames and the catalog they are compared to.
    `share_new`: share of the new frames carrying the attribute; `share_catalog`: share of the active catalog. Both are
    None below MIN_NEW_FOR_SHARES new frames."""
    now = now or datetime.now(timezone.utc)
    base = baselines(session)
    countries = dict(session.execute(select(Source.id, Source.country).where(Source.kind == "store")).all())
    scope = {sid for sid in base if is_creator(countries.get(sid))}
    active = [(p, store) for p, store in retail.active_products(session) if p.source_id in scope]
    fresh = [p for p, _ in active if is_new(p, base, now)]
    retired = [(p, store) for p, store in retired_products(session, now, base) if p.source_id in scope]

    per_store: dict[str, dict] = {}
    for p, store in active:
        per_store.setdefault(store, {"name": store, "new": 0, "retired": 0})["new"] += is_new(p, base, now)
    for _, store in retired:
        per_store.setdefault(store, {"name": store, "new": 0, "retired": 0})["retired"] += 1

    items: list[dict] = []
    if fresh:
        new_ids, catalog_ids = {p.id for p in fresh}, [p.id for p, _ in active]
        seen: set[tuple[int, str, str]] = set()
        in_new, in_catalog = Counter(), Counter()
        for pid, dim, code in session.execute(select(ProductTag.product_id, ProductTag.dimension, ProductTag.code)
                                              .where(ProductTag.dimension.in_(ATTRIBUTE_DIMENSIONS),
                                                     ProductTag.product_id.in_(catalog_ids))):
            if (pid, dim, code) in seen:  # a colour tag per variant code: count each frame once
                continue
            seen.add((pid, dim, code))
            in_catalog[dim, code] += 1
            in_new[dim, code] += pid in new_ids
        enough = len(fresh) >= MIN_NEW_FOR_SHARES
        order = {d: i for i, d in enumerate(ATTRIBUTE_DIMENSIONS)}
        items = [{"dimension": d, "code": c, "new": n,
                  "share_new": round(n / len(fresh), 4) if enough else None,
                  "share_catalog": round(in_catalog[d, c] / len(active), 4) if enough else None}
                 for (d, c), n in sorted(in_new.items(), key=lambda kv: (-kv[1], order[kv[0][0]], kv[0][1])) if n]
    return {"stores": sorted(per_store.values(), key=lambda s: s["name"]), "new": len(fresh), "catalog": len(active),
            "retired": len(retired), "items": items}


# --- store status (the Sources page panel) ---------------------------------------------------------

STATUS_LABELS_FR = {"ok": "À jour", "late": "En retard", "incomplete": "Incomplète", "failed": "Échec",
                    "manual": "Collecte manuelle", "never": "Jamais collectée"}


def store_status(session: Session, configs: dict[str, ScraperConfig], now: datetime | None = None) -> list[dict]:
    """One entry per configured store: product counts, how fresh its last complete crawl is, and a status:
    ok | late (last complete crawl older than LATE_FACTOR cadences) | incomplete / failed (the newest attempt, newer than
    the last complete crawl) | manual (products exist but the log has no crawl yet) | never."""
    now = now or datetime.now(timezone.utc)
    base = baselines(session)
    active = retail.active_products(session)
    retired = retired_products(session, now, base)
    out = []
    for cfg in configs.values():
        source = session.scalar(select(Source).where(Source.url == str(cfg.base_url)))
        sid = source.id if source else None
        mine = [p for p, _ in active if p.source_id == sid]

        def newest(*where) -> StoreCrawl | None:
            return session.scalar(select(StoreCrawl).where(StoreCrawl.source_id == sid, StoreCrawl.finished_at.is_not(None), *where)
                                  .order_by(StoreCrawl.finished_at.desc()).limit(1)) if sid else None

        last_ok = newest(StoreCrawl.status == "ok")
        last_try = newest(StoreCrawl.error.is_(None) | ~StoreCrawl.error.like("interrupted%"))  # a killed run says nothing
        ok_at = aware(last_ok.finished_at) if last_ok else None
        detail = None
        if last_try and last_try.status != "ok" and (ok_at is None or aware(last_try.finished_at) > ok_at):
            status = last_try.status
            detail = (last_try.problems or [None])[0] if status == "incomplete" else (last_try.error or "")[:200]
        elif ok_at is None:
            status = "manual" if mine else "never"
        elif now - ok_at > timedelta(days=cfg.crawl_every_days * LATE_FACTOR):
            status = "late"
        else:
            status = "ok"
        note = last_ok.drop_skipped if last_ok else None  # a shrink guard the operator should look at
        out.append({
            "name": cfg.name, "domain": cfg.domain, "country": cfg.country, "products": len(mine),
            "new": sum(is_new(p, base, now) for p in mine), "retired": sum(1 for p, _ in retired if p.source_id == sid),
            "creator": is_creator(cfg.country), "status": status, "status_label": STATUS_LABELS_FR[status],
            "detail": detail, "note": note, "cadence_days": cfg.crawl_every_days,
            "last_ok_at": ok_at.isoformat() if ok_at else None, "has_history": sid in base,
        })
    return out


# --- weekly brief ----------------------------------------------------------------------------------

BRIEF_ITEMS_PER_DIMENSION = 4


def _pct(share: float) -> str:
    return f"{round(share * 100)} %"


def catalog_brief(session: Session, now: datetime | None = None) -> list[str]:
    """The creator-brand section of the weekly brief; empty until a creator-brand store has a baseline."""
    data = new_by_attribute(session, now)
    if not data["stores"] and not data["catalog"]:
        return []
    tax = load_taxonomy()
    stores = " ; ".join(f"{s['name']} : {s['new']} nouveauté(s), {s['retired']} retirée(s)" for s in data["stores"])
    lines = ["", f"Nouveautés des catalogues créateurs ({NEW_DAYS} derniers jours) — indicateur avancé (ce que les marques "
                 f"mettent en catalogue) : {stores}."]
    if data["new"] < MIN_NEW_FOR_SHARES:
        lines.append(f"Trop peu de nouveautés ({data['new']}) pour parler de tendance : ne rien conclure de cette section.")
        return lines
    lines.append("Attributs des nouveautés (dimension | attribut | nouveautés | part des nouveautés | part du catalogue actif) :")
    by_dim: dict[str, list[dict]] = defaultdict(list)
    for item in data["items"]:
        by_dim[item["dimension"]].append(item)
    for dim in ATTRIBUTE_DIMENSIONS:
        for item in by_dim[dim][:BRIEF_ITEMS_PER_DIMENSION]:
            lines.append(f"{tax.dimension_labels[dim]} | {tax.label(dim, item['code'])} | {item['new']} | "
                         f"{_pct(item['share_new'])} | {_pct(item['share_catalog'])}")
    return lines
