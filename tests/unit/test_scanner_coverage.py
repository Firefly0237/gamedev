"""测试覆盖率分析的单元测试。"""

import pytest

from scanner.coverage import (
    analyze_coverage,
    extract_tested_class_names,
    is_excluded,
    is_test_file,
)


pytestmark = pytest.mark.unit


class TestCoverageHelpers:
    def test_is_test_file_by_directory(self):
        assert is_test_file("Assets/Tests/Editor/PlayerControllerTests.cs") is True

    def test_is_test_file_by_name(self):
        assert is_test_file("Assets/Scripts/TestDamageCalculator.cs") is True

    def test_non_test_file(self):
        assert is_test_file("Assets/Scripts/Player/PlayerController.cs") is False

    def test_is_excluded(self):
        assert is_excluded("Assets/Plugins/SomeLib/Plugin.cs") is True
        assert is_excluded("Assets/Scripts/Game/Foo.cs") is False

    def test_extract_tested_class_names(self):
        assert extract_tested_class_names("PlayerControllerTests") == ["PlayerController"]
        assert extract_tested_class_names("TestDamageCalculator") == ["DamageCalculator"]


class TestAnalyzeCoverage:
    def test_coverage_ratio(self):
        scripts = [
            {"path": "Assets/Scripts/Player/PlayerController.cs", "class_name": "PlayerController"},
            {"path": "Assets/Scripts/Combat/DamageCalculator.cs", "class_name": "DamageCalculator"},
            {"path": "Assets/Scripts/UI/HealthBar.cs", "class_name": "HealthBar"},
            {"path": "Assets/Tests/Editor/PlayerControllerTests.cs", "class_name": "PlayerControllerTests"},
        ]
        result = analyze_coverage(scripts)
        assert result["test_files"] == ["Assets/Tests/Editor/PlayerControllerTests.cs"]
        assert result["covered_classes"] == ["PlayerController"]
        assert len(result["uncovered_scripts"]) == 2
        assert result["coverable_count"] == 3
        assert result["coverage_ratio"] == pytest.approx(1 / 3)
