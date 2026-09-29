"""Turn collected documents into taxonomy mentions."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

import anthropic
from sqlalchemy import and_, or_, select
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
def load_prompt(name: str, version: str | None = None) -> str:
    """prompts/<name>_<version>.md; the extraction prompt version unless another is given."""
    return (PROMPTS_DIR / f"{name}_{version or settings.prompt_version}.md").read_text(encoding="utf-8")


def extraction_system_prompt() -> str:
    return load_prompt("extract").replace("{taxonomy}", load_taxonomy().to_prompt())


def is_candidate(doc: Document) -> bool:
    return bool(EYEWEAR_RE.search(f"{doc.title}\n{doc.text}"))


def _user_message(doc: Document) -> str:
    return f"Source: {doc.source.name} ({doc.lang})\nTitre: {doc.title}\nURL: {doc.url}\n\n{doc.text}"


def _add_mentions(doc: Document, dim: str, found) -> None:
    """One mention per distinct code, dated on the article's publication (or collection) day."""
    day = (doc.published_at or doc.collected_at).date()
    seen: set[str] = set()
    for m in found:
        if m.code not in seen:
            seen.add(m.code)
            doc.mentions.append(Mention(dimension=dim, code=m.code, stance=m.stance, evidence=m.evidence, occurred_on=day))


def extract_document(session: Session, doc: Document, provider: LLMProvider) -> None:
    if not is_candidate(doc):
        doc.status = "irrelevant"
        return

    try:
        result = provider.extract(extraction_system_prompt(), _user_message(doc), extraction_model())
    except LLMRefused as e:
        log.warning("Refused doc %s: %s", doc.id, e)
        doc.status = "failed"
        return

    doc.prompt_version = settings.prompt_version
    if not result.is_relevant:
        doc.status = "irrelevant"
        return

    doc.mentions.clear()
    for dim in load_taxonomy().dimensions:
        _add_mentions(doc, dim, getattr(result, dim))
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


# --- re-reading one dimension after its taxonomy changed ------------------------------------------------

def reread_marker(doc: Document, dimension: str) -> str:
    """prompt_version of a document whose other dimensions come from its original prompt and this dimension from
    the current one, e.g. "v1+color@v2"."""
    return f"{doc.prompt_version or 'v?'}+{dimension}@{settings.prompt_version}"


def reread_query(dimension: str):
    """Extracted, non-demo documents whose `dimension` mentions predate the current prompt, oldest first."""
    current = settings.prompt_version
    return (select(Document)
            .where(Document.status == "extracted", Document.is_demo.is_(False),
                   or_(Document.prompt_version.is_(None),
                       and_(Document.prompt_version != current, Document.prompt_version.not_like(f"%+{dimension}@{current}"))))
            .order_by(Document.collected_at, Document.id))


def reread_dimension(session: Session, doc: Document, provider: LLMProvider, dimension: str) -> str:
    """Re-read one document for one dimension under the current prompt and taxonomy. Only that dimension's
    mentions are replaced: the other dimensions, brands and summary stay as first extracted, so their history
    does not move. Returns "reread", or "kept" when the model now calls the text not relevant (the old mentions
    stay: one different answer must not erase history)."""
    result = provider.extract(extraction_system_prompt(), _user_message(doc), extraction_model((dimension,)))
    marker = reread_marker(doc, dimension)
    if result.is_relevant:
        for m in [m for m in doc.mentions if m.dimension == dimension]:
            doc.mentions.remove(m)
        _add_mentions(doc, dimension, getattr(result, dimension))
    doc.prompt_version = marker
    return "reread" if result.is_relevant else "kept"


def reread_pending(session: Session, provider: LLMProvider, dimension: str, limit: int = 100) -> dict[str, int]:
    """Re-read up to `limit` documents (reread_query). Each one is committed as it is done, so a run stopped by
    a rate limit resumes where it stopped."""
    docs = session.scalars(reread_query(dimension).limit(limit)).all()
    stats = {"reread": 0, "kept": 0, "failed": 0}
    for doc in docs:
        try:
            stats[reread_dimension(session, doc, provider, dimension)] += 1
        except LLMRefused as e:
            log.warning("Refused doc %s: %s", doc.id, e)
            stats["failed"] += 1  # left unmarked: tried again next run
        except anthropic.RateLimitError:
            log.warning("Rate limited; stopping the re-read, remaining docs stay selectable")
            break
        except anthropic.APIConnectionError:
            log.warning("API unreachable; stopping the re-read")
            break
        except anthropic.APIStatusError as e:
            log.error("API error on doc %s: %s", doc.id, e)
            stats["failed"] += 1
        session.commit()
    stats["remaining"] = len(session.scalars(reread_query(dimension)).all())
    return stats
