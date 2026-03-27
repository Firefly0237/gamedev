import streamlit as st


st.header("⚡ 性能审计")
st.caption("ReAct 模式 — Agent 自主调用工具扫描代码+资源+配置")

scope = st.selectbox("审计范围", ["全项目", "指定目录"])
target_directory = ""
if scope == "指定目录":
    target_directory = st.text_input("目标目录", placeholder="Assets/Scripts/Combat")

if st.button("⚡ 开始审计", use_container_width=True):
    if scope == "指定目录" and not target_directory.strip():
        st.warning("请输入要审计的目录。")
    else:
        st.info("TODO: 模块六实现")

st.text_area("审计报告", value="", height=300, disabled=True, placeholder="这里会显示性能审计结果")
