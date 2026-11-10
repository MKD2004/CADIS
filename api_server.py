"""Compatibility shim — the backend now lives in the `cadis` package (backend/cadis/).

Kept so `uvicorn api_server:app` from the repository root still works during
the V1 → V2 migration (DECISIONS ADR-023). Prefer:

    uvicorn cadis.main:app --app-dir backend --port 8000 --reload

Remove this file once nothing starts the app through it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from cadis.main import app  # noqa: E402,F401
