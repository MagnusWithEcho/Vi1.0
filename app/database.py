"""Hanterar anslutningen till SQLite-databasen för dagboksloggar."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

# Sökvägen till databasfilen (lagras i mappen "data")
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "diary.db"


def initialize_database() -> None:
    """Skapar databastabellen om den inte redan finns."""

    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS diary_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,
                text TEXT NOT NULL,
                mood TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_connection() -> sqlite3.Connection:
    """Returnerar en ny databaskoppling med dictionary-rader."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Gör om en databastabell-rad till en vanlig Python-dict."""

    return {
        "id": row["id"],
        "entry_date": row["entry_date"],
        "text": row["text"],
        "mood": row["mood"],
        "tag": row["tag"],
        "created_at": row["created_at"],
    }


def fetch_rows(query: str, parameters: Iterable[Any] | None = None) -> List[Dict[str, Any]]:
    """Kör en SELECT-fråga och returnerar resultatet som listor av dictar."""

    parameters = tuple(parameters or [])
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
    return [row_to_dict(row) for row in rows]


def execute(query: str, parameters: Iterable[Any]) -> int:
    """Kör en INSERT/UPDATE/DELETE-fråga och returnerar antalet påverkade rader."""

    parameters = tuple(parameters)
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
        connection.commit()
        return cursor.lastrowid


def current_timestamp() -> str:
    """Returnerar nuvarande tid i ISO-format (YYYY-MM-DD HH:MM:SS)."""

    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
