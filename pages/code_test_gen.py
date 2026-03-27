import streamlit as st


st.header("🧪 测试生成")
st.caption("固定流水线 — 读取脚本 → 生成 NUnit 测试")

script_list = st.session_state.get("script_list", [])
if script_list:
    selected_script = st.selectbox(
        "选择脚本",
        script_list,
        index=None,
        placeholder="请选择脚本",
    )
else:
    selected_script = st.text_input("输入脚本路径", placeholder="Assets/Scripts/Combat/DamageSystem.cs")

if st.button("🧪 生成测试", use_container_width=True):
    if selected_script:
        st.info("TODO: 模块六实现")
    else:
        st.warning("请先选择或输入脚本。")

st.text_area("测试代码预览", value="", height=260, disabled=True, placeholder="这里会显示 NUnit 测试代码")
