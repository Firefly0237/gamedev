"""引用关系图谱的单元测试。"""

import pytest

from scanner.reference_graph import (
    build_reference_graph,
    extract_references,
    get_impact_scope,
    get_related_scripts,
)


pytestmark = pytest.mark.unit


class TestExtractReferences:
    def test_basic_class_references(self):
        code = """
using UnityEngine;
namespace MyGame.Player {
    public class PlayerController : MonoBehaviour {
        private DamageCalculator calculator;
        private InventorySystem inventory;
    }
}
"""
        refs = extract_references(code)
        assert "DamageCalculator" in refs
        assert "InventorySystem" in refs

    def test_builtin_types_filtered(self):
        refs = extract_references("public class Foo : MonoBehaviour { void X() { int y = 0; } }")
        assert "MonoBehaviour" not in refs
        assert "int" not in refs

    def test_generic_type_references(self):
        refs = extract_references("List<WeaponItem> weapons; Dictionary<string, Achievement> map;")
        assert "WeaponItem" in refs
        assert "Achievement" in refs

    def test_namespace_and_static_call_references(self):
        refs = extract_references(
            "var calc = new MyGame.Combat.DamageCalculator(); DamageCalculator.CalculateDamage();"
        )
        assert "DamageCalculator" in refs

    def test_using_namespace_to_classes(self):
        code = "using MyGame.Combat; public class Foo { private DamageCalculator calc; }"
        refs = extract_references(code, {"MyGame.Combat": ["DamageCalculator"]})
        assert "DamageCalculator" in refs


class TestGraphHelpers:
    @pytest.fixture
    def sample_scripts(self):
        return [
            {
                "class_name": "PlayerController",
                "path": "Assets/Scripts/Player/PlayerController.cs",
                "_raw_references": {"DamageCalculator", "InventorySystem"},
            },
            {
                "class_name": "DamageCalculator",
                "path": "Assets/Scripts/Combat/DamageCalculator.cs",
                "_raw_references": set(),
            },
            {
                "class_name": "InventorySystem",
                "path": "Assets/Scripts/Systems/InventorySystem.cs",
                "_raw_references": {"DamageCalculator"},
            },
        ]

    def test_build_reference_graph(self, sample_scripts):
        ref_graph, reverse_graph, class_to_path = build_reference_graph(sample_scripts)
        assert ref_graph["PlayerController"] == ["DamageCalculator", "InventorySystem"]
        assert reverse_graph["DamageCalculator"] == ["InventorySystem", "PlayerController"]
        assert class_to_path["InventorySystem"].endswith("InventorySystem.cs")

    def test_get_related_scripts(self, sample_scripts):
        ref_graph, reverse_graph, class_to_path = build_reference_graph(sample_scripts)
        related = get_related_scripts("PlayerController", sample_scripts, ref_graph, reverse_graph, class_to_path)
        related_names = {script["class_name"] for script in related}
        assert related_names == {"DamageCalculator", "InventorySystem"}

    def test_get_impact_scope(self, sample_scripts):
        ref_graph, reverse_graph, _ = build_reference_graph(sample_scripts)
        impact = get_impact_scope("DamageCalculator", reverse_graph, depth=2)
        assert "PlayerController" in impact
        assert "InventorySystem" in impact
