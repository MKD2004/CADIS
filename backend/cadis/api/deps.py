"""Shared API dependencies: database session, caller, allowed collections.

The allowed-collection list is computed here, on the server, from the caller
— never taken from the request (DECISIONS ADR-015). Until accounts exist
(Phase 6) every request runs as the default tenant and user; tests replace
``get_principal`` through ``app.dependency_overrides``.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from cadis.config import get_settings
from cadis.storage import repositories
from cadis.storage.db import session_factory


def require_v2(request: Request) -> None:
    """V2 endpoints need the database; if startup could not open it, they
    answer 503 while the V1 endpoints keep working."""
    error = getattr(request.app.state, "v2_error", None)
    if error:
        raise HTTPException(503, f"Document storage is unavailable: {error}")


def get_db(_: None = Depends(require_v2)) -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str


def get_principal() -> Principal:
    s = get_settings()
    return Principal(s.default_tenant, s.default_user)


def get_allowed_collections(db: Session = Depends(get_db),
                            principal: Principal = Depends(get_principal)) -> list[str]:
    return repositories.allowed_collection_ids(db, principal.tenant_id, principal.user_id)
