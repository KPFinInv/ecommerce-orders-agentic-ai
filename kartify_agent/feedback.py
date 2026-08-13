"""Conversation feedback storage and customer-experience quality metrics."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from .models import FeedbackRecord


class FeedbackStore:
    """Persist demo feedback in SQLite; Community Cloud storage is ephemeral."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or Path(tempfile.gettempdir()) / "kartify_feedback.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_feedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL UNIQUE,
                    customer_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    resolved INTEGER NOT NULL,
                    comment TEXT NOT NULL DEFAULT '',
                    turns INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    intents TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save(
        self,
        record: FeedbackRecord | dict[str, Any] | None = None,
        **fields: Any,
    ) -> FeedbackRecord:
        """Validate and upsert feedback from a record, mapping, or keyword fields."""
        if record is not None and fields:
            raise ValueError("Pass either a record or keyword fields, not both.")
        payload = fields if record is None else record
        validated = payload if isinstance(payload, FeedbackRecord) else FeedbackRecord(**payload)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_feedback (
                    conversation_id, customer_id, rating, resolved, comment,
                    turns, duration_seconds, intents
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    rating=excluded.rating,
                    resolved=excluded.resolved,
                    comment=excluded.comment,
                    turns=excluded.turns,
                    duration_seconds=excluded.duration_seconds,
                    intents=excluded.intents
                """,
                (
                    validated.conversation_id,
                    validated.customer_id,
                    validated.rating,
                    int(validated.resolved),
                    validated.comment,
                    validated.turns,
                    validated.duration_seconds,
                    ",".join(validated.intents),
                ),
            )
        return validated

    def dataframe(self) -> pd.DataFrame:
        with self._connect() as connection:
            frame = pd.read_sql_query(
                "SELECT * FROM conversation_feedback ORDER BY created_at", connection
            )
        if not frame.empty:
            frame["resolved"] = frame["resolved"].astype(bool)
        return frame

    def metrics(self) -> dict[str, float | int | str]:
        frame = self.dataframe()
        if frame.empty:
            return {
                "responses": 0,
                "average_rating": 0.0,
                "resolution_rate": 0.0,
                "five_star_share": 0.0,
                "average_turns": 0.0,
                "quality_band": "Insufficient feedback",
            }
        average_rating = float(frame["rating"].mean())
        resolution_rate = float(frame["resolved"].mean())
        if average_rating >= 4.5 and resolution_rate >= 0.80:
            band = "Strong"
        elif average_rating >= 3.5 and resolution_rate >= 0.60:
            band = "Monitor"
        else:
            band = "Needs improvement"
        return {
            "responses": int(len(frame)),
            "average_rating": round(average_rating, 2),
            "resolution_rate": round(resolution_rate, 3),
            "five_star_share": round(float((frame["rating"] == 5).mean()), 3),
            "average_turns": round(float(frame["turns"].mean()), 2),
            "quality_band": band,
        }
