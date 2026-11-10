import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))   # make `fakes` importable

from cadis.answer import extractive  # noqa: E402
from cadis.config import get_settings  # noqa: E402

_ENV_PREFIXES = ("CADIS_",)
_LEGACY_ENV = ("QA_MODEL", "SUM_MODEL", "NER_MODEL", "EMB_MODEL", "FRONTEND_URL")


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Each test starts with default settings and an empty passage cache."""
    for key in list(os.environ):
        if key.startswith(_ENV_PREFIXES) or key in _LEGACY_ENV:
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    extractive.passage_cache.clear()
    yield
    get_settings.cache_clear()
    extractive.passage_cache.clear()
