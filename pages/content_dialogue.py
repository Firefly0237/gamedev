import streamlit as st


st.header("💬 对话剧情")
st.caption("固定流水线 — 生成对话树 JSON + C# 管理器")

scene_description = st.text_area(
    "场景描述",
    height=180,
    placeholder="例如：主角初次见到导师时的分支对话，包含信任度判断",
)

if st.button("💬 生成对话", use_container_width=True):
    if scene_description.strip():
        st.info("TODO: 模块六实现")
    else:
        st.warning("请输入场景描述。")

st.text_area("对话预览", value="", height=300, disabled=True, placeholder="这里会显示对话树和管理器代码")
