from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.logger import logger


PATTERNS_DIR = Path(__file__).parent / "patterns"
SCHEMAS_DIR = Path(__file__).parent / "project_schemas"

INTENT_PATTERN_MAP = {
    "config_modify": "modify_config",
    "code_modify": "modify_code",
    "code_generate": "generate_system",
    "code_review": "review_code",
    "test_generate": "generate_content",
    "shader_generate": "generate_content",
    "config_generate": "generate_content",
    "level_design": "generate_content",
    "dialogue_generate": "generate_content",
    "localization": "translate_content",
    "art_generate": "generate_content",
    "performance_audit": "analyze_project",
    "dependency_analysis": "analyze_project",
    "complex_requirement": "generate_system",
}


def load_all_patterns() -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []

    for pattern_path in sorted(PATTERNS_DIR.glob("*.md")):
        try:
            text = pattern_path.read_text(encoding="utf-8")
            lines = text.splitlines()
            if not lines:
                raise ValueError("Empty pattern file")

            title_line = lines[0].strip()
            name = title_line.removeprefix("# ").strip()
            if not name:
                raise ValueError("Pattern title is missing")

            keyword_line_index = next(
                index for index, line in enumerate(lines) if line.strip().lower().startswith("keywords:")
            )
            keyword_line = lines[keyword_line_index].strip()
            keywords = [
                keyword.strip()
                for keyword in keyword_line.split(":", 1)[1].split(",")
                if keyword.strip()
            ]

            content_lines = [
                line
                for index, line in enumerate(lines)
                if index not in {0, keyword_line_index}
            ]
            content = "\n".join(content_lines).strip()

            patterns.append(
                {
                    "pattern_id": pattern_path.stem,
                    "name": name,
                    "keywords": keywords,
                    "content": content,
                }
            )
        except Exception as exc:
            logger.warning("Pattern 加载失败 | file=%s | error=%s", pattern_path.name, exc)

    return patterns


def load_all_schemas() -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []

    for schema_path in sorted(SCHEMAS_DIR.glob("*.json")):
        try:
            schemas.append(json.loads(schema_path.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.warning("Schema 加载失败 | file=%s | error=%s", schema_path.name, exc)

    return schemas


def match_pattern(intent: str, user_input: str) -> dict[str, Any] | None:
    best_pattern: dict[str, Any] | None = None
    best_score = 0
    user_input_lower = user_input.lower()
    expected_pattern_id = INTENT_PATTERN_MAP.get(intent, "")

    for pattern in load_all_patterns():
        score = 0
        for keyword in pattern["keywords"]:
            if keyword.lower() in user_input_lower:
                score += 10
        if expected_pattern_id and pattern["pattern_id"] == expected_pattern_id:
            score += 5

        if score > best_score:
            best_score = score
            best_pattern = pattern

    logger.info(
        "Pattern 匹配 | intent=%s | pattern=%s | score=%s",
        intent,
        best_pattern["pattern_id"] if best_pattern else None,
        best_score,
    )
    return best_pattern if best_score > 0 else None


def match_schema(user_input: str) -> dict[str, Any] | None:
    best_schema: dict[str, Any] | None = None
    best_score = 0
    user_input_lower = user_input.lower()

    for schema in load_all_schemas():
        score = 0

        sample_record = schema.get("sample_record", {})
        if isinstance(sample_record, dict):
            for value in sample_record.values():
                if isinstance(value, str) and value and value.lower() in user_input_lower:
                    score += 10

        for field in schema.get("fields", []):
            if isinstance(field, str) and field.lower() in user_input_lower:
                score += 5

        file_path = str(schema.get("file_path", ""))
        file_stem = Path(file_path).stem.lower()
        file_keywords = {file_stem}
        for separator in ("_", "-", " "):
            for piece in file_stem.split(separator):
                if piece:
                    file_keywords.add(piece)

        for keyword in file_keywords:
            if keyword and keyword in user_input_lower:
                score += 3

        if score > best_score:
            best_score = score
            best_schema = schema

    return best_schema if best_score > 0 else None


def build_pattern_context(pattern: dict[str, Any], schema: dict[str, Any] | None = None) -> str:
    context = pattern["content"].strip()
    if schema is None:
        return context

    schema_block = "\n".join(
        [
            "## 项目数据格式",
            "",
            f"文件: {schema['file_path']}",
            f"字段: {', '.join(schema['fields'])}",
            f"定位字段: {schema['locate_by']}",
            f"记录数: {schema['record_count']}",
            "",
            "示例记录:",
            "```json",
            json.dumps(schema["sample_record"], ensure_ascii=False, indent=2),
            "```",
        ]
    )
    return f"{context}\n\n{schema_block}"


def load_project_context(project_path: str) -> dict[str, Any]:
    resolved_path = str(Path(project_path).resolve())
    schemas = load_all_schemas()
    logger.info("Project Schema 加载完成 | path=%s | count=%s", resolved_path, len(schemas))
    return {
        "project_path": resolved_path,
        "project_schemas": schemas,
    }
