import streamlit as st


st.header("🎨 美术资产生成")
st.caption("固定流水线")

requirement = st.text_area("输入需求", height=180, placeholder="例如：一套蒸汽朋克风格的背包与道具图标")
style = st.selectbox("风格", ["像素风", "卡通风", "扁平风", "写实风", "日系"])

if st.button("🎨 生成", use_container_width=True):
    if requirement.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入生成需求。")

st.text_area("资产生成说明", value="", height=260, disabled=True, placeholder="这里会显示美术资产提示词和产出说明")
