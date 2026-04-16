def render_git_panel():
    import streamlit as st
    from mcp_tools.mcp_client import call_mcp_tool, is_mcp_connected

    st.header("📜 Git 版本控制")
    if st.button("↩️ 返回", key="git_back"):
        st.query_params.clear()
        st.rerun()

    if not is_mcp_connected("git"):
        st.warning("⚠️ Git MCP Server 未连接。请先扫描项目。")

    tab_status, tab_diff, tab_log, tab_commit = st.tabs(["状态", "Diff", "历史", "提交"])

    with tab_status:
        if st.button("🔄 刷新"):
            try:
                status = call_mcp_tool("git_status", {})
                st.code(status, language="text")
            except Exception as e:
                st.error(f"获取状态失败: {e}")

    with tab_diff:
        diff_file = st.text_input("文件路径（留空=全部）", key="diff_path")
        if st.button("查看 Diff"):
            try:
                args = {}
                if diff_file.strip():
                    args["file_path"] = diff_file.strip()
                diff = call_mcp_tool("git_diff_unified", args)
                st.code(diff or "没有差异", language="diff")
            except Exception as e:
                st.error(f"获取 Diff 失败: {e}")

    with tab_log:
        n = st.slider("条数", 5, 50, 10)
        if st.button("查看历史"):
            try:
                log = call_mcp_tool("git_log", {"count": n})
                st.code(log, language="text")
            except Exception as e:
                st.error(f"获取历史失败: {e}")

    with tab_commit:
        st.warning("⚠️ 提交不可撤销")
        files = st.text_input("暂存文件", value=".", key="commit_files")
        msg = st.text_input("Commit Message", key="commit_msg")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📋 预览"):
                try:
                    st.code(call_mcp_tool("git_status", {}), language="text")
                except Exception as e:
                    st.error(str(e))
        with c2:
            if st.button("📤 提交", type="primary"):
                if not msg:
                    st.warning("请填写 Message")
                else:
                    try:
                        call_mcp_tool("git_add", {"files": files.strip().split()})
                        result = call_mcp_tool("git_commit", {"message": msg})
                        st.success(f"✅ {result[:200]}")
                    except Exception as e:
                        st.error(f"提交失败: {e}")
