from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from .models import MemoryRecord, MissionState


class MissionRepository:
    """SQLite-backed JSON document store for reproducible local prototyping.

    The interface deliberately mirrors the aggregate boundaries that would map to
    Postgres tables plus an event log in the production architecture.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    state_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                """
            )

    def save(self, mission: MissionState) -> MissionState:
        payload = mission.model_dump_json()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO missions(id, created_at, updated_at, status, title, state_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  updated_at=excluded.updated_at,
                  status=excluded.status,
                  title=excluded.title,
                  state_json=excluded.state_json
                """,
                (
                    mission.id,
                    mission.created_at,
                    mission.updated_at,
                    mission.status.value,
                    mission.title,
                    payload,
                ),
            )
        return mission

    def get(self, mission_id: str) -> MissionState | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM missions WHERE id = ?", (mission_id,)
            ).fetchone()
        return MissionState.model_validate_json(row["state_json"]) if row else None

    def list(self, limit: int = 50) -> list[MissionState]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT state_json FROM missions ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [MissionState.model_validate_json(row["state_json"]) for row in rows]

    def save_memory(self, memory: MemoryRecord) -> MemoryRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memories(id, mission_id, created_at, record_json)
                VALUES (?, ?, ?, ?)
                """,
                (memory.id, memory.mission_id, memory.created_at, memory.model_dump_json()),
            )
        return memory

    def list_memories(self, limit: int = 100) -> list[MemoryRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT record_json FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [MemoryRecord.model_validate_json(row["record_json"]) for row in rows]

    def export_replay(self, mission_id: str) -> dict:
        mission = self.get(mission_id)
        if not mission:
            raise KeyError(mission_id)
        return {
            "schema_version": "1.0",
            "mission": mission.model_dump(mode="json"),
            "evaluation": {
                "top_hypothesis": mission.hypotheses[0].model_dump(mode="json")
                if mission.hypotheses
                else None,
                "executed_actions": len(mission.actions),
                "approved_actions": sum(
                    1 for approval in mission.approvals if approval.decision == "approved"
                ),
            },
        }
