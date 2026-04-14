import difflib
import os
import re
from pathlib import Path

from config.logger import logger
from mcp_tools.mcp_client import call_mcp_tool, get_project_path, is_mcp_connected

# 注意：以 "engine_" 开头的工具名会在 mcp_client.call_tool 中自动翻译为引擎特定工具名。
# Supervisor 的 VERIFY 阶段会调用 validate_csharp_basic 对每个生成的文件做语法检查。

def normalize_path(path: str, project_path: str = "") -> str:
    """路径归一化：相对路径拼接项目根目录"""
    raw_path = (path or "").strip()
    if not project_path:
        project_path = get_project_path()
    if not project_path:
        return os.path.normpath(raw_path)

    project_norm = os.path.normpath(project_path)
    input_norm = os.path.normpath(raw_path)

    if os.path.isabs(input_norm):
        return input_norm

    project_name = Path(project_norm).name
    parts = Path(input_norm).parts

    if parts and parts[0] == project_name:
        input_norm = os.path.normpath(os.path.join(*parts[1:])) if len(parts) > 1 else ""

    return os.path.normpath(os.path.join(project_norm, input_norm))


def safe_write_file(path: str, content: str, project_path: str = "") -> dict:
    """安全写入文件"""
    full_path = normalize_path(path, project_path)
    parent = Path(full_path).parent
    parent.mkdir(parents=True, exist_ok=True)

    exists = False
    old_content = ""
    try:
        old_content = call_mcp_tool("read_file", {"path": full_path})
        if isinstance(old_content, str) and old_content.lstrip().startswith("ENOENT:"):
            old_content = ""
            exists = False
        else:
            exists = True
    except Exception:
        exists = False

    diff_text = ""
    if exists:
        try:
            diff_lines = difflib.unified_diff(
                (old_content or "").splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"{Path(full_path).name} (old)",
                tofile=f"{Path(full_path).name} (new)",
                n=3,
            )
            diff_text = "".join(diff_lines)[:5000]
        except Exception:
            diff_text = ""

    if exists and is_mcp_connected("git"):
        try:
            call_mcp_tool("git_add", {"files": [full_path]})
            call_mcp_tool("git_commit", {"message": f"auto-save before modify: {Path(full_path).name}"})
        except Exception:
            logger.warning(f"Git auto-save 失败: {full_path}")

    if exists:
        try:
            call_mcp_tool("write_file", {"path": full_path + ".bak", "content": old_content})
        except Exception:
            logger.warning(f"备份失败: {full_path}")

    try:
        call_mcp_tool("write_file", {"path": full_path, "content": content})
    except Exception as exc:
        return {"success": False, "error": f"写入失败: {exc}", "path": path, "diff": ""}

    try:
        verify = call_mcp_tool("read_file", {"path": full_path})
        if len(verify.strip()) < 5:
            return {"success": False, "error": "写入后验证失败: 内容异常", "path": path, "diff": ""}
    except Exception as exc:
        return {"success": False, "error": f"写入后验证失败: {exc}", "path": path, "diff": ""}

    logger.info(f"文件写入成功: {path}")
    return {"success": True, "path": path, "is_new": not exists, "error": "", "diff": diff_text}


def execute_tool_safely(tool_name: str, arguments: dict, project_path: str = "") -> str:
    """安全执行工具调用（Agent Loop 的每次工具调用都经过这里）"""
    if not project_path:
        project_path = get_project_path()

    safe_args = dict(arguments or {})

    path_tools = ("read_file", "write_file", "list_directory", "search_files", "move_file")
    if tool_name in path_tools and "path" in safe_args:
        safe_args["path"] = normalize_path(safe_args["path"], project_path)

    if tool_name == "write_file":
        result = safe_write_file(safe_args["path"], safe_args.get("content", ""), project_path)
        if result["success"]:
            return f"成功写入: {result['path']}"
        return f"写入失败: {result['error']}"

    try:
        return call_mcp_tool(tool_name, safe_args)
    except Exception as exc:
        return f"工具调用失败 [{tool_name}]: {exc}"


def validate_csharp_basic(code: str) -> list[str]:
    """C# 基础语法检查"""
    errors: list[str] = []
    if code.count("{") != code.count("}"):
        errors.append("花括号 { } 数量不匹配")
    if code.count("(") != code.count(")"):
        errors.append("圆括号 ( ) 数量不匹配")
    if "MonoBehaviour" in code and "using UnityEngine" not in code:
        errors.append("使用了 MonoBehaviour 但缺少 using UnityEngine")
    if not re.search(r"\b(class|interface|enum)\b", code):
        errors.append("未找到 class/interface/enum 定义")
    return errors


def check_file_conflict(path: str, project_path: str = "") -> str | None:
    """检查文件是否已存在"""
    full_path = normalize_path(path, project_path)
    try:
        call_mcp_tool("read_file", {"path": full_path})
        return f"文件已存在: {path}"
    except Exception:
        return None
