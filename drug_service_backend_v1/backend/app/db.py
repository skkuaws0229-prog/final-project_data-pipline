from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import settings


def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: dict | None = None) -> list[dict]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            return list(cur.fetchall())


def fetch_one(query: str, params: dict | None = None) -> dict | None:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            return cur.fetchone()


def execute(query: str, params: dict | None = None) -> None:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
        conn.commit()
