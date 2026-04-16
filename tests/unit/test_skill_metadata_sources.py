"""Skill 元数据来源测试。"""

from pathlib import Path

import pytest

import app
from context import loader


pytestmark = pytest.mark.unit


class TestSkillMetadataSources:
    def test_loader_prefers_yaml_metadata_over_md_title(self, tmp_path, monkeypatch):
        skill_dir = tmp_path / "common"
        skill_dir.mkdir(parents=True)
        (skill_dir / "test_skill.md").write_text("# Markdown Title\n\nbody", encoding="utf-8")
        (skill_dir / "test_skill.yaml").write_text(
            "\n".join(
                [
                    "skill_id: test_skill",
                    "name: YAML Title",
                    "description: yaml desc",
                    "route: orchestrator",
                ]
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(loader, "SKILLS_DIR", tmp_path)

        skill = loader.load_skill("test_skill")

        assert skill is not None
        assert skill["name"] == "YAML Title"
        assert skill["route"] == "orchestrator"

    def test_app_skill_options_use_yaml_name(self, tmp_path, monkeypatch):
        skill_dir = tmp_path / "common"
        skill_dir.mkdir(parents=True)
        (skill_dir / "demo_skill.md").write_text("# Markdown Name\n\nbody", encoding="utf-8")
        (skill_dir / "demo_skill.yaml").write_text(
            "\n".join(
                [
                    "skill_id: demo_skill",
                    "name: YAML Skill Name",
                    "description: yaml desc",
                    "route: agent_loop",
                ]
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(loader, "SKILLS_DIR", tmp_path)

        assert app._list_skill_options("common") == [("demo_skill", "YAML Skill Name")]
