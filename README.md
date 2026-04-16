# GameDev

面向 Unity 游戏开发的 Agent 工作台。当前版本已经从“单 Agent + 单模型 + 薄 Unity 封装”升级为：

- 三分叉路由：`deterministic / agent_loop / orchestrator`
- 官方 `langgraph-supervisor` 多 Worker 编排
- Coplay Unity MCP 真实接入
- 按任务分层的模型路由与降级链
- Streamlit Plan Gate + 渐进式披露 UI

## 当前能力

- **确定性修改**：`modify_config / modify_code` 走 `LLM 意图解析 -> Pydantic 校验 -> 代码执行`
- **Agent Loop**：审查、翻译、单文件生成、构建验证等短链任务
- **Orchestrator**：`generate_system / summarize_requirement` 走 `plan -> approval -> workers -> verify`
- **Unity 后端**：通过 Coplay Unity MCP 获取编译、测试、控制台日志
- **本地扫描器**：引用图谱、meta 解析、资源体积、ProjectSettings 等静态能力走本地 Python，不再伪装成 MCP
- **任务观测**：`task_logs` 记录 token、provider、model，任务结果可从历史恢复

## 架构

```text
User Input
  -> Router
     -> Deterministic
        -> intent_parse model
        -> validated file edits
     -> Agent Loop
        -> review / generation model
        -> tool calls
        -> verify
     -> Orchestrator
        -> plan model
        -> Plan Gate
        -> langgraph-supervisor workers
        -> outer verify

Tools
  -> FileSystem MCP
  -> Git MCP
  -> Coplay Unity MCP
  -> local scanner tools
```

## 模型分层

默认支持 3 家 provider：

- `deepseek`：低成本意图解析、审查、翻译
- `anthropic`：生成、修复、规划
- `openai`：Anthropic 不可用时的中间降级

默认降级链：

```text
anthropic -> openai -> deepseek
```

如果只配置了 `DEEPSEEK_API_KEY`，系统仍然可以运行，只是 `generation / plan / fix_loop` 也会降级到 DeepSeek。

## Quick Start

```bash
git clone https://github.com/Firefly0237/GameDev.git
cd GameDev
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python create_test_project.py
streamlit run app.py
```

最低配置：

- `DEEPSEEK_API_KEY`

推荐配置：

- `DEEPSEEK_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

这样 `plan / generation / fix_loop` 才会真正走分层模型，而不是全部降级到 DeepSeek。

## Unity 接入

当前 Unity 后端以 Coplay Unity MCP 为准。

前置依赖：

```bash
pip install uv
npm install -g @modelcontextprotocol/server-filesystem
pip install mcp-server-git
```

Unity 项目侧需要：

1. 在目标 Unity 项目中安装 `com.coplaydev.unity-mcp`
2. 打开 Unity Editor，让 Coplay 服务处于可连接状态
3. 在 GameDev 中扫描并初始化该项目

如果 Unity MCP 未连接：

- 本地扫描、配置修改、代码审查仍可运行
- `engine_compile / engine_run_tests` 会结构化降级为 `ENGINE_UNAVAILABLE`

## 关键开关

- `ENABLE_ORCHESTRATOR=1`
  启用 `generate_system / summarize_requirement` 的 orchestrator 路径
- `ENABLE_MODEL_TIERING=1`
  启用按任务分层的模型路由
- `DEFAULT_VERIFY_MODE=syntax|full`
  控制默认验证级别

## 测试

```bash
python -m pytest -q
```

当前基线：

- `110 passed, 5 skipped`

E2E 默认跳过，设置 `RUN_E2E=1` 可启用。

## 项目结构

- `app.py`：Streamlit 主入口
- `agents/`：LLM 工厂与模型路由
- `graphs/`：router、deterministic、agent_loop、orchestrator、verify
- `mcp_tools/`：MCP 客户端与 Unity Coplay 适配
- `scanner/`：Unity 项目扫描与本地静态工具
- `context/`：Skill YAML + Markdown 及 schema/loader
- `database/`：SQLite task log 与 checkpoint
- `pages/`：Plan Gate、任务卡、技能页、渐进披露 UI
- `tests/`：unit / integration / e2e

## 当前边界

- `code_agent` 已实装
- `art_agent / config_agent` 仍是 stub，占位为后续美术、配置、GUI agent 扩展
- GUI agent、运行时场景操控、更深的 Unity 编辑器能力还未实装
- Streamlit 适合工作台原型，不是最终 IDE 形态

## 设计文档

工作区根目录的 `guide/` 下保留了完整设计文档，包含：

- 项目评审与改进建议
- Unity 接入 / Supervisor 重构 / 模型选型方案
- 后续 10-14 的分阶段设计与落地说明
- 项目设计与面试指南
- 面试话术卡

## License

MIT
