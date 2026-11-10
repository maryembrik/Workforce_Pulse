"""Load hr_featured.csv into the `employees` table.

Default: local SQLite file `data/workforce_pulse.db`.
PostgreSQL: set DATABASE_URL, e.g. postgresql://user:pwd@localhost:5432/workforce_pulse

    python -m src.load_db
"""
import os
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "processed" / "hr_featured.csv"
SCHEMA = ROOT / "sql" / "schema.sql"
SQLITE_PATH = ROOT / "data" / "workforce_pulse.db"


def to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def load_frame() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    df.columns = [to_snake(c) for c in df.columns]
    return df


def load_sqlite(df: pd.DataFrame) -> Path:
    con = sqlite3.connect(SQLITE_PATH)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        df.to_sql("employees", con, if_exists="append", index=False)
        n = con.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    finally:
        con.close()
    print(f"SQLite: loaded {n} rows into {SQLITE_PATH}")
    return SQLITE_PATH


def load_postgres(df: pd.DataFrame, url: str) -> None:
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    with engine.begin() as con:
        con.execute(text(SCHEMA.read_text(encoding="utf-8")))
    df.to_sql("employees", engine, if_exists="append", index=False, method="multi")
    with engine.connect() as con:
        n = con.execute(text("SELECT COUNT(*) FROM employees")).scalar()
    print(f"PostgreSQL: loaded {n} rows")


if __name__ == "__main__":
    frame = load_frame()
    url = os.environ.get("DATABASE_URL")
    load_postgres(frame, url) if url else load_sqlite(frame)
