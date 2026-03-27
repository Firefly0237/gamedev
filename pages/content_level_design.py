import streamlit as st


st.header("🗺️ 关卡设计")
st.caption("ReAct 模式")

level_description = st.text_area(
    "关卡描述",
    height=180,
    placeholder="例如：设计一个三阶段 Boss 追逐关卡，包含机关、解谜和战斗切换",
)

if st.button("🗺️ 设计关卡", use_container_width=True):
    if level_description.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入关卡描述。")

st.text_area("关卡方案预览", value="", height=300, disabled=True, placeholder="这里会显示关卡设计输出")
