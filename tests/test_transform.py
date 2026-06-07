"""
Unit tests for the transform module.
Run with: pytest tests/ -v
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from etl.transform import extract_contract_number, transform


class TestExtractContractNumber:
    """Tests for the contract number extraction function."""

    def test_with_company_name(self):
        assert extract_contract_number("29389196/25 - Яндекс") == "29389196/25"

    def test_with_dash_and_spaces(self):
        assert extract_contract_number("12345678/24 - ООО Рога и копыта") == "12345678/24"

    def test_plain_number_with_slash(self):
        assert extract_contract_number("29389196/25") == "29389196/25"

    def test_plain_number_no_slash(self):
        assert extract_contract_number("29389196") == "29389196"

    def test_empty_string(self):
        assert extract_contract_number("") == ""

    def test_whitespace_only(self):
        assert extract_contract_number("   ") == ""

    def test_non_string_none(self):
        assert extract_contract_number(None) == ""  # type: ignore

    def test_leading_spaces(self):
        assert extract_contract_number("  29389196/25 - Яндекс") == "29389196/25"


class TestTransform:
    """Tests for the main transform function."""

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Номер договора": ["29389196/25 - Яндекс", "11111111/24 - Google"],
                "Дата": ["2026-03-01", "2026-03-02"],
                "Сумма": ["1000", "2000"],
                "Категория": ["A", "B"],
            }
        )

    def test_adds_sheet_name_column(self, sample_df):
        result = transform(sample_df, sheet_name="Тест")
        assert "sheet_name" in result.columns
        assert (result["sheet_name"] == "Тест").all()

    def test_removes_category_column(self, sample_df):
        result = transform(sample_df, sheet_name="Тест")
        assert "Категория" not in result.columns

    def test_adds_inserted_at_column(self, sample_df):
        result = transform(sample_df, sheet_name="Тест")
        assert "inserted_at" in result.columns
        assert result["inserted_at"].notna().all()

    def test_extracts_contract_number(self, sample_df):
        result = transform(sample_df, sheet_name="Тест")
        assert result["Номер договора"].iloc[0] == "29389196/25"
        assert result["Номер договора"].iloc[1] == "11111111/24"

    def test_row_count_preserved(self, sample_df):
        result = transform(sample_df, sheet_name="Тест")
        assert len(result) == len(sample_df)
