import os
import tempfile
from pathlib import Path

# Point the app at a throwaway SQLite DB before any app module creates the engine.
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(tempfile.mkdtemp()) / 'test.db').as_posix()}"
