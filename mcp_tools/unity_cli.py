import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from config.logger import logger
from config.settings import Settings


COMPILE_ERROR_PATTERN = re.compile(
    r"(?P<file>[^:()\n]+\.cs)\((?P<line>\d+),(?P<col>\d+)\):\s+"
    r"(?P<level>error|warning)\s+(?P<code>CS\d+):\s+(?P<message>.+)"
)

TEST_RESULT_PATTERN = re.compile(
    r"Tests\s+passed:\s+(?P<passed>\d+).*?failed:\s+(?P<failed>\d+).*?skipped:\s+(?P<skipped>\d+)",
    re.IGNORECASE,
)


def _check_unity() -> Optional[str]:
    """检查 Unity 可用性，不可用返回错误信息"""
    if not Settings.UNITY_EXECUTABLE_PATH:
        return "Unity 未配置：请在 .env 中设置 UNITY_EXECUTABLE_PATH"
    if not os.path.isfile(Settings.UNITY_EXECUTABLE_PATH):
        return f"Unity 路径无效：{Settings.UNITY_EXECUTABLE_PATH}"
    return None


def _find_default_log_path() -> str:
    """获取系统默认的 Unity Editor.log 路径"""
    import platform

    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Windows":
        return os.path.join(os.getenv("LOCALAPPDATA", ""), "Unity", "Editor", "Editor.log")
    if system == "Darwin":
        return os.path.join(home, "Library", "Logs", "Unity", "Editor.log")
    return os.path.join(home, ".config", "unity3d", "Editor.log")


def run_unity_compile(project_path: str) -> dict:
    """触发 Unity headless 编译并解析结果"""
    err = _check_unity()
    if err:
        return {
            "success": False,
            "errors": [],
            "warnings": [],
            "duration": 0.0,
            "fallback": err,
            "raw_log_tail": "",
        }

    project_path = os.path.abspath(project_path)
    if not os.path.isdir(os.path.join(project_path, "Assets")):
        return {
            "success": False,
            "errors": [{"file": "", "line": 0, "message": f"非 Unity 项目: {project_path}"}],
            "warnings": [],
            "duration": 0.0,
            "fallback": "",
            "raw_log_tail": "",
        }

    log_path = os.path.join(project_path, ".gamedev_unity.log")
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except OSError:
            pass

    cmd = [
        Settings.UNITY_EXECUTABLE_PATH,
        "-batchmode",
        "-quit",
        "-nographics",
        "-projectPath",
        project_path,
        "-logFile",
        log_path,
    ]

    logger.info(f"Unity 编译启动: {project_path}")
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            timeout=Settings.UNITY_BUILD_TIMEOUT,
            capture_output=True,
            text=True,
        )
        return_code = result.returncode
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "errors": [{"file": "", "line": 0, "message": f"Unity 编译超时 ({Settings.UNITY_BUILD_TIMEOUT}s)"}],
            "warnings": [],
            "duration": time.time() - t0,
            "fallback": "",
            "raw_log_tail": "",
        }
    except Exception as exc:
        return {
            "success": False,
            "errors": [{"file": "", "line": 0, "message": f"Unity 启动失败: {exc}"}],
            "warnings": [],
            "duration": time.time() - t0,
            "fallback": "",
            "raw_log_tail": "",
        }

    duration = time.time() - t0

    log_content = ""
    if os.path.exists(log_path):
        try:
            log_content = Path(log_path).read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            logger.warning(f"读取 Unity 日志失败: {exc}")

    errors = []
    warnings = []
    for match in COMPILE_ERROR_PATTERN.finditer(log_content):
        item = {
            "file": match.group("file").strip(),
            "line": int(match.group("line")),
            "code": match.group("code"),
            "message": match.group("message").strip(),
        }
        if match.group("level") == "error":
            errors.append(item)
        else:
            warnings.append(item)

    success = (return_code == 0) and (len(errors) == 0)

    logger.info(
        f"Unity 编译完成: success={success}, errors={len(errors)}, warnings={len(warnings)}, {duration:.1f}s"
    )

    try:
        os.remove(log_path)
    except OSError:
        pass

    return {
        "success": success,
        "errors": errors[:50],
        "warnings": warnings[:20],
        "duration": duration,
        "fallback": "",
        "raw_log_tail": log_content[-5000:],
    }


def run_unity_tests(project_path: str, test_filter: str = "") -> dict:
    """运行 Unity NUnit 测试"""
    err = _check_unity()
    if err:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": [],
            "duration": 0.0,
            "fallback": err,
        }

    project_path = os.path.abspath(project_path)
    log_path = os.path.join(project_path, ".gamedev_unity_test.log")
    result_xml = os.path.join(project_path, ".gamedev_test_results.xml")

    for path in (log_path, result_xml):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    cmd = [
        Settings.UNITY_EXECUTABLE_PATH,
        "-batchmode",
        "-nographics",
        "-projectPath",
        project_path,
        "-runTests",
        "-testPlatform",
        "EditMode",
        "-testResults",
        result_xml,
        "-logFile",
        log_path,
    ]
    if test_filter:
        cmd += ["-testFilter", test_filter]

    logger.info(f"Unity 测试启动: filter={test_filter or '全部'}")
    t0 = time.time()
    try:
        subprocess.run(cmd, timeout=Settings.UNITY_BUILD_TIMEOUT, capture_output=True)
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": [{"name": "", "message": f"测试超时 ({Settings.UNITY_BUILD_TIMEOUT}s)"}],
            "duration": time.time() - t0,
            "fallback": "",
        }
    except Exception as exc:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": [{"name": "", "message": f"Unity 启动失败: {exc}"}],
            "duration": time.time() - t0,
            "fallback": "",
        }

    duration = time.time() - t0
    passed = failed = skipped = 0
    failures = []

    if os.path.exists(result_xml):
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(result_xml)
            root = tree.getroot()

            for test_case in root.iter("test-case"):
                result = test_case.get("result", "")
                name = test_case.get("name", "")
                if result == "Passed":
                    passed += 1
                elif result == "Failed":
                    failed += 1
                    failure_node = test_case.find("failure")
                    message = ""
                    if failure_node is not None:
                        msg_node = failure_node.find("message")
                        if msg_node is not None:
                            message = (msg_node.text or "")[:500]
                    failures.append({"name": name, "message": message})
                elif result == "Skipped":
                    skipped += 1
        except Exception as exc:
            logger.warning(f"NUnit XML 解析失败: {exc}")

    logger.info(f"Unity 测试完成: passed={passed}, failed={failed}, skipped={skipped}, {duration:.1f}s")

    for path in (log_path, result_xml):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "failures": failures[:20],
        "duration": duration,
        "fallback": "",
    }


def get_unity_logs(lines: int = 100) -> str:
    """读取系统默认位置的 Editor.log 最后 N 行"""
    log_path = _find_default_log_path()
    if not os.path.exists(log_path):
        return f"Editor.log 不存在: {log_path}"
    try:
        all_lines = Path(log_path).read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(all_lines[-lines:])
    except Exception as exc:
        return f"读取失败: {exc}"
