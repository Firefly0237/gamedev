# 🎮 GameDev

**游戏开发者的 AI 工作台**

在已有游戏项目中，通过自然语言驱动的多 Agent 系统（LangGraph + MCP）自动化日常研发任务——配置修改、代码审查、测试生成、内容管理、质量检查。系统通过 Scanner 分析项目代码结构，通过 Project Schema 理解数据格式，项目代码越多，系统理解越深，输出越准确。

---

## 架构

```
Streamlit 前端
    │
    ▼
Intent Router（意图分类 + Pattern 匹配）
    │
    ├→ 确定性执行器（配置/代码精确修改）
    ├→ 10 条专家 Pipeline（ReAct / 固定流水线）
    └→ 2 个 Supervisor 工作流（多 Agent 协作）
    │
    ▼
MCPClientManager（动态工具发现 + 引擎映射）
    │
    ├── 官方 FileSystem MCP Server
    ├── 官方 Git MCP Server
    ├── 社区 Unity MCP Server (CoplayDev)
    └── 自建 GameDev MCP Server
```

## 功能

### 代码

| 功能 | 模式 | 说明 |
|------|------|------|
| 代码生成 | ReAct | Agent 自主读取项目了解风格后生成 C# 脚本 |
| 代码审查 | ReAct | 多维度审查（性能/规范/反模式/安全） |
| 测试生成 | 固定 | 为指定脚本生成 NUnit 测试 |
| Shader 生成 | 固定 | 根据效果描述生成 ShaderLab/HLSL |
| 性能审计 | ReAct | Agent 自主扫描代码 + 资源 + 配置 |

### 内容

| 功能 | 模式 | 说明 |
|------|------|------|
| 配置生成 | 固定 | 生成 JSON 配置表 + C# 数据类 |
| 关卡设计 | ReAct | 生成关卡配置 + 2D 预览 + 合理性分析 |
| 对话剧情 | 固定 | 生成对话树 JSON + C# 管理器 |
| 本地化 | 固定 | 翻译语言表，自动保护 `{xxx}` 占位符 |
| 资源依赖 | 固定 | 解析 GUID 引用关系 |

### 美术

| 功能 | 模式 | 说明 |
|------|------|------|
| 资产生成 | 固定 | 图片生成（API 可用时）/ 美术需求文档 |

### 工作流

| 功能 | 说明 |
|------|------|
| 需求实现 | Supervisor 自动拆解需求 → 调度多 Agent → evaluate 评估 → 汇总 |
| 提交前检查 | git status → 逐文件审查 → 测试覆盖检查 → 报告 |

## 核心设计

- **Pattern + Project Schema**：8 个通用操作模式（跨项目复用）+ 扫描自动生成的项目数据格式描述，组合后为 LLM 提供精确操作指南
- **确定性修改**：LLM 解析意图输出操作指令，代码精确执行修改，old_value 校验防静默覆盖
- **验证闭环**：语法 → 一致性 → Agent 自审 → 引擎编译，失败自动修复最多 3 轮
- **引擎无关**：Scanner 抽象基类 + 抽象工具名 + MCPClientManager 引擎映射，更换引擎时 Pipeline 代码零修改
- **MCP 动态工具发现**：连接后自动注册工具路由表，不硬编码工具名
- **模型无关**：按任务类型配置不同 LLM（router / generation / review / supervisor）

## 技术栈

LangGraph · MCP · DeepSeek · Pydantic · Streamlit · SQLite · Docker · LangSmith

## 快速开始

```bash
# 克隆
git clone https://github.com/Firefly0237/GameDev.git
cd GameDev

# 环境
python -m venv venv && source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install -g @modelcontextprotocol/server-filesystem @modelcontextprotocol/server-git

# 配置
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 启动
streamlit run app.py
```

## Docker

```bash
docker compose up --build -d
# http://localhost:8501
```

## 项目结构

```
GameDev/
├── app.py                    # 主入口
├── pages/                    # 代码 / 内容 / 美术 / 工作流 / Git
├── config/                   # 全局配置、日志
├── database/                 # SQLite、Checkpoint
├── scanner/                  # 引擎扫描器（base + unity）
├── agents/                   # LLM 封装
├── mcp_tools/                # MCP Server + Client
├── context/                  # Pattern + Project Schema + Loader
├── prompts/                  # System Prompt
├── schemas/                  # Pydantic 输出模型
└── graphs/                   # LangGraph Pipeline + Supervisor
```

## License

MIT
