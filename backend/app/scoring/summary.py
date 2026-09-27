"""AI-written weekly summary in French, grounded only in computed scores."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.extraction.llm import LLMProvider
from app.extraction.service import load_prompt
from app.models import Document, Mention, TrendSnapshot, WeeklySummary
from app.scoring.retail import (
    MIN_TAGGED, PRODUCT_TYPES, TYPE_LABELS, comparable, shelf_by_attribute, shelf_gaps_by_type, unmapped_share,
)
from app.taxonomy import load_taxonomy


def latest_week(session: Session) -> date | None:
    return session.scalar(select(func.max(TrendSnapshot.week)))


def build_brief(session: Session, week: date) -> str:
    tax = load_taxonomy()
    snaps = session.scalars(select(TrendSnapshot).where(TrendSnapshot.week == week)).all()
    # Sample size behind each score: weighted mentions over the last 4 weeks.
    volume_4w: dict[tuple[str, str], float] = {}
    for s in session.scalars(select(TrendSnapshot).where(TrendSnapshot.week > week - timedelta(weeks=4), TrendSnapshot.week <= week)):
        volume_4w[(s.dimension, s.code)] = volume_4w.get((s.dimension, s.code), 0.0) + s.mentions

    def line(s: TrendSnapshot) -> str:
        fading = f"{s.decline_share:.0%}" if s.decline_share is not None else "n/d"
        return (f"{tax.dimension_labels[s.dimension]} | {tax.label(s.dimension, s.code)} | {s.mentions:.1f} | "
                f"{volume_4w.get((s.dimension, s.code), 0.0):.0f} | {s.momentum:+.0%} | {s.status} | {fading}")

    ranked = sorted((s for s in snaps if s.mentions > 0 or s.search), key=lambda s: -s.momentum)
    lines = [
        f"Semaine du {week.isoformat()}", "",
        "Scores (dimension | attribut | mentions pondérées cette semaine | mentions sur 4 sem. | momentum du volume | statut | part des avis « en recul » sur 4 sem.):",
        *[line(s) for s in ranked if s.status != "faible"],
    ]
    weak = [line(s) for s in ranked if s.status == "faible"]
    if weak:
        lines += ["", "Signaux faibles (trop peu de mentions pour conclure, à citer seulement comme « à surveiller ») :", *weak]
    extracts = session.scalars(
        select(Document.summary_fr)
        .join(Mention)
        .where(Mention.occurred_on >= week, Document.summary_fr.is_not(None))
        .distinct()
        .limit(12)
    ).all()
    if extracts:
        lines += ["", "Extraits de sources:"] + [f"- {e}" for e in extracts]
    lines += shelf_brief(session, week)
    return "\n".join(lines)


STATUS_WORDS = {"en_hausse": "en hausse", "au_pic": "au pic", "en_baisse": "en baisse", "stable": "stable"}


def _relative(md: dict | None) -> str:
    """Markdown vs the store's usual sale, e.g. "+34 pts vs habituelle"; "n/d" when no store publishes list prices."""
    return "n/d" if md is None else f"{md['relative_depth'] * 100:+.0f} pts vs habituelle"


def _pct(share: float) -> str:
    return f"{round(share * 100)} %"


def shelf_brief(session: Session, week: date) -> list[str]:
    """The Tunisian shelf (lagging indicator) next to the press scores, one shelf per product type
    (prescription vs sunglasses: their shape mix differs); empty without store data."""
    everything = shelf_by_attribute(session)
    if not everything["stores"]:
        return []
    tax = load_taxonomy()
    stores = ", ".join(f"{st['name']} ({st['products']} réf.)" for st in everything["stores"])
    lines = ["", f"Marché tunisien — enseignes suivies : {stores}. Indicateur retardé (ce qui est déjà en rayon), "
             "à comparer au signal presse international ci-dessus (indicateur avancé)."]
    gaps = shelf_gaps_by_type(session, week)
    for product_type in PRODUCT_TYPES:
        shelf, label = gaps["shelves"][product_type], TYPE_LABELS[product_type]
        if not gaps["types"][product_type]:
            lines.append(f"Rayon {label} : couverture insuffisante (aucune référence suivie), pas de comparaison.")
            continue
        lines.append(f"Rayon {label} — {gaps['types'][product_type]} références (dimension | attribut | références "
                     "en rayon | part du rayon de la dimension | prix moyen | remise vs remise habituelle de l'enseigne) :")
        for dim, data in shelf["dimensions"].items():
            if not comparable(data):
                why = (f"{data['tagged']} références renseignées" if data["tagged"] < MIN_TAGGED
                       else f"vocabulaire des boutiques non reconnu pour {_pct(unmapped_share(data))} des valeurs")
                lines.append(f"{tax.dimension_labels[dim]} : couverture insuffisante ({why}), pas de comparaison.")
                continue
            for code, item in sorted(data["items"].items(), key=lambda kv: -kv[1]["sku"])[:6]:
                price = " / ".join(f"{v:.0f} {cur}" for cur, v in item["avg_price"].items()) or "n/d"
                lines.append(f"{tax.dimension_labels[dim]} | {tax.label(dim, code)} | {item['sku']} | {_pct(item['share'])} | {price}"
                             f" | {_relative(item['markdown'])}")
    if gaps["opportunities"] or gaps["risks"]:
        lines.append("Écarts presse / rayon (calculés, par type de rayon) :")
        lines += [f"Opportunité ({TYPE_LABELS[g['product_type']]}) : {g['label']} ({tax.dimension_labels[g['dimension']]}) — "
                  f"{STATUS_WORDS.get(g['status'], g['status'])} dans la presse ({g['momentum']:+.0%}), "
                  f"{g['sku']} référence(s) en rayon ({_pct(g['share'])})" for g in gaps["opportunities"][:3]]
        lines += [f"Risque de stock ({TYPE_LABELS[g['product_type']]}) : {g['label']} ({tax.dimension_labels[g['dimension']]}) — "
                  f"en baisse dans la presse ({g['momentum']:+.0%}), {g['sku']} références en rayon ({_pct(g['share'])})"
                  + (f", déstockage : remise {_relative(g['markdown'])}" if g["clearance"] else "")
                  for g in gaps["risks"][:3]]
    return lines


def generate_weekly_summary(session: Session, provider: LLMProvider, week: date | None = None) -> WeeklySummary | None:
    week = week or latest_week(session)
    if week is None:
        return None
    text = provider.write(load_prompt("summary_fr"), build_brief(session, week))
    row = session.scalar(select(WeeklySummary).where(WeeklySummary.week == week))
    if row is None:
        row = WeeklySummary(week=week, text_fr=text, model=settings.summary_model)
        session.add(row)
    else:
        row.text_fr, row.model = text, settings.summary_model
    session.commit()
    return row
