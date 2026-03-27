from pages._common import render_pipeline_page

render_pipeline_page(
    pipeline_key="code_review",
    title="代码审查",
    description="对指定脚本执行启发式代码审查。",
    params_example={"file_path": "Assets/Scripts/PlayerController.cs"},
)
