import streamlit as st


st.header("✨ Shader 生成")
st.caption("固定流水线")

effect_description = st.text_area(
    "效果描述",
    height=180,
    placeholder="例如：带有扫描线和霓虹描边的科幻护盾 Shader",
)

if st.button("✨ 生成 Shader", use_container_width=True):
    if effect_description.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入效果描述。")

st.text_area("Shader 代码预览", value="", height=260, disabled=True, placeholder="这里会显示 Shader 草稿")
