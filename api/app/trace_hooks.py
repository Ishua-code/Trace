"""Glue between the NC workflow and Hanu's engine.

Call reindex_nc(db, nc_id) after an NC is created or updated (after the commit).
It must never break the NC workflow: engine errors are logged and swallowed.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.engine.core import TraceEngineImpl
from app.pg_store import PostgresStore

log = logging.getLogger("trace.hooks")


def get_engine(db: Session) -> TraceEngineImpl:
    return TraceEngineImpl(PostgresStore(db))


def reindex_nc(db: Session, nc_id: str) -> None:
    try:
        get_engine(db).index_nc(nc_id)
    except NotImplementedError:
        pass  # engine step 6 (link scoring) not merged yet
    except Exception:  # noqa: BLE001
        log.exception("index_nc failed for %s", nc_id)
