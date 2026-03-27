import streamlit as st


st.header("📊 配置生成")
st.caption("固定流水线 — 生成 JSON 配置表 + C# 数据类")

requirement = st.text_area("输入需求", height=180, placeholder="例如：设计一个包含稀有度和掉落权重的装备配置表")

if st.button("📊 生成配置", use_container_width=True):
    if requirement.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入配置需求。")

st.text_area("配置输出预览", value="", height=260, disabled=True, placeholder="这里会显示 JSON 与 C# 数据类")
