from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="GameDev", page_icon="🎮", layout="wide")


def init_session_state() -> None:
    defaults = {
        "project_context": {},
        "project_scanned": False,
        "project_path": "",
        "chat_history": [],
        "script_list": [],
        "shader_list": [],
        "config_list": [],
        "localization_list": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value


def build_navigation():
    return st.navigation(
        {
            "💻 代码": [
                st.Page(str(BASE_DIR / "pages" / "code_gen.py"), title="代码生成", icon="⌨️"),
                st.Page(str(BASE_DIR / "pages" / "code_review.py"), title="代码审查", icon="🔍"),
                st.Page(str(BASE_DIR / "pages" / "code_test_gen.py"), title="测试生成", icon="🧪"),
                st.Page(str(BASE_DIR / "pages" / "code_shader_gen.py"), title="Shader 生成", icon="✨"),
                st.Page(str(BASE_DIR / "pages" / "code_performance.py"), title="性能审计", icon="⚡"),
            ],
            "📋 内容": [
                st.Page(str(BASE_DIR / "pages" / "content_config_gen.py"), title="配置生成", icon="📊"),
                st.Page(str(BASE_DIR / "pages" / "content_level_design.py"), title="关卡设计", icon="🗺️"),
                st.Page(str(BASE_DIR / "pages" / "content_dialogue.py"), title="对话剧情", icon="💬"),
                st.Page(str(BASE_DIR / "pages" / "content_localization.py"), title="本地化", icon="🌐"),
                st.Page(str(BASE_DIR / "pages" / "content_dependency.py"), title="资源依赖分析", icon="🔗"),
            ],
            "🎨 美术": [
                st.Page(str(BASE_DIR / "pages" / "art_asset_gen.py"), title="美术资产生成", icon="🎨"),
            ],
            "🔄 工作流": [
                st.Page(str(BASE_DIR / "pages" / "workflow_requirement.py"), title="需求实现", icon="🚀"),
                st.Page(str(BASE_DIR / "pages" / "workflow_precommit.py"), title="提交前检查", icon="✅"),
            ],
            "📜 Git": [
                st.Page(str(BASE_DIR / "pages" / "git_panel.py"), title="Git 面板", icon="📜"),
            ],
        }
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.title("🎮 GameDev")

        with st.expander("⚙️ API 设置", expanded=False):
            st.text_input(
                "DeepSeek API Key",
                value=os.getenv("DEEPSEEK_API_KEY", ""),
                type="password",
                key="ui_deepseek_api_key",
                help="当前仅提供输入框结构，后续模块会接入真实 LLM 调用。",
            )

        unity_project_path = st.text_input(
            "Unity 项目路径",
            value=st.session_state.project_path or os.getenv("UNITY_PROJECT_PATH", ""),
            placeholder="例如：D:/UnityProjects/MyGame",
            key="ui_unity_project_path",
        )

        if st.button("🔍 扫描项目", use_container_width=True):
            candidate_path = unity_project_path.strip()
            if not candidate_path:
                st.warning("请输入 Unity 项目路径。")
            else:
                normalized_path = str(Path(candidate_path).expanduser())
                # TODO: 在后续模块中调用 UnityScanner 执行真实项目扫描。
                st.session_state.project_context = {
                    "project_path": normalized_path,
                    "engine": "unity",
                    "scenes": [],
                    "assets": [],
                    "config_files": [],
                    "localization_files": [],
                    "shader_files": [],
                    "mcp_connected": False,
                }
                st.session_state.project_scanned = True
                st.session_state.project_path = normalized_path
                st.session_state.script_list = []
                st.session_state.shader_list = []
                st.session_state.config_list = []
                st.session_state.localization_list = []
                st.info("TODO: 扫描器集成将在后续模块中实现，当前已写入占位项目上下文。")

        if st.session_state.project_scanned:
            context = st.session_state.project_context
            scripts = st.session_state.script_list
            scenes = context.get("scenes", [])
            mcp_connected = bool(context.get("mcp_connected", False))

            st.caption(f"当前项目：{st.session_state.project_path}")
            col1, col2, col3 = st.columns(3)
            col1.metric("脚本数", len(scripts))
            col2.metric("场景数", len(scenes))
            col3.metric("MCP", "在线" if mcp_connected else "离线")

            status_color = "#16a34a" if mcp_connected else "#dc2626"
            status_text = "已连接" if mcp_connected else "未连接"
            st.markdown(
                (
                    "<div style='display:flex;align-items:center;gap:0.5rem;'>"
                    f"<span style='width:10px;height:10px;border-radius:999px;background:{status_color};display:inline-block;'></span>"
                    f"<span>MCP 状态：{status_text}</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

        st.divider()

        with st.expander("📋 执行历史", expanded=False):
            # TODO: 在后续模块中接入数据库中的执行历史记录。
            st.info("TODO: 执行历史将在后续模块中实现。")


def main() -> None:
    init_session_state()
    render_sidebar()
    nav = build_navigation()
    nav.run()


if __name__ == "__main__":
    main()
