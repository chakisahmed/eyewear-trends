from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text, true
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
    __table_args__ = (Index("ix_products_source_id_is_active", "source_id", "is_active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[float | None] = mapped_column(Float)
    list_price: Mapped[float | None] = mapped_column(Float)  # pre-markdown price, only when above price (a discount)
    currency: Mapped[str | None] = mapped_column(String(3))
    rank: Mapped[int | None] = mapped_column(Integer)
    flags: Mapped[dict | None] = mapped_column(JSON)  # {"is_bestseller": True, "raw_specs": {...}}
    image_url: Mapped[str | None] = mapped_column(String(1000))
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # last seen
    # Catalog history: first_seen_at is set once, at insert; is_active means "in the store's latest complete crawl";
    # dropped_at is when a crawl noticed the product gone (cleared if it returns).
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tags: Mapped[list["ProductTag"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductTag(Base):
    """Taxonomy code (or audience / product_type) found on a store product by the rule-based tagger."""

    __tablename__ = "product_tags"
    __table_args__ = (
        # One tag per (product, dimension, code, supplier_code): a product may list several variant codes of one
        # color family. NULLs are distinct in SQL, so the partial index keeps "at most one uncoded tag" as before.
        UniqueConstraint("product_id", "dimension", "code", "supplier_code"),
        Index("uq_product_tags_uncoded", "product_id", "dimension", "code", unique=True,
              sqlite_where=text("supplier_code IS NULL"), postgresql_where=text("supplier_code IS NULL")),
        Index("ix_product_tags_dimension_code", "dimension", "code"),  # the trend detail lookup
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    dimension: Mapped[str] = mapped_column(String(20))  # taxonomy dimension, or audience | product_type
    code: Mapped[str] = mapped_column(String(40))
    field: Mapped[str] = mapped_column(String(40))  # provenance: name | categories | spec:<key>
    term: Mapped[str] = mapped_column(String(100))  # the folded synonym that matched
    rules_version: Mapped[int] = mapped_column(Integer)
    # Three-tier color schema, set on dimension == "color" tags only (NULL everywhere else, and on tags made
    # before rules v5 until `retag-products`): family (Palier 1) is the code, hex (Palier 2) the taxonomy's
    # hex for it, supplier_code (Palier 3) the store's commercial variant code, e.g. "HV/BL".
    color_family: Mapped[str | None] = mapped_column(String(40))
    color_hex: Mapped[str | None] = mapped_column(String(7))
    supplier_code: Mapped[str | None] = mapped_column(String(60))

    product: Mapped[Product] = relationship(back_populates="tags")


class StoreCrawl(Base):
    """One crawl of one store (`crawl-store`, `crawl-stores`): what it read, what it changed, and how it ended.

    Crawls run outside the app (Windows Task Scheduler), so this is the only trace the dashboard can read. One row per
    store per crawl, never per product. `crawl-stores` judges which stores are due from the last `ok` crawl."""

    __tablename__ = "store_crawls"
    __table_args__ = (Index("ix_store_crawls_source_id_started_at", "source_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL while running
    # running | ok (complete listing) | incomplete (synced, but the listing may have missed products) | failed
    status: Mapped[str] = mapped_column(String(12))
    trigger: Mapped[str] = mapped_column(String(12))  # single (crawl-store) | batch (crawl-stores)
    listed: Mapped[int | None] = mapped_column(Integer)  # product URLs the listings returned
    crawled: Mapped[int | None] = mapped_column(Integer)  # valid products built from them
    inserted: Mapped[int | None] = mapped_column(Integer)
    updated: Mapped[int | None] = mapped_column(Integer)
    reactivated: Mapped[int | None] = mapped_column(Integer)
    dropped: Mapped[int | None] = mapped_column(Integer)
    drop_skipped: Mapped[str | None] = mapped_column(String(300))  # why nothing was dropped (incomplete, listing shrank)
    problems: Mapped[list | None] = mapped_column(JSON)  # the CrawlReport's reasons the listing may be incomplete
    error: Mapped[str | None] = mapped_column(Text)


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
