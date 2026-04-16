from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from config.settings import Settings
from scanner.unity_mcp import COPLAY_PACKAGE_NAME, detect_coplay_package


ENGINE_TOOL_REQUIREMENTS = {
    "engine_compile": {"validate_script", "read_console"},
    "engine_run_tests": {"run_tests", "get_test_job"},
    "engine_get_logs": {"read_console"},
}

CONSOLE_ERROR_PATTERN = re.compile(
    r"(?P<file>Assets/[^:(\n]+\.cs)\((?P<line>\d+),(?P<col>\d+)\):\s*"
    r"(?P<level>error|warning)\s*(?P<code>CS\d+)?:?\s*(?P<message>.+)",
    re.IGNORECASE,
)


def get_coplay_stdio_invocation() -> tuple[str | None, list[str], dict[str, str]]:
    uvx = shutil.which("uvx") or shutil.which("uvx.exe")
    if uvx:
        return (
            uvx,
            ["--from", "mcpforunityserver", "mcp-for-unity", "--transport", "stdio"],
            {"MCP_TOOL_TIMEOUT": Settings.MCP_TOOL_TIMEOUT_MS},
        )

    uv = shutil.which("uv") or shutil.which("uv.exe")
    if uv:
        return (
            uv,
            ["tool", "run", "--from", "mcpforunityserver", "mcp-for-unity", "--transport", "stdio"],
            {"MCP_TOOL_TIMEOUT": Settings.MCP_TOOL_TIMEOUT_MS},
        )

    return None, [], {}


def is_engine_tool_available(tool_name: str, registered_tools: set[str]) -> bool:
    required = ENGINE_TOOL_REQUIREMENTS.get(tool_name, set())
    return bool(required) and required.issubset(registered_tools)


def coplay_package_name() -> str:
    return COPLAY_PACKAGE_NAME


def _parse_payload(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"success": False, "message": text}
    return {"success": False, "message": str(raw)}


def _uri_for_path(path: str) -> str:
    normalized = str(path or "").replace("\\", "/").lstrip("/")
    return f"mcpforunity://path/{normalized}"


def _to_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_diagnostic(item: dict, file_path: str, source: str) -> dict:
    severity = str(item.get("severity") or item.get("level") or item.get("type") or "").lower()
    return {
        "file": file_path,
        "line": _to_int(item.get("line") or item.get("lineNumber") or item.get("startLine")),
        "column": _to_int(item.get("column") or item.get("columnNumber") or item.get("startColumn")),
        "code": str(item.get("code") or item.get("diagnosticId") or ""),
        "message": str(item.get("message") or item.get("text") or ""),
        "severity": severity,
        "source": source,
    }


def _collect_validate_script_diagnostics(call_tool, files: list[str]) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []

    for rel_path in files:
        if not rel_path.lower().endswith(".cs"):
            continue
        payload = _parse_payload(
            call_tool(
                "validate_script",
                {
                    "uri": _uri_for_path(rel_path),
                    "level": "standard",
                    "include_diagnostics": True,
                },
            )
        )
        if not payload.get("success"):
            errors.append(
                {
                    "file": rel_path,
                    "line": 0,
                    "column": 0,
                    "code": "VALIDATE_SCRIPT_FAILED",
                    "message": str(payload.get("message") or payload.get("error") or "validate_script 失败"),
                    "severity": "error",
                    "source": "validate_script",
                }
            )
            continue

        data = payload.get("data", {}) or {}
        diagnostics = data.get("diagnostics", []) or []
        for item in diagnostics:
            normalized = _normalize_diagnostic(item, rel_path, "validate_script")
            if normalized["severity"] in {"error", "fatal"}:
                errors.append(normalized)
            else:
                warnings.append(normalized)

    return errors, warnings


def _parse_console_entry(item: dict, target_files: set[str]) -> dict | None:
    message = str(item.get("message") or item.get("text") or "")
    severity = str(item.get("level") or item.get("severity") or item.get("type") or "").lower()
    match = CONSOLE_ERROR_PATTERN.search(message)

    if match:
        rel_path = match.group("file").replace("\\", "/")
        if target_files and rel_path not in target_files and not any(rel_path.endswith(path) for path in target_files):
            return None
        return {
            "file": rel_path,
            "line": _to_int(match.group("line")),
            "column": _to_int(match.group("col")),
            "code": str(match.group("code") or ""),
            "message": match.group("message").strip(),
            "severity": match.group("level").lower(),
            "source": "read_console",
        }

    if severity not in {"error", "warning"}:
        return None
    return {
        "file": "",
        "line": _to_int(item.get("line")),
        "column": _to_int(item.get("column")),
        "code": str(item.get("code") or ""),
        "message": message,
        "severity": severity,
        "source": "read_console",
    }


def _collect_console_diagnostics(call_tool, files: list[str]) -> tuple[list[dict], list[dict]]:
    payload = _parse_payload(
        call_tool(
            "read_console",
            {
                "action": "get",
                "types": ["error", "warning"],
                "count": 100,
                "format": "json",
                "include_stacktrace": False,
            },
        )
    )
    if not payload.get("success"):
        return [], []

    data = payload.get("data", {}) or {}
    items = data.get("items") or data.get("lines") or data if isinstance(data, list) else []
    if not isinstance(items, list):
        return [], []

    target_files = {path.replace("\\", "/") for path in files if path.lower().endswith(".cs")}
    errors: list[dict] = []
    warnings: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed = _parse_console_entry(item, target_files)
        if not parsed:
            continue
        if parsed["severity"] == "warning":
            warnings.append(parsed)
        else:
            errors.append(parsed)
    return errors, warnings


def _dedupe(entries: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for entry in entries:
        key = (
            entry.get("file", ""),
            entry.get("line", 0),
            entry.get("column", 0),
            entry.get("code", ""),
            entry.get("message", ""),
            entry.get("severity", ""),
            entry.get("source", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _discover_project_cs_files(project_path: str) -> list[str]:
    project_root = Path(project_path).resolve()
    assets_root = project_root / "Assets"
    if not assets_root.exists():
        return []

    results = []
    for path in sorted(assets_root.rglob("*.cs")):
        if any(part in {"Library", "Temp", "Packages", "obj", ".git", "Plugins"} for part in path.parts):
            continue
        results.append(str(path.relative_to(project_root)).replace("\\", "/"))
    return results


def run_engine_compile(call_tool, files: list[str], project_path: str = "") -> dict:
    cs_files = [path for path in files if path.lower().endswith(".cs")]
    if not cs_files and project_path:
        cs_files = _discover_project_cs_files(project_path)
    if not cs_files:
        return {
            "success": True,
            "errors": [],
            "warnings": [],
            "duration": 0.0,
            "provider": "coplay",
        }

    t0 = time.time()
    validation_errors, validation_warnings = _collect_validate_script_diagnostics(call_tool, cs_files)
    console_errors, console_warnings = _collect_console_diagnostics(call_tool, cs_files)
    errors = _dedupe(validation_errors + console_errors)
    warnings = _dedupe(validation_warnings + console_warnings)
    return {
        "success": len(errors) == 0,
        "errors": errors[:50],
        "warnings": warnings[:20],
        "duration": time.time() - t0,
        "provider": "coplay",
    }


def run_engine_tests(call_tool, mode: str = "EditMode", test_filter: str = "", wait_timeout: int | None = None) -> dict:
    if wait_timeout is None:
        wait_timeout = Settings.UNITY_TEST_WAIT_TIMEOUT
    t0 = time.time()
    params = {
        "mode": mode,
        "include_failed_tests": True,
        "include_details": False,
    }
    if test_filter:
        params["test_names"] = [test_filter]

    start = _parse_payload(
        call_tool("run_tests", params)
    )
    if not start.get("success"):
        return {
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "failures": [{"name": "", "message": str(start.get("message") or start.get("error") or "run_tests 失败")}],
            "duration": time.time() - t0,
            "provider": "coplay",
        }

    job_id = ((start.get("data") or {}).get("job_id")) or ""
    if not job_id:
        return {
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "failures": [{"name": "", "message": "run_tests 未返回 job_id"}],
            "duration": time.time() - t0,
            "provider": "coplay",
        }

    deadline = time.time() + wait_timeout
    last_payload = start
    while time.time() < deadline:
        payload = _parse_payload(
            call_tool(
                "get_test_job",
                {
                    "job_id": job_id,
                    "include_failed_tests": True,
                    "include_details": False,
                },
            )
        )
        if payload.get("success"):
            last_payload = payload
            data = payload.get("data", {}) or {}
            status = str(data.get("status") or "").lower()
            if status in {"succeeded", "failed", "cancelled"}:
                result = data.get("result", {}) or {}
                summary = result.get("summary", {}) or {}
                failures = [
                    {
                        "name": item.get("fullName") or item.get("name") or "",
                        "message": item.get("message") or item.get("state") or "",
                    }
                    for item in (result.get("results") or [])
                    if str(item.get("state") or "").lower() != "passed"
                ]
                return {
                    "passed": _to_int(summary.get("passed")),
                    "failed": _to_int(summary.get("failed")),
                    "skipped": _to_int(summary.get("skipped")),
                    "failures": failures[:20],
                    "duration": time.time() - t0,
                    "provider": "coplay",
                }
        time.sleep(2)

    return {
        "passed": 0,
        "failed": 1,
        "skipped": 0,
        "failures": [{"name": job_id, "message": f"等待 Unity 测试结果超时 ({wait_timeout}s)"}],
        "duration": time.time() - t0,
        "provider": "coplay",
        "last_status": (last_payload.get("data") or {}).get("status", ""),
    }


def run_engine_get_logs(call_tool, lines: int = 100) -> str:
    payload = _parse_payload(
        call_tool(
            "read_console",
            {
                "action": "get",
                "types": ["error", "warning", "log"],
                "count": lines,
                "format": "detailed",
                "include_stacktrace": False,
            },
        )
    )
    if not payload.get("success"):
        return json.dumps(
            {
                "status": "error",
                "error_code": "ENGINE_LOGS_FAILED",
                "message": str(payload.get("message") or payload.get("error") or "read_console 失败"),
            },
            ensure_ascii=False,
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)
