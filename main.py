"""
CLI entry point for the Google Sheets -> Database ETL pipeline.

Простой запуск (все настройки берутся из config.py):
    python main.py

Перезаписать данные за конкретную дату:
    python main.py --date 2026-03-01

С переопределением настроек:
    python main.py --spreadsheet-id <ID> --db-url postgresql://...
"""
from __future__ import annotations

import io
import sys

# Force UTF-8 output on Windows to correctly display Cyrillic characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from datetime import date

import click

import config
from etl.database import upsert_data
from etl.google_sheets import fetch_sheet
from etl.transform import transform


@click.command()
@click.option(
    "--spreadsheet-id",
    default=config.SPREADSHEET_ID,
    show_default=True,
    help="Google Spreadsheet ID. По умолчанию берётся из config.py.",
)
@click.option(
    "--sheet",
    default=config.SHEET_NAME,
    show_default=True,
    help="Название листа Google Таблицы.",
)
@click.option(
    "--date",
    "date_to_overwrite",
    default=None,
    show_default=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help=(
        "Date (YYYY-MM-DD) to overwrite: deletes existing rows for this date "
        "and inserts only matching rows from the sheet. "
        "If omitted, ALL rows are inserted (initial full load)."
    ),
)
@click.option(
    "--db-url",
    default=config.DATABASE_URL,
    show_default=True,
    envvar="DATABASE_URL",
    help=(
        "SQLAlchemy URL базы данных.\n"
        "Примеры:\n"
        "  sqlite:///data.db\n"
        "  postgresql://user:pass@localhost:5432/mydb\n"
        "  clickhouse+native://user:pass@host:9000/default"
    ),
)
@click.option(
    "--table",
    default=config.TABLE_NAME,
    show_default=True,
    help="Название таблицы в БД.",
)
@click.option(
    "--credentials",
    "credentials_path",
    default="credentials.json",
    show_default=True,
    type=click.Path(exists=True),
    help="Path to OAuth 2.0 credentials JSON file.",
)
@click.option(
    "--token",
    "token_path",
    default="token.json",
    show_default=True,
    help="Path to cached OAuth token file (created automatically on first run).",
)
@click.option(
    "--contract-col",
    default=None,
    help="Column name containing contract numbers (auto-detected if not set).",
)
@click.option(
    "--date-col",
    default=None,
    help="Column name containing dates (used for overwrite; auto-detected if not set).",
)
@click.option(
    "--header-row",
    default=0,
    show_default=True,
    type=int,
    help="0-indexed row number to use as column headers. Use 1 if the sheet has a title row above headers.",
)
def main(
    spreadsheet_id: str,
    sheet: str,
    date_to_overwrite,
    db_url: str,
    table: str,
    credentials_path: str,
    token_path: str,
    contract_col: str | None,
    date_col: str | None,
    header_row: int,
) -> None:
    """ETL pipeline: Google Sheets -> Database."""

    overwrite_date = date_to_overwrite.date() if date_to_overwrite else None
    mode = f"overwrite {overwrite_date}" if overwrite_date else "full load (all rows)"

    click.echo("=" * 60)
    click.echo(f"  Spreadsheet ID : {spreadsheet_id}")
    click.echo(f"  Sheet          : {sheet}")
    click.echo(f"  Mode           : {mode}")
    click.echo(f"  Database       : {db_url}")
    click.echo(f"  Table          : {table}")
    click.echo("=" * 60)

    # Step 1: Extract
    click.echo("\n[1/3] Fetching data from Google Sheets...")
    df = fetch_sheet(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet,
        credentials_path=credentials_path,
        token_path=token_path,
        header_row=header_row,
    )
    click.echo(f"  Fetched {len(df)} row(s), {len(df.columns)} column(s).")
    click.echo(f"  Columns: {df.columns.tolist()}")

    # Step 2: Transform
    click.echo("\n[2/3] Transforming data...")
    df_transformed = transform(
        df=df,
        sheet_name=sheet,
        contract_col=contract_col,
        date_col=date_col,
    )
    click.echo(f"  Columns after transform: {df_transformed.columns.tolist()}")

    # Step 3: Load
    click.echo(f"\n[3/3] Loading data into '{table}' (overwrite {overwrite_date})...")
    rows_inserted = upsert_data(
        df=df_transformed,
        db_url=db_url,
        table_name=table,
        date_to_overwrite=overwrite_date,
        date_col=date_col,
    )
    click.echo(f"  Inserted {rows_inserted} row(s).")

    click.echo("\n✓ Done!")


if __name__ == "__main__":
    main()
