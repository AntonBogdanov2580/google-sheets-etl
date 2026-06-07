"""
Database layer.
SQLAlchemy-based model definition and upsert logic.
Supports SQLite (default), PostgreSQL, ClickHouse — change DATABASE_URL.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# We use a flexible "wide" table with Text columns so that the schema works
# regardless of the exact column names coming from Google Sheets.
# The fixed/known columns are declared explicitly; unknown columns from the
# sheet are stored via pandas to_sql with extend_existing=True.
# ---------------------------------------------------------------------------


def get_engine(db_url: str):
    """Create a SQLAlchemy engine. Works with SQLite, PostgreSQL, ClickHouse."""
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(db_url, connect_args=connect_args, echo=False)


def ensure_table(engine, table_name: str, df: pd.DataFrame) -> None:
    """
    Create the table if it doesn't exist, using the DataFrame columns.
    'inserted_at' is always added as a TIMESTAMP column.
    """
    with engine.connect() as conn:
        # Build CREATE TABLE IF NOT EXISTS dynamically
        col_defs = []
        for col in df.columns:
            if col == "inserted_at":
                col_defs.append(f'"{col}" TIMESTAMP')
            else:
                col_defs.append(f'"{col}" TEXT')

        cols_sql = ",\n    ".join(col_defs)
        ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n    {cols_sql}\n)'
        conn.execute(text(ddl))
        conn.commit()


def upsert_data(
    df: pd.DataFrame,
    db_url: str,
    table_name: str = "sheets_data",
    date_to_overwrite: date | None = None,
    date_col: str | None = None,
) -> int:
    engine = get_engine(db_url)
    ensure_table(engine, table_name, df)

    df_to_insert = df  # default: insert everything

    with engine.connect() as conn:
        if date_to_overwrite is not None:
            # Режим перезаписи: DELETE только строки за указанную дату,
            # затем INSERT только строки за эту же дату
            col = date_col or _detect_date_column(df.columns.tolist())
            date_str = date_to_overwrite.strftime("%Y-%m-%d")

            if col and col in df.columns:
                delete_sql = text(
                    f'DELETE FROM "{table_name}" '
                    f'WHERE CAST("{col}" AS TEXT) LIKE :date_prefix'
                )
                result = conn.execute(delete_sql, {"date_prefix": f"{date_str}%"})
                conn.commit()
                print(f"  Deleted {result.rowcount} existing row(s) for {date_str}.")

                mask = df[col].astype(str).str.startswith(date_str)
                df_to_insert = df[mask]
                print(
                    f"  Filtered to {len(df_to_insert)} row(s) matching {date_str} "
                    f"(out of {len(df)} total fetched)."
                )
            else:
                print(
                    "  Warning: date column not found; skipping delete/filter step. "
                    "All rows will be inserted. Use --date-col to specify the column name."
                )
        else:
            # Режим полной загрузки: DELETE все строки, затем INSERT все —
            # идемпотентно: можно запускать сколько угодно раз без дубликатов
            result = conn.execute(text(f'DELETE FROM "{table_name}"'))
            conn.commit()
            print(f"  Cleared {result.rowcount} existing row(s) (full reload).")
            print(f"  Inserting all {len(df_to_insert)} row(s).")

        df_to_insert.to_sql(
            table_name,
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
        )
        conn.commit()

    return len(df_to_insert)


def _detect_date_column(columns: list[str]) -> str | None:
    keywords = ["дата", "date", "период", "месяц"]
    for col in columns:
        if any(kw in col.lower() for kw in keywords):
            return col
    return None
