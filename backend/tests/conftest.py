import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))   # make `fakes` importable

from cadis.answer import extractive  # noqa: E402
from cadis.config import get_settings  # noqa: E402

_ENV_PREFIXES = ("CADIS_",)
_LEGACY_ENV = ("QA_MODEL", "SUM_MODEL", "NER_MODEL", "EMB_MODEL", "FRONTEND_URL")

EVAL_DOCS = Path(__file__).resolve().parents[2] / "data" / "eval" / "documents"


@pytest.fixture(autouse=True)
def clean_state(monkeypatch, tmp_path):
    """Each test starts with default settings, an empty passage cache and its
    own data directory (so nothing is ever written to ./var)."""
    for key in list(os.environ):
        if key.startswith(_ENV_PREFIXES) or key in _LEGACY_ENV:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CADIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CADIS_RUN_WORKER", "false")
    get_settings.cache_clear()
    extractive.passage_cache.clear()
    yield
    get_settings.cache_clear()
    extractive.passage_cache.clear()


@pytest.fixture
def v2(monkeypatch):
    """V2 storage in the test's temp dir: migrated SQLite, a fake embedder and
    an in-memory vector store. Use ``v2_chroma`` for the real ChromaDB."""
    from fakes import FakeEmbedder, InMemoryVectorStore

    from cadis.index import vector_store
    from cadis.models import registry
    from cadis.storage import db, repositories

    emb = FakeEmbedder()
    monkeypatch.setattr(registry, "get_embedder", lambda: emb)
    store = InMemoryVectorStore()
    vector_store.set_vector_store(store)
    db.init_db()
    with db.session_scope() as s:
        repositories.ensure_tenant(s, get_settings().default_tenant)
    yield store
    vector_store.set_vector_store(None)
    db.dispose_engines()


@pytest.fixture
def v2_chroma(monkeypatch):
    """Like ``v2`` but with a real on-disk ChromaDB (integration tests)."""
    from fakes import FakeEmbedder

    from cadis.index import vector_store
    from cadis.models import registry
    from cadis.storage import db, repositories

    emb = FakeEmbedder()
    monkeypatch.setattr(registry, "get_embedder", lambda: emb)
    vector_store.set_vector_store(None)
    db.init_db()
    with db.session_scope() as s:
        repositories.ensure_tenant(s, get_settings().default_tenant)
    yield vector_store.get_vector_store()
    vector_store.set_vector_store(None)
    db.dispose_engines()
