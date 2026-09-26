"""Database access for the storefront — Postgres or SQLite, same SQL.

DATABASE_URL decides which engine is used:

    postgresql://user:pass@host/db     a live server
    sqlite:///data/cargo-auto.db       the file that ships with the repository

Statements are written once, with `:name` placeholders. SQLite consumes those
directly; for Postgres they are rewritten to the adapter's `%(name)s` form.
"""
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/cargo-auto.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_pool = None
_sqlite_path: Path | None = None

_NAMED = re.compile(r":(\w+)")


def _to_pg(sql: str) -> str:
    """`:name` -> `%(name)s`, leaving `::casts` alone."""
    return _NAMED.sub(lambda m: f"%({m.group(1)})s", sql.replace("::", "\0")).replace("\0", "::")


def engine() -> str:
    return "sqlite" if IS_SQLITE else "postgresql"


async def open_pool() -> None:
    global _pool, _sqlite_path
    if IS_SQLITE:
        _sqlite_path = Path(DATABASE_URL.split("://", 1)[1].lstrip("/"))
        if not _sqlite_path.exists():
            raise RuntimeError(f"SQLite database not found: {_sqlite_path}")
        return

    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    _pool = AsyncConnectionPool(DATABASE_URL, min_size=1, max_size=10,
                                open=False, kwargs={"row_factory": dict_row})
    await _pool.open(wait=True, timeout=30)


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()


@asynccontextmanager
async def _pg_connection():
    if _pool is None:
        raise RuntimeError("database pool is not open")
    async with _pool.connection() as conn:
        yield conn


def _sqlite_connection() -> sqlite3.Connection:
    # read-only: the API never writes, and this keeps a file committed to the
    # repository from being modified by serving traffic
    conn = sqlite3.connect(f"file:{_sqlite_path}?mode=ro", uri=True,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


async def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[dict]:
    params = params or {}
    if IS_SQLITE:
        conn = _sqlite_connection()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    async with _pg_connection() as conn:
        cur = await conn.execute(_to_pg(sql), params)
        return await cur.fetchall()


async def fetch_one(sql: str, params: dict[str, Any] | None = None) -> dict | None:
    rows = await fetch_all(sql, params)
    return rows[0] if rows else None
