from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


# 只记录了总 tokens，没有拆分输入/输出，因此这里用官方单价的中位近似值估算。
PRICES = {
    ("deepseek", "deepseek-chat"): 0.35,
    ("deepseek", "deepseek-reasoner"): 1.37,
    ("anthropic", "claude-haiku-4-5"): 3.0,
    ("anthropic", "claude-sonnet-4-5"): 9.0,
    ("openai", "gpt-5.4-mini"): 2.625,
    ("openai", "gpt-5.4"): 8.75,
}


def _iter_usage(row: sqlite3.Row):
    result_json = row["result_json"] or ""
    if result_json:
        try:
            payload = json.loads(result_json)
            entries = payload.get("model_usage") or []
            if entries:
                for entry in entries:
                    provider = entry.get("provider", "")
                    model = entry.get("model", "")
                    tokens = int(entry.get("tokens", 0) or 0)
                    if provider and model and tokens:
                        yield provider, model, tokens
                return
        except Exception:
            pass

    provider = row["provider"] or ""
    model = row["model"] or ""
    tokens = int(row["token_count"] or 0)
    if provider and model and tokens:
        yield provider, model, tokens


def report(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT provider, model, token_count, result_json
        FROM task_logs
        WHERE created_at >= datetime('now', 'localtime', '-1 day')
        """
    ).fetchall()

    usage: dict[tuple[str, str], int] = {}
    for row in rows:
        for provider, model, tokens in _iter_usage(row):
            usage[(provider, model)] = usage.get((provider, model), 0) + tokens

    total = 0.0
    for provider, model in sorted(usage):
        tokens = usage[(provider, model)]
        price = PRICES.get((provider, model), 1.0)
        cost = tokens / 1_000_000 * price
        total += cost
        print(f"{provider}/{model}: {tokens:>10} tokens ~= ${cost:.4f}")
    print(f"Total (24h): ${total:.4f}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    db_file = root / "gamedev.db"
    report(sys.argv[1] if len(sys.argv) > 1 else str(db_file))
