from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config.logger import logger
from config.settings import Settings


class Database:
    def __init__(self) -> None:
        self.db_path = Path(Settings.DB_PATH)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    pipeline_type TEXT NOT NULL,
                    input_summary TEXT NOT NULL,
                    output_summary TEXT DEFAULT '',
                    output_files TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'running',
                    error_message TEXT DEFAULT '',
                    token_count INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS project_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT NOT NULL,
                    scanned_at TEXT DEFAULT (datetime('now','localtime')),
                    context_json TEXT NOT NULL,
                    file_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS pipeline_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    pipeline_type TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    output_text TEXT NOT NULL,
                    result TEXT NOT NULL,
                    error_detail TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_task_logs_created_at
                ON task_logs(created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_project_context_project_path
                ON project_context(project_path);

                CREATE INDEX IF NOT EXISTS idx_pipeline_feedback_created_at
                ON pipeline_feedback(created_at DESC);
                """
            )
            conn.commit()
            logger.info("数据库表初始化完成 | 路径=%s", self.db_path)
        finally:
            if conn is not None:
                conn.close()

    def log_task_start(self, pipeline_type: str, input_summary: str) -> int:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                """
                INSERT INTO task_logs (pipeline_type, input_summary)
                VALUES (?, ?)
                """,
                (pipeline_type, input_summary),
            )
            conn.commit()
            task_id = int(cursor.lastrowid)
            logger.info("任务开始 | id=%s | type=%s", task_id, pipeline_type)
            return task_id
        finally:
            if conn is not None:
                conn.close()

    def log_task_end(self, task_id: int, status: str, **kwargs: Any) -> None:
        field_map = {
            "output_summary": "output_summary",
            "output_files": "output_files",
            "error_message": "error_message",
            "token_count": "token_count",
            "duration": "duration_seconds",
            "duration_seconds": "duration_seconds",
        }

        update_data: dict[str, Any] = {"status": status}
        for key, column in field_map.items():
            if key not in kwargs:
                continue
            value = kwargs[key]
            if column == "output_files":
                value = json.dumps(value if value is not None else [], ensure_ascii=False)
            update_data[column] = value

        assignments = ", ".join(f"{column} = ?" for column in update_data)
        params = [*update_data.values(), task_id]

        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            conn.execute(
                f"UPDATE task_logs SET {assignments} WHERE id = ?",
                params,
            )
            conn.commit()
            logger.info("任务结束 | id=%s | status=%s", task_id, status)
        finally:
            if conn is not None:
                conn.close()

    def get_recent_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            rows = conn.execute(
                """
                SELECT
                    id,
                    created_at,
                    pipeline_type,
                    input_summary,
                    output_summary,
                    output_files,
                    status,
                    error_message,
                    token_count,
                    duration_seconds
                FROM task_logs
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            tasks: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                try:
                    item["output_files"] = json.loads(item.get("output_files", "[]"))
                except json.JSONDecodeError:
                    item["output_files"] = []
                tasks.append(item)
            return tasks
        finally:
            if conn is not None:
                conn.close()

    def get_task_stats(self) -> dict[str, int]:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
                    SUM(CASE WHEN status NOT IN ('success', 'running') THEN 1 ELSE 0 END) AS failed,
                    COALESCE(SUM(token_count), 0) AS total_tokens
                FROM task_logs
                """
            ).fetchone()
            stats = {
                "total": int(row["total"] or 0),
                "success": int(row["success"] or 0),
                "failed": int(row["failed"] or 0),
                "total_tokens": int(row["total_tokens"] or 0),
            }
            logger.debug("任务统计读取完成 | %s", stats)
            return stats
        finally:
            if conn is not None:
                conn.close()

    def save_project_context(self, project_path: str, context_dict: dict[str, Any], file_count: int) -> None:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            conn.execute("DELETE FROM project_context WHERE project_path = ?", (project_path,))
            conn.execute(
                """
                INSERT INTO project_context (project_path, context_json, file_count)
                VALUES (?, ?, ?)
                """,
                (project_path, json.dumps(context_dict, ensure_ascii=False), file_count),
            )
            conn.commit()
            logger.info("项目上下文已保存 | path=%s | files=%s", project_path, file_count)
        finally:
            if conn is not None:
                conn.close()

    def get_project_context(self, project_path: str) -> dict[str, Any] | None:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            row = conn.execute(
                """
                SELECT context_json
                FROM project_context
                WHERE project_path = ?
                ORDER BY datetime(scanned_at) DESC, id DESC
                LIMIT 1
                """,
                (project_path,),
            ).fetchone()
            if row is None:
                return None
            context = json.loads(row["context_json"])
            logger.debug("项目上下文命中 | path=%s", project_path)
            return context
        finally:
            if conn is not None:
                conn.close()

    def log_feedback(
        self,
        pipeline_type: str,
        input_text: str,
        output_text: str,
        result: str,
        error_detail: str = "",
    ) -> None:
        conn: sqlite3.Connection | None = None
        try:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO pipeline_feedback (pipeline_type, input_text, output_text, result, error_detail)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pipeline_type, input_text, output_text, result, error_detail),
            )
            conn.commit()
            logger.info("反馈已记录 | type=%s | result=%s", pipeline_type, result)
        finally:
            if conn is not None:
                conn.close()


db = Database()
