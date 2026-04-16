from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass


@dataclass
class Recommendation:
    skill: str
    label: str
    reason: str
    weight: int


_SKILL_LABELS = {
    "review_code": "🔍 代码审查",
    "modify_config": "📊 配置修改",
    "modify_code": "🧱 代码修改",
    "generate_test": "🧪 测试生成",
    "generate_system": "🛠 系统实现",
    "analyze_perf": "⚡ 性能分析",
    "translate": "🌐 本地化",
}


def _skill_label(skill: str) -> str:
    return _SKILL_LABELS.get(skill, skill)


def _extract_class_names(user_text: str, project_context: dict) -> list[str]:
    if not user_text:
        return []
    class_to_path = project_context.get("class_to_path", {})
    matched = [class_name for class_name in class_to_path.keys() if class_name and class_name in user_text]
    return matched[:2]


def _from_scan(project_context: dict) -> list[Recommendation]:
    recs: list[Recommendation] = []
    total_scripts = project_context.get("total_scripts", 0)
    uncovered = project_context.get("uncovered_scripts", [])
    config_files = project_context.get("config_files", [])
    localization_files = project_context.get("localization_files", [])
    scripts = project_context.get("scripts", [])

    if total_scripts > 0:
        recs.append(Recommendation("review_code", _skill_label("review_code"), f"{total_scripts} 个脚本可审查", 40))
    if config_files:
        recs.append(
            Recommendation("modify_config", _skill_label("modify_config"), f"发现 {len(config_files)} 个配置文件", 45)
        )
    if localization_files:
        recs.append(Recommendation("translate", _skill_label("translate"), "发现语言文件", 35))
    if uncovered:
        recs.append(
            Recommendation("generate_test", _skill_label("generate_test"), f"{len(uncovered)} 个脚本仍无测试", 55)
        )

    has_update = any(
        any(name in ("Update", "FixedUpdate") for name in script.get("unity_methods", []))
        for script in scripts
    )
    if has_update:
        recs.append(Recommendation("analyze_perf", _skill_label("analyze_perf"), "检测到 Update/FixedUpdate", 38))

    return recs


def compute_dynamic_recommendations(
    project_context: dict,
    chat_history: list,
    task_logs: list,
) -> list[dict]:
    """三信号融合：扫描结果 + 聊天上下文 + 历史行为。"""
    recommendations: list[Recommendation] = []
    recommendations.extend(_from_scan(project_context))

    last_user = next((msg for msg in reversed(chat_history or []) if msg.get("role") == "user"), None)
    if last_user:
        mentioned_classes = _extract_class_names(last_user.get("content", ""), project_context)
        uncovered = {item.get("class_name", "") for item in project_context.get("uncovered_scripts", [])}
        for class_name in mentioned_classes:
            recommendations.append(
                Recommendation("review_code", f"🔍 审查 {class_name}", f"你刚刚提到了 {class_name}", 100)
            )
            if class_name in uncovered:
                recommendations.append(
                    Recommendation(
                        "generate_test",
                        f"🧪 为 {class_name} 生成测试",
                        f"{class_name} 目前未被测试覆盖",
                        90,
                    )
                )

    if task_logs:
        recent_skills = [task.get("pipeline_type", "") for task in task_logs[:5] if task.get("pipeline_type")]
        if recent_skills:
            skill_id, _ = Counter(recent_skills).most_common(1)[0]
            recommendations.append(
                Recommendation(skill_id, f"⚡ 再跑一次 {skill_id}", "最近常用的操作", 50)
            )

    deduped: list[Recommendation] = []
    seen = set()
    for rec in sorted(recommendations, key=lambda item: (-item.weight, item.label)):
        if rec.skill in seen:
            continue
        seen.add(rec.skill)
        deduped.append(rec)

    return [asdict(item) for item in deduped[:5]]
