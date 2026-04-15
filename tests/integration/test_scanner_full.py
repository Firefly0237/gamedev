"""Scanner 的集成测试。"""

from __future__ import annotations

import time

import pytest


pytestmark = pytest.mark.integration


class TestUnityScanner:
    def test_scan_returns_context(self, scanned_context):
        assert scanned_context["total_scripts"] >= 3

    def test_reference_graph_built(self, scanned_context):
        assert "reference_graph" in scanned_context
        assert "reverse_graph" in scanned_context
        assert "class_to_path" in scanned_context

    def test_coverage_analyzed(self, scanned_context):
        assert "test_coverage_ratio" in scanned_context
        assert "uncovered_scripts" in scanned_context

    def test_genre_detection(self, scanned_context):
        assert scanned_context["detected_genre"] != ""

    def test_schemas_generated(self, scanned_context, project_root):
        _ = scanned_context
        schema_dir = project_root / "context" / "project_schemas"
        schemas = list(schema_dir.glob("*.json"))
        assert len(schemas) >= 1


class TestIncrementalScan:
    def test_second_scan_faster(self, test_project_path):
        from scanner.unity_scanner import UnityScanner

        scanner = UnityScanner(test_project_path)
        scanner.clear_cache()

        t1 = time.time()
        scanner.scan()
        d1 = time.time() - t1

        t2 = time.time()
        scanner.scan()
        d2 = time.time() - t2

        assert d2 <= d1 * 1.5
