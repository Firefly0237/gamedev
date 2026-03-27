import streamlit as st


st.header("🔄 需求实现")
st.caption("Supervisor 多 Agent 协作")

requirement = st.text_area("输入需求", height=150, placeholder="描述一个需要多 Agent 协作落地的完整功能需求")
st.info("Supervisor 会在后续模块中串联需求拆解、代码生成、测试生成和审查流程。")

if st.button("🚀 开始实现", type="primary", use_container_width=True):
    if requirement.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入需求描述。")

st.text_area("执行计划预览", value="", height=280, disabled=True, placeholder="这里会显示 Supervisor 的执行计划")
