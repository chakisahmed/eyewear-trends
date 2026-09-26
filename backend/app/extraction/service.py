"""Turn collected documents into taxonomy mentions."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.extraction.llm import LLMProvider, LLMRefused
from app.extraction.schema import extraction_model
from app.models import Document, Mention
from app.progress import Progress, report
from app.taxonomy import load_taxonomy

log = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).with_name("prompts")

# Free pre-filter before spending LLM tokens: the text must talk about eyewear at all.
EYEWEAR_RE = re.compile(
    r"\b(lunettes?|montures?|solaires|opticien|optique|eyewear|eyeglass(es)?|glasses|sunglasses|spectacles|frames?)\b",
    re.IGNORECASE,
)


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}_{settings.prompt_version}.md").read_text(encoding="utf-8")


def extraction_system_prompt() -> str:
    return load_prompt("extract").replace("{taxonomy}", load_taxonomy().to_prompt())


def is_candidate(doc: Document) -> bool:
    return bool(EYEWEAR_RE.search(f"{doc.title}\n{doc.text}"))


def extract_document(session: Session, doc: Document, provider: LLMProvider) -> None:
    if not is_candidate(doc):
        doc.status = "irrelevant"
        return

    user = f"Source: {doc.source.name} ({doc.lang})\nTitre: {doc.title}\nURL: {doc.url}\n\n{doc.text}"
    try:
        result = provider.extract(extraction_system_prompt(), user, extraction_model())
    except LLMRefused as e:
        log.warning("Refused doc %s: %s", doc.id, e)
        doc.status = "failed"
        return

    doc.prompt_version = settings.prompt_version
    if not result.is_relevant:
        doc.status = "irrelevant"
        return

    day = (doc.published_at or doc.collected_at).date()
    doc.mentions.clear()
    for dim in load_taxonomy().dimensions:
        seen: set[str] = set()
        for m in getattr(result, dim):
            if m.code in seen:
                continue
            seen.add(m.code)
            doc.mentions.append(
                Mention(dimension=dim, code=m.code, stance=m.stance, evidence=m.evidence, occurred_on=day)
            )
    doc.brands = sorted(set(result.brands))
    doc.summary_fr = result.summary_fr
    doc.status = "extracted"


def extract_pending(session: Session, provider: LLMProvider, limit: int = 100, progress: Progress = None) -> dict[str, int]:
    docs = session.scalars(
        select(Document).where(Document.status == "pending").order_by(Document.collected_at).limit(limit)
    ).all()
    stats = {"extracted": 0, "irrelevant": 0, "failed": 0}
    for i, doc in enumerate(docs):
        report(progress, i, len(docs))  # articles analysed so far
        try:
            extract_document(session, doc, provider)
        except anthropic.RateLimitError:
            log.warning("Rate limited; stopping extraction run, remaining docs stay pending")
            break
        except anthropic.APIConnectionError:
            log.warning("API unreachable; stopping extraction run")
            break
        except anthropic.APIStatusError as e:
            log.error("API error on doc %s: %s", doc.id, e)
            doc.status = "failed"
        stats[doc.status] = stats.get(doc.status, 0) + 1
        session.commit()
    else:
        report(progress, len(docs), len(docs))
    return stats
