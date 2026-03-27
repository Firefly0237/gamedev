import streamlit as st


st.header("✅ 提交前检查")
st.caption("Supervisor — git status → 审查 → 测试覆盖 → 报告")
st.info("该流程会在后续模块中接入 Git、代码审查和测试覆盖分析。")

if st.button("🔍 开始检查", type="primary", use_container_width=True):
    st.info("TODO: 模块六实现")

st.text_area("检查报告", value="", height=300, disabled=True, placeholder="这里会显示提交前检查结果")
