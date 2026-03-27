from pages._common import render_pipeline_page

render_pipeline_page(
    pipeline_key="dependency_analysis",
    title="资源依赖",
    description="分析资源或脚本引用关系。",
    params_example={"target": "Assets/Prefabs/Player.prefab.meta"},
)
