"""Re-reading one dimension (colors) after its taxonomy changed: only that dimension's mentions move, the rest of
the history stays as first extracted. Fake provider: nothing reaches Claude."""

from datetime import date, datetime, timezone

import anthropic
import httpx
import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.extraction.llm as llm
from app.cli import cli
from app.config import settings
from app.db import Base, SessionLocal, init_db
from app.extraction.service import load_prompt, reread_pending, reread_query
from app.models import Document, Mention, Source

PUBLISHED = datetime(2026, 8, 24, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


class FakeProvider:
    """answers: article title -> list of (code, stance, evidence) color mentions, or None for "not relevant".
    rate_limit_on: titles that raise RateLimitError."""

    def __init__(self, answers: dict, rate_limit_on: tuple[str, ...] = ()):
        self.answers, self.rate_limit_on, self.calls = answers, rate_limit_on, []

    def extract(self, system, user, schema):
        title = user.split("\nTitre: ", 1)[1].split("\n", 1)[0]
        self.calls.append((title, system, schema))
        if title in self.rate_limit_on:
            raise anthropic.RateLimitError("rate limited", response=httpx.Response(
                429, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")), body=None)
        found = self.answers[title]
        return schema.model_validate({"is_relevant": found is not None, "language": "en", "color": [
            {"code": c, "stance": st, "evidence": ev} for c, st, ev in found or []]})


def article(s, title: str, *, prompt_version="v1", status="extracted", is_demo=False, collected=None) -> Document:
    source = s.scalar(select(Source).where(Source.name == "Trade press")) or Source(
        name="Trade press", kind="press", url="https://press.test/feed", lang="en")
    doc = Document(source=source, url=f"https://press.test/{title}", title=title, lang="en", status=status,
                   text="New eyewear frames: available in khaki, blue and black.", published_at=PUBLISHED,
                   collected_at=collected or PUBLISHED, prompt_version=prompt_version, is_demo=is_demo,
                   brands=["Moscot"], summary_fr="Une phrase.")
    doc.mentions = [
        Mention(dimension="color", code="black", stance="neutral", evidence="khaki, blue and black", occurred_on=PUBLISHED.date()),
        Mention(dimension="shape", code="round", stance="rising", evidence="round frames", occurred_on=PUBLISHED.date()),
        Mention(dimension="material", code="acetate", stance="neutral", evidence="acetate", occurred_on=PUBLISHED.date()),
    ]
    s.add(doc)
    s.commit()
    return doc


def mentions(doc: Document, dimension: str) -> set[tuple]:
    return {(m.code, m.stance, m.evidence) for m in doc.mentions if m.dimension == dimension}


def test_only_color_mentions_are_replaced_and_the_rest_of_the_article_is_untouched(s):
    doc = article(s, "khaki-blue-black")
    others = {(m.id, m.dimension, m.code) for m in doc.mentions if m.dimension != "color"}
    provider = FakeProvider({"khaki-blue-black": [("gold", "rising", "gold temples"), ("clear", "neutral", "crystal"),
                                                  ("gold", "neutral", "duplicate code")]})

    assert reread_pending(s, provider, "color") == {"reread": 1, "kept": 0, "failed": 0, "remaining": 0}
    s.refresh(doc)
    assert mentions(doc, "color") == {("gold", "rising", "gold temples"), ("clear", "neutral", "crystal")}  # one per code
    assert all(m.occurred_on == date(2026, 8, 24) for m in doc.mentions)
    assert {(m.id, m.dimension, m.code) for m in doc.mentions if m.dimension != "color"} == others  # same rows
    assert (doc.brands, doc.summary_fr, doc.status) == (["Moscot"], "Une phrase.", "extracted")
    assert doc.prompt_version == f"v1+color@{settings.prompt_version}"

    (_, system, schema), = provider.calls
    assert set(schema.model_fields) == {"is_relevant", "language", "color"}          # colors only: a small answer
    assert "Colors:" in system and "- black:" in system                              # current prompt + taxonomy


def test_a_second_run_selects_nothing_and_spends_nothing(s):
    article(s, "once")
    provider = FakeProvider({"once": [("black", "neutral", "black")]})
    reread_pending(s, provider, "color")
    assert reread_pending(s, provider, "color") == {"reread": 0, "kept": 0, "failed": 0, "remaining": 0}
    assert len(provider.calls) == 1


def test_only_older_non_demo_extracted_articles_are_selected(s):
    article(s, "old")
    article(s, "current", prompt_version=settings.prompt_version)         # already analysed with this prompt
    article(s, "demo", is_demo=True)
    article(s, "irrelevant", status="irrelevant")
    article(s, "pending", status="pending", prompt_version=None)
    article(s, "no-version", prompt_version=None)
    assert [d.title for d in s.scalars(reread_query("color"))] == ["old", "no-version"]
    assert [d.title for d in s.scalars(reread_query("material"))] == ["old", "no-version"]  # markers are per dimension


def test_a_not_relevant_answer_keeps_the_old_colors(s):
    doc = article(s, "flaky")
    stats = reread_pending(s, FakeProvider({"flaky": None}), "color")
    s.refresh(doc)
    assert stats["kept"] == 1 and mentions(doc, "color") == {("black", "neutral", "khaki, blue and black")}
    assert doc.prompt_version.endswith("+color@" + settings.prompt_version)  # decided: not asked again


def test_a_rate_limit_stops_the_run_and_the_rest_resumes_next_time(s):
    for n, title in enumerate(("a", "b", "c")):
        article(s, title, collected=datetime(2026, 8, 1 + n, tzinfo=timezone.utc))
    answers = {t: [("black", "neutral", "black")] for t in "abc"}
    first = reread_pending(s, FakeProvider(answers, rate_limit_on=("b",)), "color")
    assert first == {"reread": 1, "kept": 0, "failed": 0, "remaining": 2}
    second = FakeProvider(answers)
    assert reread_pending(s, second, "color")["reread"] == 2 and [t for t, _, _ in second.calls] == ["b", "c"]


def test_both_v2_prompts_load():
    assert settings.prompt_version == "v2"
    extract, summary = load_prompt("extract"), load_prompt("summary_fr")
    assert "{taxonomy}" in extract and "tinted_lens" in extract and "khaki, blue and black" in extract
    assert summary.startswith("Tu es analyste tendances")


def test_cli_prints_the_cost_and_spends_nothing_without_confirm(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("Claude called without --confirm")
    monkeypatch.setattr(llm, "get_provider", forbidden)
    init_db()
    with SessionLocal() as db:  # the shared test DB: the row is removed again below
        doc = article(db, "cli-cost-check")
        doc_id, source_id = doc.id, doc.source_id
    try:
        result = CliRunner().invoke(cli, ["reread-colors"])
        assert result.exit_code == 0, result.output
        assert "articles have colors from an older prompt: ~$" in result.stdout and "Nothing spent" in result.stdout
    finally:
        with SessionLocal() as db:
            db.delete(db.get(Document, doc_id))
            db.delete(db.get(Source, source_id))
            db.commit()
