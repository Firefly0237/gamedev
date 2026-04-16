# Changelog

## v1.4.0 - 2026-04-16

这次版本不是单点修补，而是把 `后续10-14` 收成一个可解释、可验证、可继续扩展的基线。

### Added

- 引入基于官方 `langgraph-supervisor` 的 orchestrator 框架
- 新增 `code_agent / art_agent / config_agent` WorkerSpec 体系
- 新增 Plan Gate 审批流与历史任务恢复
- 新增动态推荐区、折叠式任务卡、流式输出链路
- 新增 Coplay Unity MCP 适配层和本地 scanner 工具层
- 新增模型分层调试脚本 `tools/debug/dump_task_routing.py`
- 新增 24h 成本报表 `tools/reports/daily_cost.py`
- 新增 `task_logs.provider / task_logs.model` 埋点

### Changed

- `Supervisor` 业务主路径收口为 `orchestrator`
- Skill 元数据改为以 YAML 为权威来源
- `generate_system / summarize_requirement` 改为 `plan -> approval -> workers -> verify`
- Unity 接入从自建薄封装迁移到官方 Coplay 现状
- 本地静态能力不再伪装成 MCP 工具，统一走 local tool
- LLM 工厂从“单 DeepSeek”升级为“按 task_type 分层 + provider 降级链”
- `modify_config / modify_code` 改走 `intent_parse`
- planner 改走 `plan`
- `agent_loop` 改成按 skill 映射真实 `task_type`
- orchestrator 统计补齐 worker token，不再只记 planner

### Removed

- 下线自建 `mcp_server_unity.py`
- 下线自建 `mcp_server_gamedev.py`
- 删除旧的多处 `supervisor` 业务命名残留
- 删除旧式 Skill 路由硬编码和双来源元数据依赖

### Documentation

- 重写 `README.md`，对齐当前架构与配置方式
- 更新 `guide/项目设计与面试指南.md`
- 新增 `guide/面试话术卡.md`

### Verification

- `python -m pytest -q`
- 结果：`110 passed, 5 skipped`

### Notes

- 如果只配置了 `DEEPSEEK_API_KEY`，系统仍能运行，但 `generation / fix_loop / plan` 会降级到 DeepSeek
- 要真正启用 Haiku / Sonnet / GPT 分层，需要额外配置 `ANTHROPIC_API_KEY` 与 `OPENAI_API_KEY`
