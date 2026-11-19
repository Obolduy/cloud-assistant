import sys

import psycopg
from psycopg.rows import dict_row

from core.config import PG_DSN, ROOT

DB_DIR = ROOT / "db"


def connect() -> psycopg.Connection:
    return psycopg.connect(PG_DSN, row_factory=dict_row)


def migrate() -> list[str]:
    applied = []
    with connect() as conn:
        for sql_file in sorted(DB_DIR.glob("*.sql")):
            conn.execute(sql_file.read_text(encoding="utf-8"))
            applied.append(sql_file.name)
    return applied


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def fetchone(sql: str, params: tuple = ()) -> dict | None:
    with connect() as conn:
        return conn.execute(sql, params).fetchone()


if __name__ == "__main__":
    if sys.argv[1:] != ["migrate"]:
        raise SystemExit("usage: python -m core.db migrate")
    for name in migrate():
        print(f"ok: {name}")
