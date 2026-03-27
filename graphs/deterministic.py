from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graphs.base import PipelineDefinition, PipelineState, add_artifact, finalize_result, record_step, register_pipeline
from graphs.safety import create_backup, ensure_parent_directory, preview_diff
from schemas.outputs import CodeEditInstruction, ConfigEditInstruction


def apply_config_edit(project_root: Path, instruction: ConfigEditInstruction) -> dict[str, Any]:
    target = (project_root / instruction.file_path).resolve()
    payload = json.loads(target.read_text(encoding="utf-8"))
    records: list[dict[str, Any]]
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = [payload]
    else:
        raise ValueError("Config file must be a JSON object or array.")
    target_record = next(
        (
            item
            for item in records
            if isinstance(item, dict) and str(item.get(instruction.record_locator_field)) == str(instruction.record_locator_value)
        ),
        None,
    )
    if target_record is None:
        raise KeyError("Could not locate target record.")
    if instruction.old_value is not None and target_record.get(instruction.target_field) != instruction.old_value:
        raise ValueError("old_value mismatch. The file may have changed.")
    before = json.dumps(payload, ensure_ascii=False, indent=2)
    target_record[instruction.target_field] = instruction.new_value
    after = json.dumps(payload, ensure_ascii=False, indent=2)
    ensure_parent_directory(target)
    create_backup(target)
    target.write_text(after, encoding="utf-8")
    return {
        "file_path": str(target),
        "diff": preview_diff(before, after, instruction.file_path),
        "new_value": instruction.new_value,
    }


def apply_code_edit(project_root: Path, instruction: CodeEditInstruction) -> dict[str, Any]:
    target = (project_root / instruction.file_path).resolve()
    content = target.read_text(encoding="utf-8")
    if instruction.old_value is not None and instruction.old_value not in content:
        raise ValueError("old_value mismatch. The file may have changed.")
    if instruction.search_text not in content:
        raise ValueError("search_text was not found in the file.")
    updated = content.replace(instruction.search_text, instruction.replace_text, 1)
    create_backup(target)
    target.write_text(updated, encoding="utf-8")
    return {
        "file_path": str(target),
        "diff": preview_diff(content, updated, instruction.file_path),
    }


def run_config_modify(state: PipelineState, _) -> Any:
    project_root = Path(state["project_root"])
    params = state.get("params", {})
    instruction = ConfigEditInstruction.model_validate(params)
    record_step(state, "deterministic", f"Applying config edit to {instruction.file_path}.")
    result = apply_config_edit(project_root, instruction)
    add_artifact(state, result["file_path"], "json", "Deterministic config modification", result["diff"][:1200])
    state["output"] = result
    return finalize_result("config_modify", state, "success", "Config file updated.")


def run_code_modify(state: PipelineState, _) -> Any:
    project_root = Path(state["project_root"])
    params = state.get("params", {})
    instruction = CodeEditInstruction.model_validate(params)
    record_step(state, "deterministic", f"Applying code edit to {instruction.file_path}.")
    result = apply_code_edit(project_root, instruction)
    add_artifact(state, result["file_path"], "code", "Deterministic code modification", result["diff"][:1200])
    state["output"] = result
    return finalize_result("code_modify", state, "success", "Code file updated.")


register_pipeline(
    PipelineDefinition(
        key="config_modify",
        title="配置修改",
        category="content",
        mode="deterministic",
        description="对 JSON 配置做精确字段修改。",
        pattern="modify_config",
        input_label="配置修改指令",
        placeholder="例如：{\"file_path\":\"Configs/Weapon.json\", ...}",
        handler=run_config_modify,
        visible_in_ui=False,
    )
)

register_pipeline(
    PipelineDefinition(
        key="code_modify",
        title="代码修改",
        category="code",
        mode="deterministic",
        description="对代码做精确文本替换。",
        pattern="modify_code",
        input_label="代码修改指令",
        placeholder="例如：{\"file_path\":\"Assets/Scripts/Foo.cs\", ...}",
        handler=run_code_modify,
        visible_in_ui=False,
    )
)
