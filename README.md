# GameDev

An open-source, Unity-first agent workbench for game development.

GameDev combines task routing, structured file operations, multi-worker orchestration, MCP-based engine access, and skill-driven workflows to help developers review code, modify configs, generate gameplay systems, and verify changes against a real Unity project.

English | [中文](#中文说明)

---

## English

### Overview

GameDev is designed for **game development workflows**, not generic coding tasks.

It focuses on scenarios such as:

- changing gameplay or balance configs safely
- reviewing Unity C# code with project context
- generating tests, UI code, shaders, or editor tooling
- planning and executing multi-file system changes
- connecting to Unity through MCP for compile, test, and console feedback

The project is currently **Unity-first**, with architecture that leaves room for future workers such as art, config, and GUI agents.

### Core Features

- **Three execution routes**
  - `deterministic`: structured config/code modification
  - `agent_loop`: short-chain review, generation, translation, and validation tasks
  - `orchestrator`: plan-gated, multi-worker execution for larger tasks
- **Skill-driven workflows**
  - task behavior is defined by skill metadata and instruction files under `context/skills/common`
- **Unity MCP integration**
  - uses Coplay Unity MCP for compile, test, and console access
- **Model tiering with fallback**
  - routes different task types to different providers/models
  - fallback chain: `anthropic -> openai -> deepseek`
- **Local static analysis tools**
  - reference search, `.meta` parsing, asset stats, project settings, and config validation stay local and deterministic
- **Streamlit workbench UI**
  - includes plan approval, progressive disclosure, task cards, and task history recovery

### How It Works

```text
User Request
  -> Router
     -> Deterministic
        -> intent parsing
        -> validated structured edit
     -> Agent Loop
        -> tool use
        -> short execution loop
        -> verification
     -> Orchestrator
        -> planning
        -> plan approval
        -> worker execution
        -> final verification

Backends
  -> local scanner tools
  -> filesystem MCP
  -> git MCP
  -> Coplay Unity MCP
```

### Repository Layout

```text
agents/       LLM factory and model routing
config/       settings and logging
context/      skill metadata, skill instructions, and context loading
database/     task logs and checkpoint storage
graphs/       router, deterministic flow, agent loop, orchestrator, verification
mcp_tools/    MCP client management and Unity Coplay adapter
pages/        Streamlit UI components
scanner/      Unity project scanning and local deterministic tools
schemas/      structured contracts and Pydantic models
tools/        debug and reporting scripts
app.py        Streamlit entrypoint
```

### Getting Started

#### 1. Clone the repository

```bash
git clone https://github.com/Firefly0237/gamedev.git
cd gamedev
```

#### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

- Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

- macOS / Linux:

```bash
source venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
npm install -g @modelcontextprotocol/server-filesystem
pip install mcp-server-git
pip install uv
```

#### 4. Create a `.env`

Create a local `.env` file manually.

Minimum setup:

```bash
DEEPSEEK_API_KEY=your_key
```

Recommended setup:

```bash
DEEPSEEK_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
ENABLE_MODEL_TIERING=1
ENABLE_ORCHESTRATOR=1
DEFAULT_VERIFY_MODE=syntax
```

If only `DEEPSEEK_API_KEY` is configured, the project still runs, but generation and planning tasks will fall back to DeepSeek.

#### 5. Start the app

```bash
streamlit run app.py
```

### Unity Setup

To use real compile/test/log features, prepare your Unity project with Coplay Unity MCP:

1. Install `com.coplaydev.unity-mcp` in your Unity project
2. Open the Unity Editor for that project
3. Let GameDev scan and initialize the project from the UI

If Unity MCP is not available:

- local scanning and non-engine tasks still work
- engine-backed validation will degrade gracefully with structured unavailable errors

### Configuration Notes

Important runtime switches:

- `ENABLE_MODEL_TIERING=1`
  enables task-type based model routing
- `ENABLE_ORCHESTRATOR=1`
  enables orchestrated execution for system-generation tasks
- `DEFAULT_VERIFY_MODE=syntax|full`
  controls default verification depth

### Contributing

Contributions are welcome.

Good contribution areas include:

- new skills
- better Unity/game-dev workflows
- new worker integrations
- scanner improvements
- UI/UX improvements
- documentation cleanup

Please keep pull requests focused and scoped. For larger changes, open an issue or discussion first.

### Contributing Skills

Skill contributions are especially welcome.

To add a new skill:

1. Add a YAML metadata file under `context/skills/common/`
2. Add the matching Markdown instruction file
3. Define a clear `skill_id`, `description`, `route`, and trigger text
4. Keep instructions procedural and operational, not essay-style
5. In your PR description, include:
   - what the skill is for
   - one or two example prompts
   - whether it reads files, writes files, or requires Unity

Suggested examples of useful community skills:

- gameplay balancing
- localization QA
- prefab/config consistency checks
- UI prefab generation workflows
- build/release assistant skills
- project audit and refactor skills

### Project Status

Current state:

- `code_agent` is implemented
- `art_agent` and `config_agent` are placeholders for future expansion
- GUI-oriented agents and deeper engine automation are planned, not complete

### License

MIT

---

## 中文说明

### 项目简介

GameDev 是一个面向 **Unity 游戏开发场景** 的开源 Agent 工作台，而不是通用代码助手。

它主要解决这类问题：

- 安全地修改玩法或数值配置
- 带项目上下文地审查 Unity C# 代码
- 生成测试、UI 代码、Shader、编辑器工具
- 对多文件功能改动做计划、执行和验证
- 通过 MCP 连接 Unity，拿到编译、测试和控制台反馈

当前项目以 **Unity-first** 为目标，但底层已经预留了未来扩展到 `art / config / GUI` 等 worker 的架构空间。

### 核心能力

- **三条执行路径**
  - `deterministic`：配置/代码的结构化修改
  - `agent_loop`：审查、短链生成、翻译、验证等任务
  - `orchestrator`：带计划审批的多 worker 编排
- **Skill 驱动工作流**
  - 任务行为通过 `context/skills/common` 下的技能元数据和说明文件定义
- **Unity MCP 接入**
  - 通过 Coplay Unity MCP 获取编译、测试和控制台日志
- **模型分层与降级**
  - 按任务类型路由到不同模型
  - 降级链为 `anthropic -> openai -> deepseek`
- **本地静态分析工具**
  - 引用查询、`.meta` 解析、资源统计、ProjectSettings 读取、配置校验等能力保持本地确定性执行
- **Streamlit 工作台**
  - 包含计划审批、渐进式披露、任务卡片和历史任务恢复

### 工作方式

```text
用户请求
  -> Router
     -> Deterministic
        -> 意图解析
        -> 结构化修改
     -> Agent Loop
        -> 工具调用
        -> 短链执行
        -> 验证
     -> Orchestrator
        -> 规划
        -> 计划审批
        -> worker 执行
        -> 最终验证

后端能力
  -> 本地 scanner 工具
  -> 文件系统 MCP
  -> Git MCP
  -> Coplay Unity MCP
```

### 仓库结构

```text
agents/       LLM 工厂与模型路由
config/       配置与日志
context/      Skill 元数据、Skill 指令、上下文加载
database/     任务日志与 checkpoint
graphs/       路由、确定性链路、agent loop、orchestrator、验证
mcp_tools/    MCP 客户端管理与 Unity Coplay 适配
pages/        Streamlit 页面组件
scanner/      Unity 项目扫描与本地确定性工具
schemas/      结构化契约与 Pydantic 模型
tools/        调试与报表脚本
app.py        Streamlit 入口
```

### 快速开始

#### 1. 克隆仓库

```bash
git clone https://github.com/Firefly0237/gamedev.git
cd gamedev
```

#### 2. 创建虚拟环境

```bash
python -m venv venv
```

激活方式：

- Windows PowerShell：

```powershell
venv\Scripts\Activate.ps1
```

- macOS / Linux：

```bash
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
npm install -g @modelcontextprotocol/server-filesystem
pip install mcp-server-git
pip install uv
```

#### 4. 手动创建 `.env`

最小配置：

```bash
DEEPSEEK_API_KEY=你的key
```

推荐配置：

```bash
DEEPSEEK_API_KEY=你的key
ANTHROPIC_API_KEY=你的key
OPENAI_API_KEY=你的key
ENABLE_MODEL_TIERING=1
ENABLE_ORCHESTRATOR=1
DEFAULT_VERIFY_MODE=syntax
```

如果只配置了 `DEEPSEEK_API_KEY`，项目仍然可以运行，但生成和规划任务会降级到 DeepSeek。

#### 5. 启动应用

```bash
streamlit run app.py
```

### Unity 接入说明

如果要使用真实编译、测试、控制台日志能力，需要先准备好带 Coplay Unity MCP 的 Unity 项目：

1. 在 Unity 项目中安装 `com.coplaydev.unity-mcp`
2. 打开该项目的 Unity Editor
3. 在 GameDev UI 中扫描并初始化该项目

如果 Unity MCP 不可用：

- 本地扫描和不依赖引擎的任务仍可正常运行
- 引擎相关验证会优雅降级，返回结构化不可用结果

### 配置说明

几个关键开关：

- `ENABLE_MODEL_TIERING=1`
  启用按任务类型分层的模型路由
- `ENABLE_ORCHESTRATOR=1`
  启用系统生成类任务的 orchestrator 路径
- `DEFAULT_VERIFY_MODE=syntax|full`
  控制默认验证深度

### 参与贡献

欢迎贡献。

适合贡献的方向包括：

- 新技能
- 更好的 Unity / 游戏开发工作流
- 新 worker 集成
- scanner 能力增强
- UI/UX 改进
- 文档完善

请尽量保持 PR 聚焦、范围清晰。  
如果是较大的改动，建议先提 issue 或 discussion。

### 如何贡献 Skill

非常欢迎提交 Skill。

新增 Skill 时建议：

1. 在 `context/skills/common/` 下新增 YAML 元数据文件
2. 新增对应的 Markdown 指令文件
3. 明确写好 `skill_id`、`description`、`route` 和触发文本
4. 指令尽量写成操作手册，而不是说明文档
5. 在 PR 描述里补充：
   - 这个 skill 解决什么问题
   - 1 到 2 个示例 prompt
   - 它是否读文件、写文件、是否依赖 Unity

适合社区贡献的 Skill 类型例如：

- 数值平衡调整
- 本地化 QA
- Prefab / 配置一致性检查
- UI 生成工作流
- 构建与发布辅助
- 项目审计与重构辅助

### 当前状态

当前版本：

- `code_agent` 已实装
- `art_agent` 和 `config_agent` 仍是后续扩展位
- GUI 类 agent 和更深的引擎自动化还在后续计划中

### License

MIT
