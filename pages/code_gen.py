import streamlit as st


st.header("⌨️ 代码生成")
st.caption("ReAct 模式 — Agent 自主读取项目了解风格后生成代码")

requirement = st.text_area("输入需求", height=180, placeholder="例如：生成一个可配置冷却时间的技能系统控制器")
script_type = st.selectbox("脚本类型", ["MonoBehaviour", "ScriptableObject", "纯工具类", "Editor 扩展"])

if st.button("⌨️ 生成", use_container_width=True):
    if requirement.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入生成需求。")

st.text_area("生成结果预览", value="", height=260, disabled=True, placeholder="这里会显示生成后的代码草稿")
