"""
Google Sheets API client.
Handles OAuth 2.0 authentication and data fetching.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required for reading Google Sheets and Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_credentials(credentials_path: str, token_path: str) -> Credentials:
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def fetch_sheet(
    spreadsheet_id: str,
    sheet_name: str,
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
    header_row: int = 0,
) -> pd.DataFrame:
    creds = _get_credentials(credentials_path, token_path)
    service = build("sheets", "v4", credentials=creds)

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
    )

    values = result.get("values", [])
    if not values:
        raise ValueError(f"Sheet '{sheet_name}' is empty or not found.")

    if header_row >= len(values):
        raise ValueError(
            f"header_row={header_row} is out of range "
            f"(sheet has {len(values)} row(s))."
        )

    headers = values[header_row]
    rows = values[header_row + 1 :]

    padded_rows = [row + [""] * (len(headers) - len(row)) for row in rows]

    df = pd.DataFrame(padded_rows, columns=headers)
    df = df[df.apply(lambda r: r.str.strip().ne("").any(), axis=1)].reset_index(drop=True)
    return df
