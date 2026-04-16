import json
from pathlib import Path
from typing import Any

from config.logger import logger


NON_NEGATIVE_FIELDS = [
    "id",
    "level",
    "price",
    "damage",
    "hp",
    "health",
    "mp",
    "mana",
    "exp",
    "experience",
    "gold",
    "cost",
    "attackSpeed",
    "speed",
    "range",
]
PROBABILITY_FIELDS = ["critRate", "dropRate", "successRate", "chance", "probability"]
NON_EMPTY_STRING_FIELDS = ["name", "title", "description", "type", "category"]


def validate_config_file(file_path: str, schema: dict = None) -> list[dict]:
    """验证一个配置文件并返回问题列表。"""
    issues: list[dict[str, Any]] = []

    try:
        raw = Path(file_path).read_text(encoding="utf-8-sig")
        data = json.loads(raw)
    except Exception as exc:
        logger.warning(f"配置文件无法解析: {file_path} ({exc})")
        return [{"severity": "error", "field": "", "record": "", "message": f"文件无法解析: {exc}"}]

    items = data if isinstance(data, list) else [data]

    if items and isinstance(items[0], dict):
        ids_seen = {}
        for idx, item in enumerate(items):
            for id_field in ("id", "ID", "Id"):
                if id_field not in item:
                    continue
                value = item[id_field]
                if value in ids_seen:
                    issues.append(
                        {
                            "severity": "error",
                            "field": id_field,
                            "record": str(value),
                            "message": f"ID 重复: {value} 出现在第 {ids_seen[value]} 和第 {idx} 条记录",
                        }
                    )
                else:
                    ids_seen[value] = idx
                break

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        record_label = str(item.get("name", item.get("id", f"#{idx}")))[:30]
        for field, value in item.items():
            field_lower = field.lower()

            if any(field_lower == candidate.lower() for candidate in NON_NEGATIVE_FIELDS):
                if isinstance(value, (int, float)) and value < 0:
                    issues.append(
                        {
                            "severity": "error",
                            "field": field,
                            "record": record_label,
                            "message": f"{field} 不应为负数，实际 {value}",
                        }
                    )

            if any(field_lower == candidate.lower() for candidate in PROBABILITY_FIELDS):
                if isinstance(value, (int, float)) and (value < 0 or value > 1):
                    issues.append(
                        {
                            "severity": "warning",
                            "field": field,
                            "record": record_label,
                            "message": f"{field} 应在 [0, 1] 范围内，实际 {value}",
                        }
                    )

            if any(field_lower == candidate.lower() for candidate in NON_EMPTY_STRING_FIELDS):
                if isinstance(value, str) and not value.strip():
                    issues.append(
                        {
                            "severity": "warning",
                            "field": field,
                            "record": record_label,
                            "message": f"{field} 不应为空字符串",
                        }
                    )

            if value is None:
                issues.append(
                    {
                        "severity": "warning",
                        "field": field,
                        "record": record_label,
                        "message": f"{field} 为 null",
                    }
                )

    if schema and items and isinstance(items[0], dict):
        sample = schema.get("sample_record", {})
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            record_label = str(item.get("name", item.get("id", f"#{idx}")))[:30]
            for field, sample_value in sample.items():
                if field not in item:
                    issues.append(
                        {
                            "severity": "warning",
                            "field": field,
                            "record": record_label,
                            "message": f"缺少字段 {field}（在 sample_record 中存在）",
                        }
                    )
                    continue

                actual = item[field]
                same_numeric_family = isinstance(actual, (int, float)) and isinstance(sample_value, (int, float))
                if type(actual).__name__ != type(sample_value).__name__ and not same_numeric_family:
                    issues.append(
                        {
                            "severity": "warning",
                            "field": field,
                            "record": record_label,
                            "message": (
                                f"{field} 类型不一致：期望 {type(sample_value).__name__}，"
                                f"实际 {type(actual).__name__}"
                            ),
                        }
                    )

    return issues


def validate_all_configs(project_path: str, schemas: list[dict]) -> dict:
    """验证项目所有配置文件。"""
    result = {"total_files": 0, "total_issues": 0, "by_file": {}}
    schema_map = {schema["file_path"]: schema for schema in schemas if schema.get("file_path")}
    project_root = Path(project_path)
    visited: set[str] = set()

    for rel_path, schema in schema_map.items():
        full_path = project_root / rel_path
        if not full_path.exists():
            continue

        issues = validate_config_file(str(full_path), schema)
        result["total_files"] += 1
        visited.add(rel_path.replace("\\", "/"))
        if issues:
            result["by_file"][rel_path] = issues
            result["total_issues"] += len(issues)

    config_root = project_root / "Assets"
    if config_root.exists():
        for file_path in config_root.rglob("*.json"):
            rel_path = str(file_path.relative_to(project_root)).replace("\\", "/")
            if rel_path in visited:
                continue
            issues = validate_config_file(str(file_path), None)
            result["total_files"] += 1
            if issues:
                result["by_file"][rel_path] = issues
                result["total_issues"] += len(issues)

    return result
