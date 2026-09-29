"""Weekly summary prompt v3: color may not lose every bullet to shapes. The brief names the color families that
must be cited (zero LLM, deterministic); the summary is checked for one of them. Fake provider: no Claude."""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base
from app.extraction.service import load_prompt
from app.models import TrendSnapshot, WeeklySummary
from app.scoring.summary import build_brief, cited_color_missing, generate_weekly_summary

WEEK = date(2026, 9, 21)
HEADING = "Couleurs à citer obligatoirement"


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def trend(s, dimension: str, code: str, weekly: float, status: str, momentum: float) -> None:
    """Four weeks of `weekly` mentions (4 x weekly over 4 weeks), `status` in the reporting week."""
    for n in range(4):
        s.add(TrendSnapshot(dimension=dimension, code=code, week=WEEK - timedelta(weeks=n), mentions=weekly,
                            momentum=momentum, status=status if n == 0 else "stable"))
    s.commit()


def must_cite_section(brief: str) -> list[str]:
    if HEADING not in brief:
        return []
    section = brief.split(HEADING, 1)[1].split("\n\n", 1)[0].splitlines()[1:]
    return [line.split(" | ")[1] for line in section]


class FakeProvider:
    def __init__(self, text: str):
        self.text, self.system = text, None

    def write(self, system: str, user: str) -> str:
        self.system = system
        return self.text


def test_the_summary_uses_prompt_v4_and_extraction_stays_on_v2():
    assert settings.summary_prompt_version == "v4" and settings.prompt_version == "v2"  # re-read markers name v2
    v3, v4 = load_prompt("summary_fr", "v3"), load_prompt("summary_fr", "v4")
    assert "Couleur obligatoire" in v3 and HEADING in v3 and "exactement comme elle est écrite" in v3
    assert "Couleur obligatoire" not in load_prompt("summary_fr", "v2")
    # v4 = v3 plus guidance for the catalog section, and nothing taken away
    assert all(line in v4 for line in v3.splitlines() if line.strip())
    assert "Nouveautés des catalogues créateurs" in v4 and "Nouveautés des catalogues créateurs" not in v3
    assert "Cette puce ne remplace jamais la puce couleur obligatoire" in v4 and "trop peu de nouveautés" in v4
    assert "{taxonomy}" in load_prompt("extract")                                   # default: the extraction version


def test_rising_or_peaking_colors_with_10_mentions_must_be_cited_strongest_first(s):
    trend(s, "color", "green", 3.0, "en_hausse", 1.59)     # 12 over 4 weeks
    trend(s, "color", "black", 4.25, "au_pic", 0.40)       # 17, peaking also counts
    trend(s, "color", "grey", 1.25, "en_hausse", 2.25)     # 5: too few, however strong the momentum
    trend(s, "color", "clear", 2.5, "en_baisse", -0.41)    # 10 but declining
    trend(s, "shape", "shield", 5.0, "en_hausse", 3.61)    # not a color
    assert must_cite_section(build_brief(s, WEEK)) == ["Vert / Kaki", "Noir"]


def test_no_section_when_no_color_qualifies(s):
    trend(s, "color", "blue", 2.0, "en_hausse", 0.64)      # 8 over 4 weeks
    trend(s, "shape", "shield", 5.0, "en_hausse", 3.61)
    assert HEADING not in build_brief(s, WEEK)


@pytest.mark.parametrize(("text", "missing"), [
    ("- **Le vert progresse** : +159 % (12 mentions).", []),                 # one part of "Vert / Kaki" is enough
    ("- **Vert / Kaki en hausse** : +159 %.", []),
    ("- **Masque** : +361 %. - **Oversize** : +273 %.", ["Vert / Kaki"]),    # color left out: flagged
    ("- **Le kaki revient** : +159 %.", []),
])
def test_the_summary_is_checked_for_a_mandatory_color(s, text, missing):
    trend(s, "color", "green", 3.0, "en_hausse", 1.59)
    assert cited_color_missing(s, WEEK, text) == missing


def test_generation_sends_v3_and_warns_when_the_color_bullet_is_missing(s, caplog):
    trend(s, "color", "green", 3.0, "en_hausse", 1.59)
    provider = FakeProvider("- **Masque / enveloppante** : +361 %.")
    with caplog.at_level("WARNING", logger="app.scoring.summary"):
        row = generate_weekly_summary(s, provider, WEEK)
    assert "Couleur obligatoire" in provider.system
    assert row.text_fr == provider.text and s.query(WeeklySummary).count() == 1
    assert "names none of the mandatory color families: Vert / Kaki" in caplog.text

    caplog.clear()
    with caplog.at_level("WARNING", logger="app.scoring.summary"):
        generate_weekly_summary(s, FakeProvider("- **Vert / Kaki** : +159 %."), WEEK)
    assert "mandatory color" not in caplog.text and s.query(WeeklySummary).count() == 1  # same week: updated in place


def test_the_brief_carries_the_creator_catalog_section_only_with_history(s):
    from datetime import datetime, timezone
    from app.models import Product, ProductTag, Source, StoreCrawl
    trend(s, "shape", "round", 5, "en_hausse", 0.4)
    assert "Nouveautés des catalogues créateurs" not in build_brief(s, WEEK)      # no store history at all
    now = datetime.now(timezone.utc)
    src = Source(name="Etnia", kind="store", url="https://etnia.test/", lang="en", country="ES")
    s.add(src)
    s.flush()
    s.add(StoreCrawl(source_id=src.id, status="ok", trigger="batch", started_at=now - timedelta(days=20, hours=1),
                     finished_at=now - timedelta(days=20)))
    p = Product(source_id=src.id, url="https://etnia.test/a", name="A", seen_at=now, first_seen_at=now - timedelta(days=2))
    p.tags = [ProductTag(dimension="shape", code="round", field="spec:Forme", term="round", rules_version=10)]
    s.add(p)
    s.commit()
    brief = build_brief(s, WEEK)
    assert "Nouveautés des catalogues créateurs" in brief and "Etnia : 1 nouveauté(s)" in brief
    assert "Trop peu de nouveautés (1)" in brief                                    # under the volume floor: do not conclude
