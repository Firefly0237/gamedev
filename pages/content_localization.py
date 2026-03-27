import streamlit as st


st.header("🌐 本地化")
st.caption("固定流水线 — 翻译语言表，自动保护占位符")

localization_list = st.session_state.get("localization_list", [])
if localization_list:
    source_file = st.selectbox(
        "选择源文件",
        localization_list,
        index=None,
        placeholder="请选择源语言文件",
    )
else:
    source_file = st.text_input("输入源文件路径", placeholder="Assets/Localization/zh-CN.json")

target_languages = st.multiselect("目标语言", ["en", "ja", "ko", "fr", "de", "es", "pt", "ru"])

if st.button("🌐 翻译", use_container_width=True):
    if not source_file:
        st.warning("请先选择或输入源文件。")
    elif not target_languages:
        st.warning("请至少选择一种目标语言。")
    else:
        st.info("TODO: 模块六实现")

st.text_area("翻译结果预览", value="", height=280, disabled=True, placeholder="这里会显示本地化输出")
