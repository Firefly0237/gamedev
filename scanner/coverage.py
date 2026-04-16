from config.logger import logger


EXCLUDE_PATH_PATTERNS = [
    "Assets/Editor/",
    "Assets/Plugins/",
    "Assets/ThirdParty/",
    "Assets/StreamingAssets/",
    "Packages/",
]

TEST_PATH_INDICATORS = ["Tests/", "Test/", "/EditMode/", "/PlayMode/"]


def is_test_file(rel_path: str) -> bool:
    """判断一个 .cs 文件是否是测试文件。"""
    if not rel_path.endswith(".cs"):
        return False

    rel_path_norm = rel_path.replace("\\", "/")
    if any(indicator in rel_path_norm for indicator in TEST_PATH_INDICATORS):
        return True

    file_name = rel_path_norm.split("/")[-1]
    if file_name.endswith("Tests.cs") or file_name.endswith(".Tests.cs"):
        return True
    if file_name.startswith("Test") and len(file_name) > 7:
        rest = file_name[4:-3]
        if rest and rest[0].isupper() and rest not in ("Utils", "Helper", "Helpers", "Runner"):
            return True

    return False


def is_excluded(rel_path: str) -> bool:
    """判断一个脚本是否应该被排除出覆盖率分析。"""
    rel_path_norm = rel_path.replace("\\", "/")
    return any(pattern in rel_path_norm for pattern in EXCLUDE_PATH_PATTERNS)


def extract_tested_class_names(test_class_name: str) -> list[str]:
    """从测试类名推导被测源类名候选。"""
    candidates = []

    if test_class_name.endswith("Tests"):
        candidates.append(test_class_name[:-5])
    elif test_class_name.endswith("Test"):
        candidates.append(test_class_name[:-4])

    if test_class_name.startswith("Test") and len(test_class_name) > 4:
        candidates.append(test_class_name[4:])

    return candidates


def analyze_coverage(scripts: list[dict]) -> dict:
    """分析测试覆盖（文件级命名匹配覆盖率）。"""
    test_files = []
    test_classes = []
    coverable_scripts = []

    for script in scripts:
        path = script.get("path", "")
        class_name = script.get("class_name", "")

        if is_test_file(path):
            test_files.append(path)
            if class_name:
                test_classes.append(class_name)
        elif not is_excluded(path) and class_name:
            coverable_scripts.append(script)

    coverable_class_names = {script["class_name"] for script in coverable_scripts}
    covered_classes = set()

    for test_class in test_classes:
        for candidate in extract_tested_class_names(test_class):
            if candidate in coverable_class_names:
                covered_classes.add(candidate)

    uncovered_scripts = [script for script in coverable_scripts if script["class_name"] not in covered_classes]
    coverable_count = len(coverable_scripts)
    coverage_ratio = len(covered_classes) / coverable_count if coverable_count > 0 else 0.0

    logger.info(
        f"测试覆盖：{len(covered_classes)}/{coverable_count} ({coverage_ratio:.0%}) | 测试文件 {len(test_files)} 个"
    )

    return {
        "test_files": sorted(test_files),
        "covered_classes": sorted(covered_classes),
        "uncovered_scripts": uncovered_scripts,
        "coverage_ratio": coverage_ratio,
        "coverable_count": coverable_count,
    }
