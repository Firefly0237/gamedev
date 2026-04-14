import json
import re
from typing import Callable

from config.logger import logger
from config.settings import Settings
from graphs.safety import normalize_path, validate_csharp_basic
from mcp_tools.mcp_client import call_mcp_tool, get_project_path, is_mcp_connected
from schemas.contracts import empty_verification


def validate_nunit_test(content: str, file_path: str = "") -> list[str]:
    """校验 NUnit 测试文件。"""
    errors = validate_csharp_basic(content)

    if "using NUnit.Framework" not in content:
        errors.append("缺少 using NUnit.Framework")

    if "[Test]" not in content and "[TestCase]" not in content:
        errors.append("没有 [Test] 或 [TestCase] 标记")

    class_match = re.search(r"\bclass\s+(\w+)", content)
    if class_match:
        class_name = class_match.group(1)
        has_test_fixture = "[TestFixture]" in content
        if not class_name.endswith("Tests") and not has_test_fixture:
            errors.append(f"测试类名 '{class_name}' 应以 Tests 结尾或标注 [TestFixture]")

    return errors


def validate_shader_basic(content: str, file_path: str = "") -> list[str]:
    """校验 Unity Shader 文件基本结构。"""
    errors: list[str] = []

    if not re.search(r'Shader\s+"[^"]+"', content):
        errors.append('缺少 Shader "name" 声明')

    if "SubShader" not in content:
        errors.append("缺少 SubShader 块")

    if "Pass" not in content:
        errors.append("缺少 Pass 块")

    if content.count("{") != content.count("}"):
        errors.append("花括号 { } 数量不匹配")

    return errors


def validate_localization_basic(content: str, file_path: str = "") -> list[str]:
    """校验本地化 JSON 文件。"""
    errors: list[str] = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        errors.append(f"JSON 解析失败: {exc}")
        return errors

    if not isinstance(data, dict):
        errors.append("本地化文件应该是 JSON 对象（key-value 形式）")
        return errors

    if not data:
        errors.append("本地化文件为空")
        return errors

    for key, value in data.items():
        if not isinstance(value, str):
            errors.append(f"key '{key}' 的 value 不是字符串")

    return errors


def validate_config_json(content: str, file_path: str = "") -> list[str]:
    """校验配置 JSON 文件（基础）。"""
    errors: list[str] = []
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        errors.append(f"JSON 解析失败: {exc}")
    return errors


SKILL_VALIDATORS = {
    "generate_test": validate_nunit_test,
    "generate_shader": validate_shader_basic,
    "translate": validate_localization_basic,
    "modify_config": validate_config_json,
}


def _pick_validator(skill_id: str, file_path: str) -> Callable:
    """根据 skill_id 和文件路径选验证器。"""
    if skill_id in SKILL_VALIDATORS:
        return SKILL_VALIDATORS[skill_id]

    lower = file_path.lower()
    if lower.endswith(".cs"):
        return validate_csharp_basic
    if lower.endswith(".shader") or lower.endswith(".shadergraph"):
        return validate_shader_basic
    if lower.endswith(".json"):
        return validate_config_json

    return lambda content, file_path="": []


def _run_validator(validator: Callable, content: str, file_path: str) -> list[str]:
    """兼容单参数和双参数 validator 签名。"""
    try:
        return validator(content, file_path)
    except TypeError:
        return validator(content)


def verify_files(
    files: list[str],
    project_context: dict = None,
    mode: str = None,
    skill_id: str = "",
) -> dict:
    """验证文件列表。"""
    if mode is None:
        mode = Settings.DEFAULT_VERIFY_MODE

    if mode == "off" or not files:
        verification = empty_verification()
        verification["performed"] = False
        verification["passed"] = True
        return verification

    verification = empty_verification()
    verification["performed"] = True
    details = verification["details"]

    project_path = get_project_path()
    if not project_path and project_context:
        project_path = project_context.get("project_path", "")

    syntax_passed = True
    for rel_path in files:
        full_path = normalize_path(rel_path, project_path)
        try:
            content = call_mcp_tool("read_file", {"path": full_path})
            if isinstance(content, str) and content.lstrip().startswith("ENOENT:"):
                raise FileNotFoundError(content)
        except Exception as exc:
            syntax_passed = False
            details.append(
                {
                    "type": "syntax",
                    "passed": False,
                    "message": f"{rel_path}: 读取失败 {exc}",
                }
            )
            continue

        validator = _pick_validator(skill_id, rel_path)
        errors = _run_validator(validator, content, rel_path)

        if errors:
            syntax_passed = False
            details.append(
                {
                    "type": "syntax",
                    "passed": False,
                    "message": f"{rel_path}: {'; '.join(errors[:3])}",
                }
            )
        else:
            details.append(
                {
                    "type": "syntax",
                    "passed": True,
                    "message": f"{rel_path}: 语法 OK",
                }
            )

    engine_passed = True
    if mode == "full":
        if Settings.is_unity_available() and is_mcp_connected("unity"):
            logger.info("verify_files: 调用 engine_compile")
            try:
                compile_result = call_mcp_tool("engine_compile", {})
                compile_data = json.loads(compile_result) if isinstance(compile_result, str) else compile_result

                if compile_data.get("success"):
                    details.append(
                        {
                            "type": "compile",
                            "passed": True,
                            "message": f"Unity 编译通过 ({compile_data.get('duration', 0):.1f}s)",
                        }
                    )
                else:
                    engine_passed = False
                    errors = compile_data.get("errors", [])
                    error_summary = "; ".join(
                        f"{item.get('file', '?')}:{item.get('line', '?')} {item.get('message', '')[:80]}"
                        for item in errors[:3]
                    )
                    details.append(
                        {
                            "type": "compile",
                            "passed": False,
                            "message": f"Unity 编译失败: {error_summary}",
                        }
                    )
            except Exception as exc:
                details.append(
                    {
                        "type": "compile",
                        "passed": False,
                        "message": f"Unity 编译调用失败: {exc}",
                    }
                )
                engine_passed = False
        else:
            details.append(
                {
                    "type": "compile",
                    "passed": True,
                    "message": "Unity 未配置，跳过真编译（降级到语法层）",
                }
            )

        if skill_id == "generate_test" and Settings.is_unity_available() and is_mcp_connected("unity") and engine_passed:
            logger.info("verify_files: 调用 engine_run_tests")
            try:
                test_result = call_mcp_tool("engine_run_tests", {})
                test_data = json.loads(test_result) if isinstance(test_result, str) else test_result

                passed = test_data.get("passed", 0)
                failed = test_data.get("failed", 0)
                skipped = test_data.get("skipped", 0)

                if failed == 0:
                    details.append(
                        {
                            "type": "test",
                            "passed": True,
                            "message": f"测试通过: {passed} 个（跳过 {skipped}）",
                        }
                    )
                else:
                    engine_passed = False
                    failures = test_data.get("failures", [])
                    fail_summary = "; ".join(
                        f"{item.get('name', '?')}: {item.get('message', '')[:80]}"
                        for item in failures[:3]
                    )
                    details.append(
                        {
                            "type": "test",
                            "passed": False,
                            "message": f"测试失败: {failed} 个. {fail_summary}",
                        }
                    )
            except Exception as exc:
                details.append(
                    {
                        "type": "test",
                        "passed": False,
                        "message": f"测试调用失败: {exc}",
                    }
                )
                engine_passed = False

    verification["passed"] = syntax_passed and engine_passed
    return verification


def run_fix_loop(
    verify_result: dict,
    retry_func: Callable,
    max_retries: int = 1,
) -> tuple:
    """通用修复循环。"""
    if verify_result["passed"]:
        return verify_result, [], 0

    current_verify = verify_result
    current_files: list[str] = []
    total_tokens = 0

    for attempt in range(max_retries):
        error_summary = "\n".join(
            f"- {detail['message']}"
            for detail in current_verify["details"]
            if not detail["passed"]
        )

        logger.info(f"run_fix_loop 第 {attempt + 1} 次修复尝试")
        new_files, tokens, err = retry_func(error_summary)
        total_tokens += tokens

        if err or not new_files:
            logger.warning(f"修复调用失败: {err}")
            return current_verify, current_files, total_tokens

        current_files = new_files
        break

    return current_verify, current_files, total_tokens
