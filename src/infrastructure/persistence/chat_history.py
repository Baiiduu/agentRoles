from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4


@dataclass(frozen=True)
class PersistedChatMessage:
    message_id: str
    session_id: str
    agent_id: str
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class PersistedChatSession:
    session_id: str
    agent_id: str
    title: str
    created_at: str
    updated_at: str


class SQLiteAgentChatHistoryRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def append_user_message(self, *, session_id: str, agent_id: str, content: str) -> PersistedChatMessage:
        return self._insert_message(
            session_id=session_id,
            agent_id=agent_id,
            role="user",
            content=content,
        )

    def append_agent_message(self, *, session_id: str, agent_id: str, content: str) -> PersistedChatMessage:
        return self._insert_message(
            session_id=session_id,
            agent_id=agent_id,
            role="agent",
            content=content,
        )

    def list_messages(
        self,
        *,
        session_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[PersistedChatMessage]:
        if session_id is None and agent_id is None:
            raise ValueError("session_id or agent_id is required")
        where_clause = "session_id = ?" if session_id is not None else "agent_id = ?"
        where_value = session_id if session_id is not None else agent_id
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT message_id, session_id, agent_id, role, content, created_at
                FROM (
                    SELECT message_id, session_id, agent_id, role, content, created_at
                    FROM agent_chat_messages
                    WHERE """
                + where_clause
                + """
                    ORDER BY created_at DESC, message_id DESC
                    LIMIT ?
                )
                ORDER BY created_at ASC, message_id ASC
                """,
                (where_value, int(limit)),
            ).fetchall()
        return [
            PersistedChatMessage(
                message_id=str(row["message_id"]),
                session_id=str(row["session_id"]),
                agent_id=str(row["agent_id"]),
                role=str(row["role"]),
                content=str(row["content"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def _insert_message(
        self,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
    ) -> PersistedChatMessage:
        created_at = datetime.now(timezone.utc).isoformat()
        message_id = f"{session_id}:{role}:{created_at}"
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO agent_chat_messages (
                    message_id,
                    session_id,
                    agent_id,
                    role,
                    content,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, agent_id, role, content, created_at),
            )
            connection.execute(
                """
                UPDATE agent_chat_sessions
                SET updated_at = ?
                WHERE session_id = ?
                """,
                (created_at, session_id),
            )
            connection.commit()
        return PersistedChatMessage(
            message_id=message_id,
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            created_at=created_at,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_chat_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_agent_chat_sessions_agent_updated
                ON agent_chat_sessions (agent_id, updated_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_agent_chat_messages_agent_created
                ON agent_chat_messages (agent_id, created_at)
                """
            )
            connection.commit()


class SQLiteAgentChatSessionRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        SQLiteAgentChatHistoryRepository(db_path)

    def create_session(self, *, agent_id: str, title: str | None = None) -> PersistedChatSession:
        timestamp = datetime.now(timezone.utc).isoformat()
        session_id = f"agent_session_{uuid4().hex}"
        normalized_title = (title or "").strip() or "New Session"
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO agent_chat_sessions (session_id, agent_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, agent_id, normalized_title, timestamp, timestamp),
            )
            connection.commit()
        return PersistedChatSession(
            session_id=session_id,
            agent_id=agent_id,
            title=normalized_title,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def get_session(self, *, session_id: str) -> PersistedChatSession | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT session_id, agent_id, title, created_at, updated_at
                FROM agent_chat_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return self._hydrate_session(row)

    def list_sessions(self, *, agent_id: str, limit: int = 20) -> list[PersistedChatSession]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT session_id, agent_id, title, created_at, updated_at
                FROM agent_chat_sessions
                WHERE agent_id = ?
                ORDER BY updated_at DESC, session_id DESC
                LIMIT ?
                """,
                (agent_id, int(limit)),
            ).fetchall()
        return [item for item in (self._hydrate_session(row) for row in rows) if item is not None]

    def get_or_create_latest_session(self, *, agent_id: str) -> PersistedChatSession:
        sessions = self.list_sessions(agent_id=agent_id, limit=1)
        if sessions:
            return sessions[0]
        return self.create_session(agent_id=agent_id)

    def rename_session_if_placeholder(self, *, session_id: str, title: str) -> PersistedChatSession | None:
        normalized_title = title.strip()[:80]
        if not normalized_title:
            return self.get_session(session_id=session_id)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                UPDATE agent_chat_sessions
                SET title = CASE WHEN title = 'New Session' THEN ? ELSE title END
                WHERE session_id = ?
                """,
                (normalized_title, session_id),
            )
            connection.commit()
        return self.get_session(session_id=session_id)

    def delete_session(self, *, session_id: str, agent_id: str) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM agent_chat_sessions WHERE session_id = ? AND agent_id = ?",
                (session_id, agent_id),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                "DELETE FROM agent_chat_messages WHERE session_id = ?",
                (session_id,),
            )
            connection.execute(
                "DELETE FROM agent_chat_sessions WHERE session_id = ? AND agent_id = ?",
                (session_id, agent_id),
            )
            connection.commit()
        return True

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _hydrate_session(self, row: sqlite3.Row | None) -> PersistedChatSession | None:
        if row is None:
            return None
        return PersistedChatSession(
            session_id=str(row["session_id"]),
            agent_id=str(row["agent_id"]),
            title=str(row["title"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
