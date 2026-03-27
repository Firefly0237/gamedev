# GameDev

GameDev 是一个面向游戏研发流程的 AI 工作台，用于将自然语言需求路由到代码生成、配置处理、内容生产、资源分析、工作流编排和 Git 检查等模块。项目围绕 Intent Router、Pipeline、Supervisor、MCP 工具层、项目扫描器和 Pattern + Project Schema 上下文注入机制构建。

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Feature Status](#feature-status)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Module Breakdown](#module-breakdown)
- [License](#license)

## Overview

GameDev 面向以下场景：

- 从聊天入口接收游戏研发需求并自动路由
- 基于项目扫描结果生成更贴近当前项目的数据上下文
- 对 JSON 配置和代码文本执行确定性修改
- 将代码、内容、美术、工作流和 Git 能力统一到同一工作台
- 通过抽象工具名和引擎映射降低对具体引擎的耦合

当前实现已经覆盖应用入口、页面结构、基础数据层、Pipeline 注册机制、Router、Unity 扫描器、自建 MCP 工具和部分可执行 Pipeline。尚未完成的能力会在功能状态中明确标注。

## Architecture

系统结构分为五层：

1. `Streamlit UI`
   聊天入口、手动页面、Git 面板、执行结果展示。

2. `Router / Pipelines / Supervisors`
   Router 负责意图识别与路由；Pipelines 负责单项任务；Supervisors 负责复杂需求拆解与编排。

3. `Context Layer`
   由 `Pattern`、`Project Schema` 和扫描器输出共同构成运行时上下文。

4. `Tool Layer`
   通过 `MCPClientManager` 管理文件、Git、Unity 和 GameDev 自建工具。

5. `Persistence Layer`
   通过 SQLite 保存执行历史、项目上下文缓存和 Checkpoint。

核心设计点：

- `Intent Router`：负责意图分类、Pattern 匹配和目标 Pipeline 决策
- `Pattern + Project Schema`：将通用操作规则和项目真实结构分离
- `Deterministic Editing`：将意图理解与实际文件写入分离
- `Engine Abstraction`：通过扫描器抽象、工具别名和引擎映射降低引擎绑定

## Feature Status

### Implemented

- Streamlit 主界面与多页面导航
- 聊天入口自动路由
- Pipeline 注册中心和统一执行入口
- SQLite 执行历史记录
- 项目上下文缓存
- LangGraph Checkpoint 接口封装
- Unity 项目基础扫描
- JSON Project Schema 自动生成
- Pattern 加载与上下文组装
- 自建 GameDev MCP 工具
- 确定性配置修改
- 确定性代码修改
- 代码审查启发式规则
- 资源体积分布扫描
- Git 只读面板
- Docker 启动配置

### In Progress / Pending

- LLM Router 的真实分类逻辑增强
- 代码生成 Pipeline 的真实产物落盘
- 测试生成 Pipeline 的 NUnit 输出
- Shader 生成 Pipeline 的实际内容生成
- 配置生成 Pipeline 的 JSON 与 C# 文件生成
- 关卡设计 Pipeline 的结构化产物生成
- 对话剧情 Pipeline 的对话树生成
- 本地化 Pipeline 的翻译执行
- Supervisor 的自动执行、依赖调度和 evaluate
- 验证闭环中的自动修复流程
- 真实 MCP Server 接入
- Unity 编译、场景、截图联动
- LangSmith 观测接入
- 自动化测试
- 完整部署与生产化运行配置

## Requirements

推荐运行环境：

- Python 3.12+
- Git
- Node.js 18+ `（接入官方 FileSystem / Git MCP Server 时需要）`
- Unity `（接入 Unity MCP 和编译验证时需要，可选）`
- 可用的 LLM API 服务 `（启用真实模型时需要，可选）`

默认配置支持 `mock` LLM 模式，可在未接入真实模型时运行 UI、扫描器和基础 Pipeline。

## Quick Start

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create environment file

Windows PowerShell:

```powershell
copy .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

### 4. Start the application

```bash
streamlit run app.py
```

Default local address:

```text
http://localhost:8501
```

### 5. Create a local sample project (optional)

```bash
python create_test_project.py
```

### 6. Run environment diagnostics (optional)

```bash
python test_env.py
```

## Configuration

主要环境变量：

- `DEFAULT_PROJECT_ROOT`：默认打开的项目路径
- `DATABASE_PATH`：任务历史数据库路径
- `CHECKPOINT_DB_PATH`：Checkpoint 数据库路径
- `LLM_PROVIDER`：`mock` 或兼容 OpenAI 的服务模式
- `LLM_BASE_URL`：模型服务地址
- `LLM_API_KEY`：模型服务密钥
- `LLM_ROUTER_MODEL`：Router 模型
- `LLM_GENERATION_MODEL`：生成类任务模型
- `LLM_REVIEW_MODEL`：审查类任务模型
- `LLM_SUPERVISOR_MODEL`：Supervisor 模型

示例：

```env
APP_NAME=GameDev
DEFAULT_PROJECT_ROOT=
LLM_PROVIDER=mock
LLM_BASE_URL=
LLM_API_KEY=
LLM_ROUTER_MODEL=deepseek-chat
LLM_GENERATION_MODEL=deepseek-chat
LLM_REVIEW_MODEL=deepseek-chat
LLM_SUPERVISOR_MODEL=deepseek-reasoner
```

## Usage

应用启动后，主要工作方式如下：

1. 在侧边栏设置项目路径并执行扫描
2. 在聊天入口直接输入研发需求，由 Router 自动选择目标 Pipeline
3. 在 `pages/` 对应的手动页面中单独执行某一模块
4. 在结果区域查看执行链路、输出数据和产物预览
5. 在 Git 面板查看仓库状态和最近提交

典型输入示例：

- `做一个背包系统`
- `审查 Assets/Scripts/PlayerController.cs`
- `分析 Assets/Prefabs/Player.prefab.meta 的引用关系`

## Project Structure

```text
GameDev/
├── app.py
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── config/
├── database/
├── scanner/
├── agents/
├── mcp_tools/
├── context/
├── prompts/
├── schemas/
├── graphs/
├── pages/
├── logs/
├── output/
├── create_test_project.py
└── test_env.py
```

## Module Breakdown

### Application

- `app.py`：Streamlit 主入口，负责聊天入口、项目状态和执行历史展示
- `pages/`：手动模式页面，每个页面绑定一个功能模块

### Core Runtime

- `graphs/base.py`：Pipeline 注册、服务容器、状态初始化、上下文加载和统一执行入口
- `graphs/router.py`：输入路由
- `graphs/deterministic.py`：确定性配置 / 代码修改执行器
- `graphs/safety.py`：备份、diff、Git auto-save 等安全辅助逻辑
- `graphs/supervisor_*.py`：Supervisor 工作流

### Context and Prompting

- `context/patterns/`：通用 Pattern 定义
- `context/project_schemas/`：扫描器自动生成的项目 Schema
- `context/loader.py`：Pattern 与 Schema 加载器
- `prompts/`：各 Pipeline 和 Router 的 Prompt 模板

### Tooling and Integration

- `scanner/`：扫描器抽象与 Unity 扫描器实现
- `mcp_tools/mcp_client.py`：MCP Client Manager
- `mcp_tools/mcp_server_gamedev.py`：自建 GameDev MCP 工具集
- `agents/llm.py`：LLM 调用封装

### Persistence

- `database/db.py`：执行历史、项目上下文和反馈表
- `database/checkpoint.py`：LangGraph Checkpoint 封装

### Schemas

- `schemas/outputs.py`：Pydantic 输出模型定义

## License

当前仓库未提供 `LICENSE` 文件。

这意味着仓库目前没有明确授予第三方复制、修改、分发和商用的许可；在法律意义上，默认应视为保留所有权利。若该项目需要以开源方式发布，应补充正式的 `LICENSE` 文件并在此处声明对应协议名称。
