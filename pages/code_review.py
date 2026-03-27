import streamlit as st


st.header("🔍 代码审查")
st.caption("ReAct 模式 — Agent 可能自主查看关联文件")

script_list = st.session_state.get("script_list", [])
if script_list:
    selected_script = st.selectbox(
        "选择待审查脚本",
        script_list,
        index=None,
        placeholder="请选择脚本",
    )
else:
    selected_script = st.text_input("输入脚本路径", placeholder="Assets/Scripts/PlayerController.cs")

review_focus = st.multiselect("审查维度", ["性能", "规范", "安全性", "可维护性"], default=["性能", "规范"])

if st.button("🔍 审查", use_container_width=True):
    if selected_script:
        st.info("TODO: 模块六实现")
    else:
        st.warning("请先选择或输入脚本。")

st.text_area("审查结果", value="", height=260, disabled=True, placeholder="这里会显示审查报告")
