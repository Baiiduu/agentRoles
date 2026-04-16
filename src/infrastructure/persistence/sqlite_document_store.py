from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3


class SQLiteDocumentStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def list_documents(self, collection: str) -> list[dict[str, object]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM json_documents
                WHERE collection = ?
                ORDER BY document_id
                """,
                (collection,),
            ).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

    def get_document(self, collection: str, document_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM json_documents
                WHERE collection = ? AND document_id = ?
                """,
                (collection, document_id),
            ).fetchone()
        if row is None:
            return None
        return json.loads(str(row["payload_json"]))

    def put_document(self, collection: str, document_id: str, payload: dict[str, object]) -> None:
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        updated_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO json_documents (collection, document_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(collection, document_id)
                DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
                """,
                (collection, document_id, serialized, updated_at),
            )
            connection.commit()

    def has_any(self, collection: str) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM json_documents WHERE collection = ? LIMIT 1",
                (collection,),
            ).fetchone()
        return row is not None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS json_documents (
                    collection TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (collection, document_id)
                )
                """
            )
            connection.commit()
