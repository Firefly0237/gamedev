"""task_logs 模型埋点测试。"""

from __future__ import annotations

import pytest

from database.db import Database


pytestmark = pytest.mark.unit


def test_log_task_end_persists_provider_and_model(tmp_path, monkeypatch):
    monkeypatch.setattr("database.db.Settings.DB_PATH", str(tmp_path / "test.db"))
    db = Database()

    task_id = db.log_task_start("review_code", "检查一下性能问题")
    db.log_task_end(
        task_id,
        "success",
        token_count=321,
        duration=1.5,
        provider="deepseek",
        model="deepseek-chat",
    )

    row = db.get_recent_tasks(1)[0]
    assert row["provider"] == "deepseek"
    assert row["model"] == "deepseek-chat"
    assert row["token_count"] == 321
