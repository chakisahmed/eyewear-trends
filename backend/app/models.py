from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    """A place we collect from: a feed, a news query, a store, a social account/hashtag."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # press | news | store | social | search
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    lang: Mapped[str] = mapped_column(String(5))  # fr | en
    country: Mapped[str | None] = mapped_column(String(5))
    active: Mapped[bool] = mapped_column(default=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="source")


class Document(Base):
    """One article, post or product page, as collected."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(5))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # pending -> extracted | irrelevant | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    summary_fr: Mapped[str | None] = mapped_column(Text)
    brands: Mapped[list | None] = mapped_column(JSON)
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    is_demo: Mapped[bool] = mapped_column(default=False)

    source: Mapped[Source] = relationship(back_populates="documents")
    mentions: Mapped[list["Mention"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Product(Base):
    """A store product (Phase 2: store crawlers)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    rank: Mapped[int | None] = mapped_column(Integer)
    flags: Mapped[list | None] = mapped_column(JSON)  # ["best_seller", "new"]
    image_url: Mapped[str | None] = mapped_column(String(1000))
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Mention(Base):
    """One taxonomy attribute found in a document — the evidence behind every trend."""

    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    dimension: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    stance: Mapped[str] = mapped_column(String(12))  # rising | declining | neutral
    evidence: Mapped[str] = mapped_column(Text)  # short quote from the source
    occurred_on: Mapped[date] = mapped_column(Date, index=True)

    document: Mapped[Document] = relationship(back_populates="mentions")


class SearchInterest(Base):
    """Google Trends interest for a taxonomy keyword (0-100 scale, per week)."""

    __tablename__ = "search_interest"
    __table_args__ = (UniqueConstraint("code", "lang", "geo", "week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dimension: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(40), index=True)
    keyword: Mapped[str] = mapped_column(String(200))
    lang: Mapped[str] = mapped_column(String(5))
    geo: Mapped[str] = mapped_column(String(5))  # "FR" or "" for worldwide
    week: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)
    is_demo: Mapped[bool] = mapped_column(default=False)


class TrendSnapshot(Base):
    """Weekly score per attribute, computed by scoring.trends."""

    __tablename__ = "trend_snapshots"
    __table_args__ = (UniqueConstraint("dimension", "code", "week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dimension: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(40))
    week: Mapped[date] = mapped_column(Date, index=True)
    mentions: Mapped[float] = mapped_column(Float)  # weighted mention VOLUME (every mention counts)
    search: Mapped[float | None] = mapped_column(Float)  # avg Google Trends interest
    momentum: Mapped[float] = mapped_column(Float)  # volume growth (+ search blend)
    status: Mapped[str] = mapped_column(String(12))  # en_hausse | au_pic | stable | en_baisse
    tone: Mapped[float | None] = mapped_column(Float)  # 4-week pooled (rising − declining) / all, −1..+1
    decline_share: Mapped[float | None] = mapped_column(Float)  # 4-week share of "fading" mentions, 0..1


class JobRun(Base):
    """One pipeline run, so the UI can show "collecte en cours" and "mis à jour il y a 3 h"."""

    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12), default="running")  # running | success | failed
    trigger: Mapped[str] = mapped_column(String(12), default="manual")  # manual | schedule | cli
    steps: Mapped[list] = mapped_column(JSON)
    report: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    # live progress, shown in the UI while the run is going
    current_step: Mapped[str | None] = mapped_column(String(20))  # one of pipeline.ALL_STEPS
    step_done: Mapped[int | None] = mapped_column(Integer)  # items done in the current step
    step_total: Mapped[int | None] = mapped_column(Integer)  # items in the current step (None = not countable)


class WeeklySummary(Base):
    __tablename__ = "weekly_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    week: Mapped[date] = mapped_column(Date, unique=True)
    text_fr: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
