# GameDev

An open-source, Unity-first agent workbench for game development.

GameDev is built around a simple idea: game development tasks benefit from different execution styles. Some tasks need structured and deterministic edits, some need short tool-using loops, and some need planning, approval, and multi-step orchestration. This project turns that idea into a practical workflow for Unity projects.

English | [中文](#中文说明)

---

## English

### Overview

GameDev helps developers work with Unity projects through a combination of:

- task routing
- structured file operations
- multi-worker orchestration
- MCP-based Unity access
- skill-driven workflows

Typical use cases include:

- updating gameplay and balance configs
- reviewing Unity C# code with project context
- generating tests, shaders, UI code, and editor tools
- planning and executing multi-file gameplay systems
- verifying changes with compile, test, and console feedback

### Design Principles

GameDev is organized around five core design principles.

#### 1. Route tasks by execution style

Different kinds of work call for different execution paths.

- `deterministic`
  for structured config/code modifications
- `agent_loop`
  for review, generation, translation, and validation tasks
- `orchestrator`
  for larger, multi-file tasks that benefit from planning and approval

#### 2. Keep critical edits structured

Config and code modification flows use structured parsing, validation, and controlled writes. This keeps important project changes observable and consistent.

#### 3. Separate planning, execution, and verification

Larger tasks are easier to trust when the system makes its plan visible, executes step by step, and verifies outputs at the end.

#### 4. Treat Unity as a first-class backend

GameDev integrates with Unity through Coplay Unity MCP for compile, test, and console workflows, while keeping local scanning and static analysis tools fast and deterministic.

#### 5. Use skills as the extension surface

Project workflows are defined through skill metadata and instruction files, making it straightforward for contributors to add new domain-specific capabilities.

### Main Features

- **Three execution routes**
  - `deterministic`
  - `agent_loop`
  - `orchestrator`
- **Skill-driven workflows**
  - skills live in `context/skills/common`
- **Plan-gated orchestration**
  - larger tasks can be reviewed before execution
- **Unity MCP integration**
  - compile, test, and console access through Coplay Unity MCP
- **Model tiering**
  - task-type based routing with provider fallback
- **Local scanner tools**
  - reference search, `.meta` parsing, asset stats, project settings, and config validation
- **Workbench UI**
  - Streamlit-based interface with task cards, history, and progressive disclosure

### Architecture

```text
User Request
  -> Router
     -> Deterministic
        -> intent parsing
        -> structured validated edit
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

- Windows PowerShell

```powershell
venv\Scripts\Activate.ps1
```

- macOS / Linux

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

#### 4. Create a local `.env`

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

A DeepSeek-only setup supports the full app. A multi-provider setup enables the full model-tiering path for planning and generation tasks.

#### 5. Run the app

```bash
streamlit run app.py
```

### Unity Setup

To enable compile, test, and console workflows:

1. install `com.coplaydev.unity-mcp` in your Unity project
2. open the Unity Editor for that project
3. scan and initialize the project from the GameDev UI

### Configuration Notes

Key runtime switches:

- `ENABLE_MODEL_TIERING=1`
  enables task-type based model routing
- `ENABLE_ORCHESTRATOR=1`
  enables orchestrated execution for system-generation tasks
- `DEFAULT_VERIFY_MODE=syntax|full`
  controls verification depth

### Contributing

Contributions are welcome.

Good contribution areas include:

- new skills
- Unity workflow improvements
- scanner improvements
- new worker integrations
- UI and usability improvements
- documentation refinement

For larger ideas, opening an issue or discussion first is helpful.

### Contributing Skills

Skill contributions are especially welcome.

To add a skill:

1. add a YAML metadata file under `context/skills/common/`
2. add the matching Markdown instruction file
3. define a clear `skill_id`, `description`, `route`, and trigger text
4. write instructions as procedural guidance
5. include in your PR:
   - what the skill is for
   - one or two example prompts
   - whether it reads files, writes files, or requires Unity

Useful community skill ideas:

- gameplay balancing
- localization QA
- prefab/config consistency checks
- UI prefab generation workflows
- build/release assistant skills
- refactor and project-audit skills

### Project Status

Current implementation highlights:

- `code_agent` is implemented
- `art_agent` and `config_agent` define extension slots for future workers
- model tiering, orchestrator routing, and Unity MCP integration are available in the current codebase

### License

MIT

---

## 中文说明

### 项目简介

GameDev 是一个面向 Unity 游戏开发的开源 Agent 工作台。

它的整体设计思路很直接：游戏开发任务适合不同的执行方式。有些任务适合结构化、确定性的修改，有些任务适合短链工具循环，有些任务适合先规划、再审批、再多步执行。GameDev 把这套思路落成了一套可运行的 Unity 工作流。

GameDev 主要服务这些场景：

- 调整玩法和数值配置
- 带项目上下文地审查 Unity C# 代码
- 生成测试、Shader、UI 代码、编辑器工具
- 规划并执行多文件功能系统改动
- 通过 Unity 编译、测试、控制台反馈验证改动结果

### 设计原则

GameDev 的总体设计围绕五条原则展开。

#### 1. 按任务执行方式做路由

不同类型的工作适合不同路径。

- `deterministic`
  负责结构化配置/代码修改
- `agent_loop`
  负责审查、生成、翻译、验证等短链任务
- `orchestrator`
  负责更大的多文件任务，支持规划和审批

#### 2. 关键修改保持结构化

配置和代码修改链路使用结构化解析、校验和受控写入，让关键项目改动保持可观察、可追踪。

#### 3. 规划、执行、验证分层清晰

更大的任务在“计划可见、分步执行、最终验证”的结构下更容易理解，也更容易协作。

#### 4. Unity 作为一等后端能力

GameDev 通过 Coplay Unity MCP 接入编译、测试和控制台工作流，同时把本地扫描和静态分析能力保留在本地，保持速度和确定性。

#### 5. Skill 作为扩展入口

项目工作流通过 Skill 元数据和指令文件定义，方便贡献者持续增加新的领域能力。

### 主要功能

- **三条执行路径**
  - `deterministic`
  - `agent_loop`
  - `orchestrator`
- **Skill 驱动工作流**
  - Skill 位于 `context/skills/common`
- **带审批的编排执行**
  - 较大的任务可以先看计划再执行
- **Unity MCP 接入**
  - 通过 Coplay Unity MCP 获取编译、测试和控制台能力
- **模型分层**
  - 按任务类型做模型路由，并带 provider 降级链
- **本地 scanner 工具**
  - 引用查询、`.meta` 解析、资源统计、ProjectSettings 读取、配置校验
- **工作台 UI**
  - 基于 Streamlit，包含任务卡片、历史恢复和渐进式披露

### 架构

```text
用户请求
  -> Router
     -> Deterministic
        -> 意图解析
        -> 结构化校验修改
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

- Windows PowerShell

```powershell
venv\Scripts\Activate.ps1
```

- macOS / Linux

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

#### 4. 创建本地 `.env`

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

仅使用 DeepSeek 也可以完整启动应用。多 provider 配置可以打开规划与生成任务的完整模型分层路径。

#### 5. 启动应用

```bash
streamlit run app.py
```

### Unity 接入

如果要启用编译、测试和控制台工作流：

1. 在 Unity 项目中安装 `com.coplaydev.unity-mcp`
2. 打开该项目的 Unity Editor
3. 在 GameDev UI 中扫描并初始化该项目

### 配置说明

几个关键开关：

- `ENABLE_MODEL_TIERING=1`
  启用按任务类型分层的模型路由
- `ENABLE_ORCHESTRATOR=1`
  启用系统生成类任务的 orchestrator 路径
- `DEFAULT_VERIFY_MODE=syntax|full`
  控制验证深度

### 参与贡献

欢迎贡献。

适合贡献的方向包括：

- 新 Skill
- Unity 工作流增强
- scanner 能力增强
- 新 worker 集成
- UI 与可用性改进
- 文档优化

如果是较大的想法，先开 issue 或 discussion 会更顺畅。

### 如何贡献 Skill

非常欢迎提交 Skill。

新增 Skill 时建议：

1. 在 `context/skills/common/` 下新增 YAML 元数据文件
2. 新增对应的 Markdown 指令文件
3. 明确写好 `skill_id`、`description`、`route` 和触发文本
4. 指令尽量写成过程化的操作手册
5. 在 PR 描述里说明：
   - 这个 skill 的用途
   - 1 到 2 个示例 prompt
   - 它是否读文件、写文件、是否依赖 Unity

适合社区贡献的 Skill 类型例如：

- 数值平衡调整
- 本地化 QA
- Prefab / 配置一致性检查
- UI 生成工作流
- 构建与发布辅助
- 重构与项目审计类 Skill

### 当前状态

当前实现要点：

- `code_agent` 已实装
- `art_agent` 和 `config_agent` 提供后续 worker 扩展位
- 模型分层、orchestrator 路由和 Unity MCP 接入已经进入当前代码库

### License

MIT
