import os
import tempfile
from pathlib import Path

# Point the app at a throwaway SQLite DB before any app module creates the engine.
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(tempfile.mkdtemp()) / 'test.db').as_posix()}"

import pytest


@pytest.fixture(autouse=True)
def no_live_sitemap_collection(monkeypatch):
    """Pipeline runs in tests must never download real sitemaps (Acuité's is ~8 MB). Tests of the
    sitemap collector call app.collectors.sitemap_news directly, with a mock transport."""
    import app.jobs.pipeline as pipeline
    monkeypatch.setattr(pipeline, "collect_sitemap_sources", lambda session, progress=None: 0)
