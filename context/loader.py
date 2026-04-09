import json
import re
from pathlib import Path

from config.logger import logger
from config.settings import Settings


SKILLS_DIR = Path(Settings.SKILLS_DIR)
SCHEMAS_DIR = Path(Settings.SCHEMAS_DIR)

KEYWORD_MAP = {
    "review_code": ["审查", "检查", "review", "代码质量"],
    "modify_config": ["改", "修改", "调整", "设置为", "改成"],
    "modify_code": ["改代码", "修改方法", "重构", "改变量"],
    "generate_test": ["测试", "test", "生成测试", "写测试"],
    "generate_system": ["实现", "做一个", "创建系统", "新功能", "新模块", "加一个"],
    "generate_shader": ["shader", "着色器", "视觉效果", "材质"],
    "generate_ui": ["ui", "面板", "界面", "hud", "菜单"],
    "generate_editor_tool": ["编辑器工具", "自定义窗口", "inspector"],
    "translate": ["翻译", "本地化", "多语言", "localization"],
    "analyze_deps": ["依赖", "引用", "orphan", "guid"],
    "analyze_perf": ["性能", "优化", "审计", "performance"],
    "summarize_requirement": ["需求", "拆解", "规划", "计划"],
}

FIELD_ALIAS_MAP = {
    "damage": ["伤害", "攻击力", "攻击"],
    "attackspeed": ["攻速", "攻击速度"],
    "critrate": ["暴击", "暴击率"],
    "price": ["价格", "售价", "金币"],
    "movespeed": ["移动速度", "速度", "移速"],
    "maxhealth": ["生命", "血量", "最大生命"],
}


def _parse_skill_file(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.stem

    trigger_text = ""
    not_for = ""
    for line in lines:
        if line.startswith("触发条件："):
            trigger_text = line.replace("触发条件：", "", 1).strip()
        elif line.startswith("不适用于："):
            not_for = line.replace("不适用于：", "", 1).strip()

    return {
        "skill_id": path.stem,
        "name": title,
        "trigger_text": trigger_text,
        "not_for": not_for,
        "content": content,
        "path": str(path.as_posix()),
    }


def load_skill(skill_name: str) -> dict | None:
    for path in SKILLS_DIR.rglob(f"{skill_name}.md"):
        return _parse_skill_file(path)
    return None


def load_all_skills() -> list[dict]:
    if not SKILLS_DIR.exists():
        return []

    skills = [_parse_skill_file(path) for path in sorted(SKILLS_DIR.rglob("*.md"))]
    logger.debug(f"加载 {len(skills)} 个 Skill")
    return skills


def match_skill(user_input: str, detected_genre: str = "unknown") -> dict | None:
    skills = load_all_skills()
    user_lower = user_input.lower()

    if any(word in user_lower for word in ["审查", "review", "检查代码", "代码质量"]):
        skill = load_skill("review_code")
        if skill:
            logger.info("Skill 匹配: review_code (explicit review intent)")
            return skill

    if "翻译" in user_lower or "本地化" in user_lower or "localization" in user_lower:
        skill = load_skill("translate")
        if skill:
            logger.info("Skill 匹配: translate (explicit translation intent)")
            return skill

    best_skill = None
    best_score = 0

    for skill in skills:
        score = 0
        skill_id = skill["skill_id"]

        for kw in KEYWORD_MAP.get(skill_id, []):
            if kw.lower() in user_lower:
                score += 10

        trigger = skill.get("trigger_text", "").lower()
        for word in re.findall(r"[\u4e00-\u9fff]+|[a-z]+", trigger):
            if len(word) >= 2 and word in user_lower:
                score += 5

        skill_path = skill.get("path", "")
        if detected_genre != "unknown" and f"/{detected_genre}/" in skill_path:
            score += 3

        if score > best_score:
            best_score = score
            best_skill = skill

    if best_skill and best_score > 0:
        logger.info(f"Skill 匹配: {best_skill['skill_id']} (score={best_score})")
        return best_skill

    logger.info("未匹配到 Skill")
    return None


def load_all_schemas() -> list[dict]:
    schemas: list[dict] = []
    if not SCHEMAS_DIR.exists():
        return schemas

    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        try:
            schemas.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            logger.warning(f"Schema 加载失败: {path}")
    return schemas


def match_schema(user_input: str) -> dict | None:
    schemas = load_all_schemas()
    user_lower = user_input.lower()
    best = None
    best_score = 0

    for schema in schemas:
        score = 0
        sample = schema.get("sample_record", {})
        if isinstance(sample, dict):
            for value in sample.values():
                if isinstance(value, str) and len(value) >= 2 and value.lower() in user_lower:
                    score += 10

        for value in schema.get("sample_values", []):
            if isinstance(value, str) and len(value) >= 2 and value.lower() in user_lower:
                score += 10

        for field in schema.get("fields", []):
            field_lower = field.lower()
            if field_lower in user_lower:
                score += 5
            for alias in FIELD_ALIAS_MAP.get(field_lower, []):
                if alias in user_input:
                    score += 5

        file_path = schema.get("file_path", "").lower()
        for part in re.split(r"[/\\.]", file_path):
            if len(part) >= 3 and part in user_lower:
                score += 3

        if score > best_score:
            best_score = score
            best = schema

    if best and best_score > 0:
        logger.info(f"Schema 匹配: {best.get('file_path')} (score={best_score})")
        return best
    return None


def build_system_prompt(skill: dict = None, schema: dict = None, project_context: dict = None) -> str:
    parts: list[str] = []

    if project_context:
        overview = (
            "## 项目概览\n"
            f"引擎: {project_context.get('engine', '?')} {project_context.get('engine_version', '?')}\n"
            f"脚本: {project_context.get('total_scripts', 0)} 个\n"
            f"场景: {', '.join(project_context.get('scenes', [])[:5])}\n"
            f"类型: {project_context.get('detected_genre', 'unknown')}"
        )
        parts.append(overview)

        tree = project_context.get("directory_tree", "")
        if tree:
            parts.append(f"## 目录结构\n```\n{tree[:800]}\n```")

        scripts = project_context.get("scripts", [])
        if scripts:
            lines = ["## 项目脚本"]
            for script in scripts[:30]:
                base = f":{script['base_class']}" if script.get("base_class") else ""
                namespace = f" ({script['namespace']})" if script.get("namespace") else ""
                lines.append(f"- {script['class_name']}{base}{namespace} — {script['path']}")
                for field in script.get("public_fields", [])[:3]:
                    lines.append(f"  field: {field['type']} {field['name']}")
                for method in script.get("public_methods", [])[:3]:
                    lines.append(f"  method: {method['return_type']} {method['name']}()")
            parts.append("\n".join(lines))

    if skill:
        parts.append(skill["content"])

    if schema:
        schema_text = (
            "## 项目数据格式\n"
            f"文件: {schema.get('file_path', '?')}\n"
            f"字段: {', '.join(schema.get('fields', []))}\n"
            f"定位字段: {schema.get('locate_by', '?')}\n"
            f"记录数: {schema.get('record_count', '?')}\n\n"
            "示例记录:\n"
            "```json\n"
            f"{json.dumps(schema.get('sample_record', {}), ensure_ascii=False, indent=2)}\n"
            "```"
        )
        parts.append(schema_text)

    return "\n\n".join(parts)


def list_skills(genre: str = "common") -> list[str]:
    skill_dir = SKILLS_DIR / genre
    if not skill_dir.exists():
        return []
    return sorted(path.stem for path in skill_dir.glob("*.md"))


def get_recommended_skills(project_context: dict) -> list[dict]:
    recs: list[dict] = []

    if project_context.get("total_scripts", 0) > 0:
        recs.append(
            {
                "skill": "review_code",
                "label": "🔍 代码审查",
                "reason": f"{project_context['total_scripts']} 个脚本可审查",
            }
        )

    if project_context.get("config_files"):
        recs.append(
            {
                "skill": "modify_config",
                "label": "📊 配置修改",
                "reason": f"发现 {len(project_context['config_files'])} 个配置文件",
            }
        )

    scripts = project_context.get("scripts", [])
    has_update = any(
        any(method.get("name") in ("Update", "FixedUpdate") for method in script.get("public_methods", []))
        or any(name in ("Update", "FixedUpdate") for name in script.get("unity_methods", []))
        for script in scripts
    )
    if has_update:
        recs.append(
            {
                "skill": "analyze_perf",
                "label": "⚡ 性能分析",
                "reason": "检测到 Update 方法，可能有性能热点",
            }
        )

    genre = project_context.get("detected_genre", "unknown")
    if genre != "unknown":
        genre_skills = list_skills(genre)
        if genre_skills:
            recs.append(
                {
                    "skill": genre_skills[0],
                    "label": f"🎮 {genre_skills[0]}",
                    "reason": f"检测到 {genre} 项目",
                }
            )

    if project_context.get("localization_files"):
        recs.append({"skill": "translate", "label": "🌐 本地化", "reason": "发现语言文件"})

    return recs[:5]
