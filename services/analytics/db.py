import os
import logging
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aqp:aqp_secret@localhost:5432/adaptive_quality"
)


@contextmanager
def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        yield cur


def execute_query(sql: str, params: dict = None) -> list[dict]:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute(sql, params or {})
            return cur.fetchall()


def execute_one(sql: str, params: dict = None) -> dict | None:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute(sql, params or {})
            return cur.fetchone()


def execute_write(sql: str, params: dict = None):
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute(sql, params or {})


def execute_write_many(sql: str, rows: list[tuple]):
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            psycopg2.extras.execute_batch(cur, sql, rows)