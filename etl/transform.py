"""
Cleans and enriches the raw DataFrame from Google Sheets.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd


def extract_contract_number(value: str) -> str:
    if not isinstance(value, str):
        return str(value) if value else ""

    value = value.strip()
    if not value:
        return ""

    # Match a number optionally followed by /number at the start
    match = re.match(r"(\d+(?:/\d+)?)", value)
    return match.group(1) if match else value


def transform(
    df: pd.DataFrame,
    sheet_name: str,
    contract_col: str | None = None,
    date_col: str | None = None,
    exclude_cols: list[str] | None = None,
) -> pd.DataFrame:

    df = df.copy()

    if exclude_cols is None:
        exclude_cols = ["Категория"]

    # 1. Add sheet name column
    df["sheet_name"] = sheet_name

    if contract_col is None:
        contract_col = _detect_contract_column(df.columns.tolist())

    if contract_col and contract_col in df.columns:
        df[contract_col] = df[contract_col].apply(extract_contract_number)

    cols_to_drop = [
        col for col in df.columns
        if any(col.strip().lower() == ex.strip().lower() for ex in exclude_cols)
    ]
    df = df.drop(columns=cols_to_drop, errors="ignore")

    df["inserted_at"] = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return df


def _detect_contract_column(columns: list[str]) -> str | None:
    priority_keywords = ["договор", "contract", "номер"]
    for keyword in priority_keywords:
        for col in columns:
            if keyword in col.lower():
                return col
    return None
