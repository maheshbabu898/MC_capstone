import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.config import settings


def connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_database() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                name TEXT NOT NULL,
                input_size_mb REAL NOT NULL,
                cpu_cycles_giga REAL NOT NULL,
                file_path TEXT,
                status TEXT NOT NULL,
                execution_location TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                execution_seconds REAL,
                network_seconds REAL,
                estimated_latency_ms REAL,
                estimated_energy_joules REAL,
                estimated_reward REAL,
                state_json TEXT,
                decision_json TEXT,
                result_json TEXT,
                server_metrics_json TEXT,
                error_message TEXT
            )
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }
        if "server_metrics_json" not in columns:
            connection.execute("ALTER TABLE tasks ADD COLUMN server_metrics_json TEXT")
        connection.execute("CREATE INDEX IF NOT EXISTS tasks_created_at_idx ON tasks(created_at)")


def create_task(
    task_type: str,
    name: str,
    input_size_mb: float,
    cpu_cycles_giga: float,
    file_path: str | None = None,
) -> dict[str, Any]:
    task = {
        "id": str(uuid4()),
        "task_type": task_type,
        "name": name,
        "input_size_mb": input_size_mb,
        "cpu_cycles_giga": cpu_cycles_giga,
        "file_path": file_path,
        "status": "created",
        "execution_location": None,
        "created_at": utc_now(),
        "started_at": None,
        "completed_at": None,
        "execution_seconds": None,
        "network_seconds": None,
        "estimated_latency_ms": None,
        "estimated_energy_joules": None,
        "estimated_reward": None,
        "state_json": None,
        "decision_json": None,
        "result_json": None,
        "server_metrics_json": None,
        "error_message": None,
    }
    columns = ", ".join(task)
    placeholders = ", ".join("?" for _ in task)
    with connect() as connection:
        connection.execute(
            f"INSERT INTO tasks ({columns}) VALUES ({placeholders})", tuple(task.values())
        )
    return task


def _decode_task(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    task = dict(row)
    for column in ("state_json", "decision_json", "result_json", "server_metrics_json"):
        encoded = task.pop(column)
        task[column.removesuffix("_json")] = json.loads(encoded) if encoded else None
    return task


def get_task(task_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        return _decode_task(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def list_tasks(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    return [task for row in rows if (task := _decode_task(row)) is not None]


def update_task(task_id: str, **fields: Any) -> None:
    allowed = {
        "status",
        "execution_location",
        "started_at",
        "completed_at",
        "execution_seconds",
        "network_seconds",
        "estimated_latency_ms",
        "estimated_energy_joules",
        "estimated_reward",
        "state_json",
        "decision_json",
        "result_json",
        "server_metrics_json",
        "error_message",
    }
    if not fields or not set(fields).issubset(allowed):
        raise ValueError("Invalid task update fields")
    encoded_fields = {
        key: json.dumps(value, ensure_ascii=False) if key.endswith("_json") and value is not None else value
        for key, value in fields.items()
    }
    assignments = ", ".join(f"{key} = ?" for key in encoded_fields)
    with connect() as connection:
        cursor = connection.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            (*encoded_fields.values(), task_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"Task {task_id} was not found")


def claim_task(task_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET status = 'processing', started_at = ?, error_message = NULL "
            "WHERE id = ? AND status IN ('created', 'failed')",
            (utc_now(), task_id),
        )
    return cursor.rowcount == 1


def performance_summary() -> dict[str, Any]:
    with connect() as connection:
        totals = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                   SUM(CASE WHEN status IN ('created', 'processing') THEN 1 ELSE 0 END) AS pending,
                   AVG(CASE WHEN status = 'completed' THEN execution_seconds END) AS average_execution_seconds,
                   AVG(CASE WHEN status = 'completed' THEN estimated_latency_ms END) AS average_estimated_latency_ms,
                   AVG(CASE WHEN status = 'completed' THEN estimated_energy_joules END) AS average_estimated_energy_joules
            FROM tasks
            """
        ).fetchone()
        counts = connection.execute(
            "SELECT execution_location, COUNT(*) AS count FROM tasks "
            "WHERE status = 'completed' AND execution_location IS NOT NULL "
            "GROUP BY execution_location"
        ).fetchall()
        decision_counts = connection.execute(
            "SELECT execution_location, COUNT(*) AS count FROM tasks "
            "WHERE execution_location IS NOT NULL "
            "GROUP BY execution_location"
        ).fetchall()
    summary = dict(totals)
    return {
        "total": summary["total"] or 0,
        "completed": summary["completed"] or 0,
        "failed": summary["failed"] or 0,
        "pending": summary["pending"] or 0,
        "average_execution_seconds": summary["average_execution_seconds"],
        "average_estimated_latency_ms": summary["average_estimated_latency_ms"],
        "average_estimated_energy_joules": summary["average_estimated_energy_joules"],
        "location_distribution": {row["execution_location"]: row["count"] for row in counts},
        "decision_distribution": {row["execution_location"]: row["count"] for row in decision_counts},
    }
