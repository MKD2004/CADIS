"""Database engine, sessions and schema setup (DECISIONS ADR-006).

SQLite settings applied to every connection:
  * ``journal_mode=WAL`` — readers do not block the single writer;
  * ``busy_timeout`` — a writer waits for the lock instead of failing at once;
  * ``foreign_keys=ON`` — needed for ON DELETE CASCADE.

The schema is created and upgraded only by Alembic (``init_db``), so tests,
development and the deployed Space all run the same migrations.
"""

import threading
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from cadis.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _sqlite_pragmas(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=10000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


_engines: dict[str, Engine] = {}
_engines_lock = threading.Lock()


def _engine_for(url: str) -> Engine:
    with _engines_lock:
        if url in _engines:
            return _engines[url]
        if url.startswith("sqlite"):
            db_path = url.split("///", 1)[-1]
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})
            event.listen(engine, "connect", _sqlite_pragmas)
        else:
            engine = create_engine(url, pool_pre_ping=True)
        _engines[url] = engine
        return engine


def get_engine() -> Engine:
    return _engine_for(get_settings().sqlalchemy_url)


def dispose_engines() -> None:
    """Close every pooled connection (tests use this before deleting temp dirs)."""
    with _engines_lock:
        for engine in _engines.values():
            engine.dispose()
        _engines.clear()


def session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope():
    """One transaction: commit on success, roll back on error."""
    session: Session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_fts5(engine: Engine) -> None:
    """FTS5 must be compiled into SQLite for keyword search (ADR-008)."""
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conn:
        opts = {row[0] for row in conn.exec_driver_sql("PRAGMA compile_options")}
    if "ENABLE_FTS5" not in opts:
        raise RuntimeError("This SQLite build has no FTS5; keyword search cannot work.")


def init_db() -> None:
    """Create or upgrade the schema to the latest migration."""
    from alembic import command
    from alembic.config import Config

    engine = get_engine()
    check_fts5(engine)
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
