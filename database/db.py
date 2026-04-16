import json
import sqlite3
import threading

from config.logger import logger
from config.settings import Settings


class Database:
    def __init__(self):
        self._local = threading.local()
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(Settings.DB_PATH)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_type TEXT NOT NULL,
                user_input TEXT DEFAULT '',
                status TEXT DEFAULT 'running',
                token_count INTEGER DEFAULT 0,
                provider TEXT DEFAULT '',
                model TEXT DEFAULT '',
                duration REAL DEFAULT 0,
                error_message TEXT DEFAULT '',
                result_json TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                completed_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT NOT NULL,
                context_json TEXT NOT NULL,
                total_scripts INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                pipeline_type TEXT,
                rating INTEGER DEFAULT 0,
                feedback TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
            """
        )
        self._ensure_column("task_logs", "result_json", "TEXT DEFAULT ''")
        self._ensure_column("task_logs", "provider", "TEXT DEFAULT ''")
        self._ensure_column("task_logs", "model", "TEXT DEFAULT ''")
        conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str):
        conn = self._get_conn()
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in rows}
        if column in existing:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()

    def log_task_start(self, pipeline_type: str, user_input: str) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO task_logs (pipeline_type, user_input) VALUES (?, ?)",
            (pipeline_type, user_input),
        )
        conn.commit()
        task_id = int(cursor.lastrowid)
        logger.debug(f"Task start: {task_id} [{pipeline_type}]")
        return task_id

    def log_task_end(
        self,
        task_id: int,
        status: str,
        token_count: int = 0,
        duration: float = 0,
        error_message: str = "",
        result_json: str = "",
        provider: str = "",
        model: str = "",
    ):
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE task_logs
            SET status = ?,
                token_count = ?,
                provider = CASE WHEN ? != '' THEN ? ELSE provider END,
                model = CASE WHEN ? != '' THEN ? ELSE model END,
                duration = ?,
                error_message = ?,
                result_json = CASE WHEN ? != '' THEN ? ELSE result_json END,
                completed_at = datetime('now','localtime')
            WHERE id = ?
            """,
            (
                status,
                token_count,
                provider,
                provider,
                model,
                model,
                duration,
                error_message,
                result_json,
                result_json,
                task_id,
            ),
        )
        conn.commit()
        logger.debug(f"Task end: {task_id} [{status}]")

    def save_task_result(self, task_id: int | None, result: dict):
        if not task_id:
            return
        conn = self._get_conn()
        conn.execute(
            "UPDATE task_logs SET result_json = ? WHERE id = ?",
            (json.dumps(result, ensure_ascii=False), task_id),
        )
        conn.commit()

    def save_project_context(self, project_path: str, context: dict, total_scripts: int = 0):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO project_context (project_path, context_json, total_scripts)
            VALUES (?, ?, ?)
            """,
            (project_path, json.dumps(context, ensure_ascii=False), total_scripts),
        )
        conn.commit()

    def get_recent_tasks(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM task_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_task_stats(self) -> dict:
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                COALESCE(SUM(token_count), 0) AS total_tokens
            FROM task_logs
            """
        ).fetchone()
        return {
            "total": row["total"] or 0,
            "success": row["success"] or 0,
            "failed": row["failed"] or 0,
            "total_tokens": row["total_tokens"] or 0,
        }

    def log_feedback(self, task_id: int, pipeline_type: str, rating: int, feedback: str = ""):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO pipeline_feedback (task_id, pipeline_type, rating, feedback)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, pipeline_type, rating, feedback),
        )
        conn.commit()


db = Database()
