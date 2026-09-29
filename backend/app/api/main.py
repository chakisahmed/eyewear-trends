from __future__ import annotations

import csv
import io
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_session, init_db
from app.jobs.pipeline import ALL_STEPS, active_run, execute_run, interrupt_orphaned_runs, start_run
from app.models import Document, JobRun, Mention, Product, ProductTag, SearchInterest, Source, TrendSnapshot, WeeklySummary
from app.scoring import retail
from app.scoring.summary import latest_week
from app.demo import clear_demo, seed_demo
from app.scoring.trends import FALLING, compute_snapshots, week_start
from app.taxonomy import load_taxonomy


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as session:
        interrupt_orphaned_runs(session)  # runs from a previous process died with it
    yield


app = FastAPI(title="Eyewear Trends API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=["*"], allow_headers=["*"])
DB = Annotated[Session, Depends(get_session)]

SPARK_WEEKS = 8
STATUS_FR = {"en_hausse": "En hausse", "au_pic": "Au pic", "stable": "Stable", "en_baisse": "En baisse", "faible": "Peu de données"}
DIM_SLUG = {"shape": "formes", "color": "couleurs", "material": "matieres", "style": "styles"}


# ---------- helpers ----------

def _item(dim: str, code: str) -> dict:
    it = load_taxonomy().get(dim, code)
    return {"code": code, "label": it.label_fr, "hex": it.hex, **({"multicolor": True} if it.multicolor else {})}


def _check_dimension(dimension: str) -> None:
    if dimension not in load_taxonomy().dimensions:
        raise HTTPException(404, f"Dimension inconnue : '{dimension}'")


def _resolve_week(db: Session, week: date | None) -> date | None:
    """The requested week (normalized to its Monday), or the latest scored week."""
    if week is None:
        return latest_week(db)
    ws = week_start(week)
    if not db.scalar(select(func.count()).select_from(TrendSnapshot).where(TrendSnapshot.week == ws)):
        raise HTTPException(404, f"Aucune donnée pour la semaine du {ws.isoformat()}")
    return ws


def _week_list(end: date, n: int) -> list[date]:
    return [end - timedelta(weeks=k) for k in range(n - 1, -1, -1)]


def _snapshot_grid(db: Session, end: date, n: int, dimension: str | None = None) -> dict[tuple[str, str], dict[date, TrendSnapshot]]:
    q = select(TrendSnapshot).where(TrendSnapshot.week >= end - timedelta(weeks=n - 1), TrendSnapshot.week <= end)
    if dimension:
        q = q.where(TrendSnapshot.dimension == dimension)
    grid: dict[tuple[str, str], dict[date, TrendSnapshot]] = {}
    for s in db.scalars(q):
        grid.setdefault((s.dimension, s.code), {})[s.week] = s
    return grid


def _mention_row(m: Mention, d: Document, s: Source) -> dict:
    return {
        **_item(m.dimension, m.code), "dimension": m.dimension, "stance": m.stance, "evidence": m.evidence,
        "date": m.occurred_on.isoformat(), "title": d.title, "url": d.url, "summary": d.summary_fr,
        "lang": d.lang, "source": s.name, "kind": s.kind, "is_demo": d.is_demo,
    }


def _mentions_query(dimension=None, code=None, lang=None, kind=None, since: date | None = None, until: date | None = None):
    q = (
        select(Mention, Document, Source)
        .join(Document, Mention.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
    )
    if dimension:
        q = q.where(Mention.dimension == dimension)
    if code:
        q = q.where(Mention.code == code)
    if lang:
        q = q.where(Document.lang == lang)
    if kind:
        q = q.where(Source.kind == kind)
    if since:
        q = q.where(Mention.occurred_on >= since)
    if until:
        q = q.where(Mention.occurred_on <= until)
    return q


def _aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


STEP_LABELS = {
    "rss": "Presse (flux RSS et sitemaps)", "news": "Actualités", "google_trends": "Google Trends",
    "extract": "Analyse IA", "score": "Calcul des tendances", "summary": "Résumé IA",
}


def _run_dict(run: JobRun | None) -> dict | None:
    if run is None:
        return None
    steps = run.steps or []
    step = run.current_step
    return {
        "id": run.id, "status": run.status, "trigger": run.trigger, "steps": steps,
        "started_at": _aware(run.started_at).isoformat(),
        "finished_at": _aware(run.finished_at).isoformat() if run.finished_at else None,
        "report": run.report, "error": run.error,
        "progress": {
            "step": step,
            "label": STEP_LABELS.get(step, step) if step else None,
            "index": steps.index(step) + 1 if step in steps else None,  # 1-based position of the step
            "count": len(steps),
            "done": run.step_done,
            "total": run.step_total,
        },
    }


def _tone_fields(s: TrendSnapshot | None) -> dict:
    """Tone plus why a trend is "en baisse": its volume fell, or its coverage calls it fading."""
    if s is None:
        return {"tone": None, "decline_share": None, "decline_reason": None}
    reason = None
    if s.status == "en_baisse":
        reason = "volume" if s.momentum <= FALLING else "tonalite"
    return {"tone": s.tone, "decline_share": s.decline_share, "decline_reason": reason}


def _decline_severity(s: TrendSnapshot) -> float:
    # most negative first: a −40 % volume drop and 70 % "fading" coverage rank on one scale
    return min(s.momentum, -(s.decline_share or 0.0))


def _fr_number(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


# ---------- routes ----------

@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/taxonomy")
def taxonomy() -> dict:
    return load_taxonomy().to_public()


@app.get("/api/meta")
def meta(db: DB) -> dict:
    """Everything the app shell needs on every page, in one cheap call."""
    last_success = db.scalar(select(JobRun).where(JobRun.status == "success").order_by(JobRun.finished_at.desc()))
    return {
        "has_demo": bool(db.scalar(select(func.count()).select_from(Document).where(Document.is_demo))),
        "weeks": [w.isoformat() for w in db.scalars(select(TrendSnapshot.week).distinct().order_by(TrendSnapshot.week.desc()))],
        "running": active_run(db) is not None,
        "last_success": _run_dict(last_success),
        "market_geo": settings.market_geo,
    }


@app.get("/api/weeks")
def weeks(db: DB) -> list[str]:
    """Scored weeks, newest first — feeds the week selector."""
    return [w.isoformat() for w in db.scalars(select(TrendSnapshot.week).distinct().order_by(TrendSnapshot.week.desc()))]


@app.get("/api/overview")
def overview(db: DB, week: date | None = None, top: int = Query(5, ge=1, le=20)) -> dict:
    end = _resolve_week(db, week)
    stats = {
        "documents": db.scalar(select(func.count()).select_from(Document).where(Document.status == "extracted")) or 0,
        "mentions": db.scalar(select(func.count()).select_from(Mention)) or 0,
        "sources": db.scalar(select(func.count()).select_from(Source).where(Source.active)) or 0,  # feeds.yaml drives press
        "pending": db.scalar(select(func.count()).select_from(Document).where(Document.status == "pending")) or 0,
    }
    has_demo = bool(db.scalar(select(func.count()).select_from(Document).where(Document.is_demo)))
    tax = load_taxonomy()
    if end is None:
        return {"week": None, "stats": stats, "has_demo": has_demo, "dimension_labels": tax.dimension_labels,
                "rising": {}, "declining": [], "summary": None}

    grid = _snapshot_grid(db, end, SPARK_WEEKS)
    spark_weeks = _week_list(end, SPARK_WEEKS)

    def row(dim: str, s: TrendSnapshot) -> dict:
        cells = grid.get((dim, s.code), {})
        return {**_item(dim, s.code), "dimension": dim, "mentions": s.mentions, "momentum": s.momentum,
                "status": s.status, **_tone_fields(s), "spark": [cells[w].mentions if w in cells else 0.0 for w in spark_weeks]}

    current = [cells[end] for cells in grid.values() if end in cells]
    rising = {
        dim: [row(dim, s) for s in sorted(
            (s for s in current if s.dimension == dim and s.mentions > 0 and s.status != "en_baisse"),
            key=lambda s: (s.status == "faible", -s.momentum),  # too-little-data attributes go last, whatever their %
        )[:top]]
        for dim in tax.dimensions
    }
    declining = [row(s.dimension, s) for s in sorted((s for s in current if s.status == "en_baisse"), key=_decline_severity)[:top]]
    summary = db.scalar(select(WeeklySummary).where(WeeklySummary.week == end))
    return {
        "week": end.isoformat(),
        "stats": stats,
        "has_demo": has_demo,
        "dimension_labels": tax.dimension_labels,
        "rising": rising,
        "declining": declining,
        "summary": {"text": summary.text_fr, "model": summary.model} if summary else None,
    }


@app.get("/api/trends/{dimension}")
def trends(dimension: str, db: DB, week: date | None = None, weeks: int = Query(12, ge=2, le=52)) -> dict:
    _check_dimension(dimension)
    end = _resolve_week(db, week)
    if end is None:
        return {"week": None, "weeks": [], "series": []}
    week_list = _week_list(end, weeks)
    series = []
    for (_, code), cells in _snapshot_grid(db, end, weeks, dimension).items():
        last = cells.get(end)
        series.append({
            **_item(dimension, code),
            "mentions": [cells[w].mentions if w in cells else 0 for w in week_list],
            "search": [cells[w].search if w in cells else None for w in week_list],
            "momentum": last.momentum if last else 0,
            "status": last.status if last else "stable",
            **_tone_fields(last),
            "share": 0.0,
        })
    total = sum(s["mentions"][-1] for s in series) or 1
    for s in series:
        s["share"] = s["mentions"][-1] / total
    series.sort(key=lambda s: -s["mentions"][-1])
    return {"week": end.isoformat(), "weeks": [w.isoformat() for w in week_list], "series": series}


RETAIL_SAMPLE_SIZE = 5


def _retail_presence(db: Session, dimension: str, code: str) -> dict:
    """"Présence en boutique": store products tagged with this attribute (rule-based tags, no LLM)."""
    tagged = set(db.scalars(select(ProductTag.product_id).where(ProductTag.dimension == dimension, ProductTag.code == code)))
    rows = [(p, store) for p, store in retail.active_products(db) if p.id in tagged]
    ids = [p.id for p, _ in rows]
    types = Counter(db.scalars(select(ProductTag.code).where(ProductTag.product_id.in_(ids), ProductTag.dimension == "product_type")))
    # Which markets these products come from (Tunisian retailers, a Spanish brand catalog…): the UI titles the section
    countries = sorted(set(db.scalars(select(Source.country).where(
        Source.id.in_({p.source_id for p, _ in rows}), Source.country.is_not(None)))))

    prices: dict[str, list[float]] = {}
    for p, _ in rows:
        if p.price and p.price > 0 and p.currency:
            prices.setdefault(p.currency, []).append(p.price)

    def out_of_stock(p: Product) -> bool:
        return bool((p.flags or {}).get("out_of_stock"))

    def bestseller(p: Product) -> bool:  # the store's own best-seller flag (frame level), when it publishes one
        return bool((p.flags or {}).get("is_bestseller"))

    # In stock first, then the store's best-sellers, then its own listing order; round-robin so one store cannot
    # fill the sample.
    per_store: dict[str, list[Product]] = {}
    for p, store in sorted(rows, key=lambda r: (r[1], out_of_stock(r[0]), not bestseller(r[0]), r[0].rank or 10**9, r[0].name)):
        per_store.setdefault(store, []).append(p)
    queues = [[(p, store) for p in items] for store, items in per_store.items()]
    sample = []
    while len(sample) < RETAIL_SAMPLE_SIZE and any(queues):
        for q in queues:
            if q and len(sample) < RETAIL_SAMPLE_SIZE:
                sample.append(q.pop(0))

    updated = max((p.seen_at for p, _ in rows), default=None)
    return {
        "retail_sku_count": len(rows),
        "retail_store_count": len(per_store),
        "retail_bestseller_count": sum(1 for p, _ in rows if bestseller(p)),
        "retail_countries": countries,  # ISO codes of the stores counted, e.g. ["ES", "TN"]
        "retail_avg_price": [
            {"currency": cur, "avg": round(mean(v), 2), "min": min(v), "max": max(v), "priced": len(v)}
            for cur, v in sorted(prices.items(), key=lambda kv: -len(kv[1]))
        ],
        "retail_by_type": {k: types[k] for k in ("optical", "sun") if types.get(k)},
        "retail_sample": [
            {"name": p.name, "brand": p.brand, "price": p.price, "currency": p.currency, "image_url": p.image_url,
             "url": p.url, "store": store, "out_of_stock": out_of_stock(p), "is_bestseller": bestseller(p)}
            for p, store in sample
        ],
        "retail_updated_at": (updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)).isoformat() if updated else None,
        # discount signal vs each store's usual markdown; None when no tracked store publishes list prices
        "retail_markdown": retail.attribute_markdown(db, dimension, code),
    }


@app.get("/api/trends/{dimension}/{code}")
def trend_detail(dimension: str, code: str, db: DB, week: date | None = None, weeks: int = Query(12, ge=4, le=52)) -> dict:
    _check_dimension(dimension)
    tax = load_taxonomy()
    if code not in tax.codes(dimension):
        raise HTTPException(404, f"Attribut inconnu : '{code}'")
    end = _resolve_week(db, week)
    base = {**_item(dimension, code), "dimension": dimension, "dimension_label": tax.dimension_labels[dimension]}
    retail = _retail_presence(db, dimension, code)
    if end is None:
        return {**base, "week": None, **retail}

    week_list = _week_list(end, weeks)
    grid = _snapshot_grid(db, end, weeks, dimension)
    cells = grid.get((dimension, code), {})
    mentions = [cells[w].mentions if w in cells else 0.0 for w in week_list]
    last = cells.get(end)

    # Consecutive weeks "en hausse", ending this week
    streak = 0
    for w in reversed(week_list):
        if w in cells and cells[w].status == "en_hausse":
            streak += 1
        else:
            break
    dim_total = sum(c[end].mentions for c in grid.values() if end in c) or 0

    # Google Trends, France (market geo) vs worldwide
    search = {"fr": [None] * weeks, "world": [None] * weeks}
    index = {w: i for i, w in enumerate(week_list)}
    for si in db.scalars(select(SearchInterest).where(SearchInterest.code == code, SearchInterest.week >= week_list[0], SearchInterest.week <= end)):
        i = index.get(week_start(si.week))
        if i is not None:
            search["fr" if si.geo else "world"][i] = round(si.value, 1)
    latest_fr = next((v for v in reversed(search["fr"]) if v is not None), None)

    # Tone and co-mentioned brands over the last 4 weeks
    since = end - timedelta(weeks=3)
    until = end + timedelta(days=6)
    stance = Counter(
        m.stance for m, _, _ in db.execute(_mentions_query(dimension, code, since=since, until=until)).all()
    )
    brand_counts: Counter[str] = Counter()
    doc_ids = select(Mention.document_id).where(
        Mention.dimension == dimension, Mention.code == code, Mention.occurred_on >= since, Mention.occurred_on <= until
    )
    # Subquery instead of DISTINCT: Postgres cannot DISTINCT over a JSON column.
    for brands in db.scalars(select(Document.brands).where(Document.id.in_(doc_ids))):
        brand_counts.update(brands or [])

    evidence = db.execute(
        _mentions_query(dimension, code, until=until).order_by(Mention.occurred_on.desc(), Mention.id.desc()).limit(10)
    ).all()
    return {
        **base,
        "week": end.isoformat(),
        "weeks": [w.isoformat() for w in week_list],
        "mentions": mentions,
        "momentum": last.momentum if last else 0.0,
        "status": last.status if last else "stable",
        **_tone_fields(last),
        "rising_streak": streak,
        "stats": {
            "this_week": mentions[-1],
            "avg_4w": round(mean(mentions[-5:-1]), 2) if len(mentions) >= 5 else None,
            "share": round(mentions[-1] / dim_total, 4) if dim_total else 0.0,
            "search_fr": latest_fr,
        },
        "search": search,
        "stance": {"rising": stance.get("rising", 0), "neutral": stance.get("neutral", 0), "declining": stance.get("declining", 0)},
        "brands": [{"name": b, "count": n} for b, n in brand_counts.most_common(10)],
        "evidence": [_mention_row(m, d, s) for m, d, s in evidence],
        **retail,
    }


@app.get("/api/retail/overview")
def retail_overview(db: DB, week: date | None = None) -> dict:
    """Tunisian shelf vs press signal for the report: tracked stores, opportunities, stock risks."""
    end = _resolve_week(db, week)
    shelf = retail.shelf_by_attribute(db)
    gaps = retail.shelf_gaps_by_type(db, end) if end else {
        "opportunities": [], "risks": [], "types": {t: 0 for t in retail.PRODUCT_TYPES},
        "skipped_dimensions": {t: list(retail.DIMENSIONS) for t in retail.PRODUCT_TYPES}}
    iso = lambda d: (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).isoformat()
    return {
        "week": end.isoformat() if end else None,
        "stores": [{"name": st["name"], "products": st["products"], "updated": iso(st["updated"])} for st in shelf["stores"]],
        "types": gaps["types"],  # active products per shelf: {"optical": n, "sun": n}
        "opportunities": gaps["opportunities"],
        "risks": gaps["risks"],
        "skipped_dimensions": gaps["skipped_dimensions"],
        "thresholds": {"opportunity_share": retail.OPPORTUNITY_SHARE, "risk_share": retail.RISK_SHARE, "min_tagged": retail.MIN_TAGGED},
    }


@app.get("/api/demand/{dimension}")
def demand(dimension: str, db: DB) -> dict:
    _check_dimension(dimension)
    rows = db.scalars(select(SearchInterest).where(SearchInterest.dimension == dimension).order_by(SearchInterest.week)).all()
    weeks = sorted({r.week for r in rows})
    out: dict[str, dict] = {}
    for r in rows:
        entry = out.setdefault(r.code, {**_item(dimension, r.code), "fr": {}, "world": {}})
        entry["fr" if r.geo else "world"][r.week] = round(r.value, 1)
    series = [
        {**{k: v for k, v in e.items() if k not in ("fr", "world")},
         "fr": [e["fr"].get(w) for w in weeks], "world": [e["world"].get(w) for w in weeks]}
        for e in out.values()
    ]
    return {"weeks": [w.isoformat() for w in weeks], "geo": settings.market_geo, "series": series}


@app.get("/api/mentions")
def mentions(
    db: DB,
    dimension: str | None = None,
    code: str | None = None,
    lang: str | None = None,
    kind: str | None = None,
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    since = date.today() - timedelta(days=days) if days else None
    q = _mentions_query(dimension, code, lang, kind, since=since)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.execute(q.order_by(Mention.occurred_on.desc(), Mention.id.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [_mention_row(m, d, s) for m, d, s in rows]}


@app.get("/api/sources")
def sources(
    db: DB,
    dimension: str | None = None,
    code: str | None = None,
    lang: str | None = None,
    kind: str | None = None,
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(6, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> dict:
    """One item per article/post/product (not per attribute), with all its detected attributes.

    Attribute filters (dimension, code, days) select documents having at least one matching mention;
    the quote shown is that matching mention's evidence.
    """
    since = date.today() - timedelta(days=days) if days else None
    matching = select(Mention.document_id)
    if dimension:
        matching = matching.where(Mention.dimension == dimension)
    if code:
        matching = matching.where(Mention.code == code)
    if since:
        matching = matching.where(Mention.occurred_on >= since)
    q = (
        select(Document, Source)
        .join(Source, Document.source_id == Source.id)
        .where(Document.status == "extracted", Document.id.in_(matching))
    )
    if lang:
        q = q.where(Document.lang == lang)
    if kind:
        q = q.where(Source.kind == kind)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    when = func.coalesce(Document.published_at, Document.collected_at)
    rows = db.execute(q.order_by(when.desc(), Document.id.desc()).limit(limit).offset(offset)).all()

    items = []
    for d, s in rows:
        seen: set[tuple[str, str]] = set()
        attrs, quote = [], None
        for m in sorted(d.mentions, key=lambda m: (m.dimension, m.code)):
            if (m.dimension, m.code) in seen:
                continue
            seen.add((m.dimension, m.code))
            attrs.append({**_item(m.dimension, m.code), "dimension": m.dimension, "stance": m.stance})
            if quote is None and (not dimension or m.dimension == dimension) and (not code or m.code == code):
                quote = m.evidence
        published = _aware(d.published_at or d.collected_at)
        items.append({
            "id": d.id, "url": d.url, "title": d.title, "source": s.name, "kind": s.kind, "lang": d.lang,
            "date": published.date().isoformat() if published else None,
            "quote": quote, "summary": d.summary_fr, "attributes": attrs, "is_demo": d.is_demo,
        })
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@app.post("/api/demo", status_code=201)
def load_demo(db: DB) -> dict:
    """Load synthetic demo data (flagged is_demo) so the dashboard can be explored before real data."""
    if active_run(db):
        raise HTTPException(409, "Une collecte est en cours")
    return {"documents": seed_demo(db), "snapshots": compute_snapshots(db)}


@app.delete("/api/demo")
def remove_demo(db: DB) -> dict:
    """Remove every demo row and rescore from real data only."""
    if active_run(db):
        raise HTTPException(409, "Une collecte est en cours")
    clear_demo(db)
    return {"snapshots": compute_snapshots(db)}


@app.get("/api/export/{dimension}.csv")
def export_csv(dimension: str, db: DB, week: date | None = None) -> Response:
    """Excel-friendly French CSV: ';' separator, decimal comma, UTF-8 with BOM."""
    _check_dimension(dimension)
    end = _resolve_week(db, week)
    if end is None:
        raise HTTPException(404, "Aucune donnée à exporter")
    snaps = db.scalars(select(TrendSnapshot).where(TrendSnapshot.dimension == dimension, TrendSnapshot.week == end)).all()
    total = sum(s.mentions for s in snaps) or 1
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(["Attribut", "Code", "Semaine", "Mentions pondérées", "Part (%)", "Momentum (%)", "Statut",
                "Avis « en recul » sur 4 sem. (%)", "Intérêt de recherche (0-100)"])
    for s in sorted(snaps, key=lambda s: -s.mentions):
        w.writerow([
            load_taxonomy().label(dimension, s.code), s.code, end.isoformat(), _fr_number(s.mentions),
            _fr_number(100 * s.mentions / total), _fr_number(100 * s.momentum, 0), STATUS_FR.get(s.status, s.status),
            _fr_number(100 * s.decline_share, 0) if s.decline_share is not None else "",
            _fr_number(s.search) if s.search is not None else "",
        ])
    filename = f"tendances-{DIM_SLUG.get(dimension, dimension)}-{end.isoformat()}.csv"
    return Response(
        content="﻿" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class RunRequest(BaseModel):
    steps: list[str] = list(ALL_STEPS)


@app.post("/api/jobs/run", status_code=202)
def run_job(req: RunRequest, background: BackgroundTasks, db: DB) -> dict:
    unknown = set(req.steps) - set(ALL_STEPS)
    if unknown:
        raise HTTPException(400, f"Étapes inconnues : {sorted(unknown)}")
    if active_run(db):
        raise HTTPException(409, "Une collecte est déjà en cours")
    run = start_run(db, tuple(req.steps), trigger="manual")
    background.add_task(execute_run, run.id)
    return _run_dict(run)


@app.get("/api/jobs/status")
def job_status(db: DB) -> dict:
    current = active_run(db)
    last = db.scalar(select(JobRun).where(JobRun.status != "running").order_by(JobRun.started_at.desc()))
    last_success = db.scalar(select(JobRun).where(JobRun.status == "success").order_by(JobRun.finished_at.desc()))
    return {"running": current is not None, "current": _run_dict(current), "last": _run_dict(last), "last_success": _run_dict(last_success)}
