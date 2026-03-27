import streamlit as st


st.header("🔗 资源依赖分析")
st.caption("固定流水线 — 解析 GUID → 搜索引用 → 报告")

project_context = st.session_state.get("project_context", {})
asset_candidates = (
    project_context.get("assets", [])
    or project_context.get("prefabs", [])
    or st.session_state.get("config_list", [])
)

if asset_candidates:
    target_asset = st.selectbox(
        "选择资源",
        asset_candidates,
        index=None,
        placeholder="请选择资源或配置文件",
    )
else:
    target_asset = st.text_input("输入资源路径", placeholder="Assets/Prefabs/Hero.prefab")

if st.button("🔗 分析依赖", use_container_width=True):
    if target_asset:
        st.info("TODO: 模块六实现")
    else:
        st.warning("请先选择或输入资源。")

st.text_area("依赖分析报告", value="", height=280, disabled=True, placeholder="这里会显示依赖引用结果")
