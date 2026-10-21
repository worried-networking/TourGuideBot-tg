import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import declarative_base

log = logging.getLogger(__package__)
Base = declarative_base()

# How long a writer waits for another one to finish before failing
SQLITE_BUSY_TIMEOUT_MS = 15000


def configure_engine(engine: AsyncEngine) -> AsyncEngine:
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _configure_sqlite_connection)

    return engine


def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    # In WAL mode readers don't block the writer and vice versa
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=%d" % SQLITE_BUSY_TIMEOUT_MS)
    cursor.close()
