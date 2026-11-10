"""Alembic environment for CADIS.

Normally run through ``cadis.storage.db.init_db()``, which passes an open
connection in ``config.attributes["connection"]``. Running the ``alembic``
command from ``backend/`` also works and uses ``CADIS_DATABASE_URL`` /
``CADIS_DATA_DIR`` from the settings.
"""

from alembic import context

from cadis.storage.tables import Base

config = context.config
target_metadata = Base.metadata


def _configure(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",   # SQLite cannot ALTER most things
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection)
        return
    from cadis.storage.db import get_engine
    with get_engine().connect() as conn:
        _configure(conn)
        conn.commit()


run_migrations_online()
