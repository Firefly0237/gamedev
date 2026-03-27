from pages._common import render_pipeline_page

render_pipeline_page(
    pipeline_key="precommit_workflow",
    title="提交前检查",
    description="汇总 git 状态和提交前检查信息。",
)
