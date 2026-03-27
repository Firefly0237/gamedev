# GameDev — 完整开发教程

## 引擎无关的多 Agent 游戏研发平台

---

# 一、项目定位

GameDev 是一个 AI 驱动的游戏研发工作台。用户用自然语言描述需求，系统自动识别意图、调度专家 Agent 完成从策划配置到代码实现到质量检查的全流程。

核心特征：
- **多 Agent Supervisor 编排**：复杂需求自动拆解为子任务，多个专家 Agent 按依赖关系协作
- **引擎无关**：Scanner 抽象基类 + Agent 使用抽象工具名 + MCPClientManager 引擎映射层，三层架构保证更换引擎时 Pipeline 代码零修改
- **Pattern + Project Schema 知识注入**：8 个通用操作模式（跨项目复用） + 项目扫描自动生成的数据格式描述（项目特有），组合后为 LLM 提供精确的操作指南
- **确定性修改**：精确的数值/代码修改由代码执行而非 LLM 生成
- **验证闭环**：生成的代码经过多层验证，失败自动修复

---

# 二、系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                   GameDev 前端（Streamlit）                    │
│  聊天入口（主界面，Intent Router 自动路由 + Pattern 匹配）     │
│  手动模式（侧边导航：代码 / 内容 / 美术 / 工作流 / Git）      │
│  执行链路实时展示                                              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                  GameDev Agent 后端（Python）                  │
│                                                              │
│  Intent Router → 意图分类 + Pattern 匹配 → 路由               │
│    ├→ 确定性执行器（数值/代码精确修改，不经过 LLM）            │
│    ├→ 单任务 Pipeline（10条，ReAct 或固定流水线）              │
│    └→ Supervisor 工作流（2条，多 Agent 编排）                  │
│                                                              │
│  共享组件：                                                   │
│    Pattern + Project Schema（两层知识注入）                    │
│    验证闭环 · 安全层 · Project Journal · Checkpoint           │
│    执行链路记录 · 上下文构建器 · 模型选择器                    │
│                                                              │
│  MCPClientManager（多 Server 连接 + 动态工具发现 + 引擎映射）  │
└─────────────────────────────┬────────────────────────────────┘
                              │ MCP (JSON-RPC over stdio)
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────────┐ ┌───────────┐ ┌──────────────────┐
      │ 官方 FS + Git │ │ 社区 Unity │ │ 自建 GameDev     │
      │ MCP Server   │ │ MCP Server│ │ MCP Server       │
      │ (Node.js)    │ │(CoplayDev)│ │ (Python, 5工具)  │
      └──────────────┘ └───────────┘ └──────────────────┘
```

---

# 三、技术栈与选型

| 层次 | 技术 | 选型理由 |
|------|------|---------|
| Agent 编排 | LangGraph StateGraph | 原生支持 ReAct 循环、Supervisor 模式、Checkpoint 持久化 |
| 工具协议 | MCP (JSON-RPC over stdio) | Agent 工具调用的行业标准，工具标准化后可跨系统复用 |
| 基础文件/Git 操作 | MCP 官方 Server (Node.js) | 官方维护的参考实现，成熟可靠 |
| Unity 引擎操作 | CoplayDev/unity-mcp | 社区最成熟方案（MIT，ACM 论文），提供 execute/compile/screenshot |
| 游戏开发专用工具 | 自建 GameDev MCP Server | 官方和社区未覆盖：.meta 解析、GUID 引用搜索、资源统计。独立 Server 保证架构一致性，未来可被 Cursor/Claude Desktop 等其他 MCP Client 直接连接复用 |
| LLM | 模型无关（默认 DeepSeek） | 按任务类型配置不同模型，不绑定供应商 |
| 输出控制 | Pydantic v2 | 强制校验 LLM 输出格式 |
| 状态持久化 | LangGraph SqliteSaver | 每个 Node 自动保存 State 快照 |
| 数据库 | SQLite | 轻量，单文件，无需额外服务 |
| 前端 | Streamlit 多页面 | Python 全栈，快速落地 |
| 可观测性 | LangSmith | Pipeline 执行全链路可视化 |
| 部署 | Docker + Docker Compose | 容器化，一键启动 |

---

# 四、功能清单

## 三大功能模块 + 编排层 + 辅助层

### 代码模块（产出 .cs 文件或代码分析报告）

| # | 名称 | 推理模式 | 输入 → 输出 |
|---|------|---------|------------|
| 1 | 代码生成 | ReAct | 自然语言需求 → .cs 文件 |
| 2 | 代码审查 | ReAct | .cs 文件 → 审查报告 |
| 3 | 代码修改 | 确定性 | 修改指令 → 精确字符串替换 |
| 4 | 测试生成 | 固定 | .cs 文件 → NUnit 测试 |
| 5 | Shader 生成 | 固定 | 效果描述 → .shader 文件 |
| 6 | 性能审计 | ReAct | 目录范围 → 性能报告 |

### 内容模块（产出 JSON 数据文件或分析报告）

| # | 名称 | 推理模式 | 输入 → 输出 |
|---|------|---------|------------|
| 7 | 配置生成 | 固定 | 数据需求 → JSON + C# 数据类 |
| 8 | 配置修改 | 确定性 | 修改指令 → JSON 字段精确修改 |
| 9 | 关卡设计 | ReAct | 关卡描述 → JSON + 预览 + 分析 |
| 10 | 对话剧情 | 固定 | 场景描述 → 对话树 JSON + C# |
| 11 | 本地化 | 固定 | 语言表 + 目标语言 → 翻译后 JSON |
| 12 | 资源依赖 | 固定 | Prefab/脚本 → 依赖分析报告 |

### 美术模块（产出图片资源或美术需求文档）

| # | 名称 | 推理模式 | 输入 → 输出 |
|---|------|---------|------------|
| 13 | 资产生成 | 固定 | 描述 → 图片（API 可用时）/ 美术需求文档 |
| — | 纹理生成 | 预留接口 | 未来迭代 |
| — | 模型生成 | 预留接口 | 未来迭代 |
| — | 动画生成 | 预留接口 | 未来迭代 |

### 编排层（调度功能模块协作）

| # | 名称 | 功能 |
|---|------|------|
| 14 | Intent Router | 自然语言 → 意图分类 + Pattern 匹配 → 路由 |
| 15 | 需求实现 | Supervisor：拆解 → 调度多 Agent → evaluate → 汇总 |
| 16 | 提交前检查 | Supervisor：git status → 审查 → 测试覆盖 → 报告 |

### 辅助层

| # | 名称 | 功能 |
|---|------|------|
| 17 | Git 面板 | status / diff / log（读取）+ add / commit（需 UI 确认） |

---

# 五、核心设计机制

## 5.1 Intent Router

用户输入任何内容，Router 用一次轻量 LLM 调用分类意图，同时匹配 Pattern：

```
"把火焰剑攻击力改到150"     → config_modify  + Pattern: modify_config
"生成一个背包系统"           → code_generate  + Pattern: generate_system
"审查 PlayerController"      → code_review    + Pattern: review_code
"加一种法杖武器类型有蓝耗"   → complex_requirement + Pattern: generate_system
"继续铁匠的对话"             → dialogue_generate + Pattern: continue_content
```

Pattern 匹配只在 Router 做一次，结果通过 PipelineState 的 `matched_pattern` 字段传递给下游 Pipeline，不重复匹配。

## 5.2 Pattern + Project Schema（两层知识注入）

**设计思路**：Prompt 不应该包含领域知识（"damage 范围 10-9999"这种），因为不同项目的数据不同。Prompt 也不应该包含操作步骤（"先生成数据类再生成逻辑"这种），因为这些步骤对任何项目都一样。

知识注入分两层：

```
Pattern（预置，跨项目通用，~8 个）：
  描述一类抽象操作的通用流程、约束和输出格式
  - modify_config: 修改配置的通用步骤和安全约束
  - modify_code: 精确修改代码的通用步骤
  - generate_system: 实现新系统的标准流程（数据类→配置→逻辑→测试）
  - generate_content: 生成内容型数据（配置表/对话/Shader）的通用规则
  - continue_content: 续写已有内容的通用规则（不改已有、ID 递增）
  - review_code: 代码审查的通用检查维度
  - analyze_project: 项目分析的通用维度（代码/资源/配置）
  - translate_content: 本地化翻译的通用规则（占位符保护）

Project Schema（扫描自动生成，项目特有）：
  描述该项目每个配置文件的真实字段、示例记录和定位字段
  扫描器分析完项目后，自动读取每个 JSON 配置文件，
  提取第一条记录作为格式示例，生成 Schema 文件。
```

运行时组合——以"把火焰剑攻击力改到 150"为例：

```
Pattern "modify_config"（通用）：
  "读取文件 → 用定位字段找到记录 → 校验旧值 → 修改 → 写回"
  "必须指定 old_value 用于安全校验"

Project Schema "WeaponConfig.json"（该项目特有）：
  字段: id, name, weaponType, damage, attackSpeed, critRate, rarity, price
  示例: {"id":1001, "name":"铁剑", "damage":50, ...}
  定位字段: name

组合后 LLM 看到：通用流程 + 该项目的真实数据格式 → 精确输出操作指令
```

**泛用性保证**：不管用户做背包系统、元素反应效果、天气系统还是成就系统，都走同一个 `generate_system` Pattern。不同项目的不同数据格式由 Project Schema 自动适配。不需要为每种系统或每个项目手写 Skill。

## 5.3 确定性修改

LLM 负责理解"用户想干什么"，代码负责"精确执行修改"。

```
用户: "把火焰剑攻击力改到150"

Step 1 — LLM 解析意图（有 Pattern + Schema 指导）：
  输出: { file: "WeaponConfig.json", match: "火焰剑",
          field: "damage", old: 100, new: 150 }

Step 2 — 代码精确执行：
  读取 JSON → 定位记录 → 校验 old_value → 修改 → 写回
  LLM 不接触文件内容

Step 3 — 安全保障：
  Git auto-save → diff 预览 → 用户确认
```

代码文件修改同理：LLM 输出 search_pattern 和 replace_with，代码做精确字符串替换。

## 5.4 验证闭环

```
generate → validate_basic（括号/using 声明）
         → validate_consistency（类名冲突、命名空间）
         → agent_self_review（另一个 LLM 轻量审查）
         → write_file
         → engine_compile（可选，引擎可用时）
         → 通过 → format_output
         → 失败 → fix → validate（最多 3 轮，retry_count 在 State 中传递）
```

## 5.5 Supervisor 多 Agent 协作

```
用户: "给游戏加一种法杖武器类型，有蓝耗和施法距离"

plan_tasks   → LLM 参考 Pattern(generate_system) 拆解为子任务
execute_next → 按依赖顺序调度专家 Agent，每个 Agent 带着 Pattern + Schema 执行
               结果写入 Project Journal，后续 Agent 读取 Journal
evaluate     → 检查子任务结果，不通过则调整计划
summarize    → 汇总所有变更
```

## 5.6 安全机制

| 机制 | 说明 |
|------|------|
| Git auto-save | 修改文件前自动 commit 当前状态 |
| .bak 备份 | 修改前生成备份文件 |
| diff 预览 | UI 展示修改内容供用户确认 |
| old_value 校验 | 确定性修改时验证原值 |
| 文件冲突检测 | 新文件检查同名是否存在 |
| Journal 文件锁 | Supervisor 中防多 Agent 同时改同一文件 |
| 占位符保护 | 本地化翻译时保护 {xxx} 不被翻译 |
| Git 写操作确认 | add/commit 需用户点击确认 |
| Supervisor 计划审阅 | 任务计划执行前展示给用户 |
| 文件只增不删 | Agent 可创建和修改文件，不可删除 |

## 5.7 记忆系统

| 层次 | 存储 | 生命周期 | 用途 |
|------|------|---------|------|
| Node 间通信 | PipelineState（内存） | 单次执行 | Node 之间传递数据 |
| Agent 间协作 | Project Journal（State 内） | 单次工作流 | Supervisor 下多 Agent 共享变更记录 |
| 执行历史 | SQLite task_logs | 永久 | 每次执行的输入/输出/状态/token |
| 项目认知 | SQLite project_context | 手动刷新前 | 缓存扫描器分析结果 |
| State 快照 | Checkpoint (SQLite) | 永久 | 中断恢复、执行回溯 |
| RL 数据收集 | SQLite pipeline_feedback | 永久 | 成功/失败 case 供未来优化 |

## 5.8 上下文工程

扫描器通过正则提取代码结构（类名、基类、公共字段/方法签名），实现 80:1 压缩比。

每次 LLM 调用注入分层上下文：

```
L1 (~200 token): 项目概览（引擎版本、脚本总数、场景列表）
L2 (~300 token): 目录树（前 20 行）
L3 (~500 token): 脚本骨架列表（类名 + 基类，≤30 个）
L4 (~1-3K token, 按需): 参考文件内容（截断 4000 字符）
L5 (~300-800 token): Pattern 操作指南 + Project Schema 数据格式
L6 (~200 token): System Prompt（角色定义 + 输出格式）
L7 (Supervisor 专用): Project Journal

总计: ~3000-5000 token/次
```

L5 是关键增量——Pattern 提供"怎么做"，Project Schema 提供"这个项目长什么样"，两者组合后 LLM 从"凭通用知识猜测"变为"按项目实际格式执行"。

## 5.9 引擎无关架构

三层抽象保证更换引擎时 Pipeline 代码零修改：

```
Layer 1 — Scanner 抽象基类：
  scanner/base.py      → BaseScanner + ProjectContext（通用字段名）
  scanner/unity_scanner.py → UnityScanner(BaseScanner)
  （未来: scanner/ue_scanner.py → UEScanner(BaseScanner)）

Layer 2 — Agent 使用抽象工具名：
  Pipeline 调用 engine_compile / engine_execute / engine_scene
  而非 unity_compile / ue_build

Layer 3 — MCPClientManager 引擎映射：
  检测连接的 Engine Server 类型
  将抽象工具名翻译为该引擎的实际工具名
  {"engine_compile": "unity_compile"} 或 {"engine_compile": "ue_build"}
```

当前 Unity 为首个完整适配。UE/Godot 通过实现对应的 Scanner + 接入对应的 MCP Server 适配。

## 5.10 MCP 动态工具发现

MCPClientManager 连接各 Server 后，通过 `list_tools()` 获取实际的工具名和参数，自动构建路由注册表。Pipeline 调用工具时，Manager 从注册表查找该工具在哪个 Server 上，自动路由。不硬编码工具名到 Server 的映射。

```python
# 连接后自动注册
self._tool_registry = {}  # {"read_file": "fs", "git_status": "git", ...}
for name, conn in self._connections.items():
    for tool_name in conn.tool_names:
        self._tool_registry[tool_name] = name

# 调用时自动路由
def call_tool(self, tool_name, arguments):
    target = self._tool_registry.get(tool_name)
    return self._connections[target].call_sync(tool_name, arguments)
```

## 5.11 模型无关设计

按任务类型配置不同 LLM：

```python
LLM_ROUTER_MODEL     = "deepseek-chat"       # 意图识别：轻量便宜
LLM_GENERATION_MODEL = "deepseek-chat"       # 代码/内容生成：主力
LLM_REVIEW_MODEL     = "deepseek-chat"       # 审查：主力
LLM_SUPERVISOR_MODEL = "deepseek-reasoner"   # Supervisor：推理增强
```

## 5.12 执行链路记录

```
📋 执行链路：
1. [Router] config_modify (0.97) + Pattern: modify_config
2. [Schema] 匹配 WeaponConfig.json (字段: id,name,damage,...)
3. [MCP:read_file] WeaponConfig.json → fs Server
4. [Validate] 火焰剑.damage = 100 ✓
5. [Execute] damage: 100 → 150（确定性修改）
6. [MCP:write_file] WeaponConfig.json → fs Server
7. [Git] auto-save ✅
```

---

# 六、MCP 工具清单

## 官方 FileSystem Server (Node.js, MIT)

read_file · write_file · list_directory · search_files · move_file · get_file_info

## 官方 Git Server (Node.js, MIT)

git_status · git_diff_unified · git_log · git_show · git_add · git_commit

## 社区 Unity MCP Server (CoplayDev/unity-mcp, MIT, ACM 论文)

unity_execute · unity_scene_hierarchy · unity_screenshot · unity_compile

## 自建 GameDev MCP Server (Python, 5 个工具)

| 工具 | 说明 |
|------|------|
| parse_meta_file | 解析 .meta 获取 GUID 和导入设置 |
| find_references | 搜索项目中引用指定 GUID 的文件 |
| scan_asset_sizes | 统计目录下各类资源文件大小分布 |
| scan_texture_info | 扫描纹理尺寸/格式信息 |
| read_project_settings | 读取 ProjectSettings 配置 |

---

# 七、前端布局

```
┌──────────────┬────────────────────────────────────┐
│  🎮 GameDev  │                                    │
│              │  💬 聊天入口（默认主界面）           │
│  📁 项目      │                                    │
│  [打开项目]  │  用户: 做一个背包系统               │
│  23脚本 3场景│  GameDev: 🤖 正在工作...           │
│  MCP 🟢🟢🟢  │  ✅ 已生成 4 个文件                 │
│              │  [查看链路] [查看代码]              │
│  ─────────── │                                    │
│  💻 代码      │  用户: 把火焰剑攻击力改到150        │
│   代码生成   │  GameDev:                          │
│   代码审查   │  damage: 100 → 150                 │
│   测试生成   │  [确认] [取消]                      │
│   Shader    │                                    │
│   性能审计   │                                    │
│  📋 内容      │                                    │
│   配置生成   │                                    │
│   关卡设计   │                                    │
│   对话剧情   │                                    │
│   本地化     │                                    │
│   资源分析   │                                    │
│  🎨 美术      │                                    │
│   资产生成   │                                    │
│  🔄 工作流    │                                    │
│   需求实现   │                                    │
│   提交检查   │                                    │
│  📜 Git       │                                    │
│  ─────────── │                                    │
│  📋 执行历史  │                                    │
└──────────────┴────────────────────────────────────┘
```

---

# 八、错误处理

| 场景 | 处理方式 |
|------|---------|
| LLM 调用失败 | 指数退避重试（1s → 2s → 4s，最多 3 次） |
| LLM 输出格式错误 | Pydantic 校验失败 → 带错误信息让 LLM 重新生成 |
| MCP Server 崩溃 | 动态注册表标记该 Server 离线，UI 显示 🔴 |
| 确定性修改 old_value 不匹配 | 拒绝执行，提示文件可能已被修改 |
| 引擎编译失败 | 提取错误信息 → 反馈给 fix Agent |
| 引擎不可用 | 自动跳过编译验证，不阻断流程 |
| Git 写操作 | UI 确认弹窗，不点确认不执行 |
| 验证闭环失败 | retry_count 在 PipelineState 中计数，最多 3 轮 |

---

# 九、项目文件结构

```
GameDev/
├── .env, .env.example, .gitignore
├── requirements.txt
├── Dockerfile, docker-compose.yml
├── README.md
├── app.py                               # 主入口 + 聊天 + 导航
│
├── pages/                               # 手动模式页面
│   ├── _common.py                       # 通用 Pipeline/Supervisor 执行函数
│   ├── code_gen.py                      # 代码模块
│   ├── code_review.py
│   ├── code_test_gen.py
│   ├── code_shader_gen.py
│   ├── code_performance.py
│   ├── content_config_gen.py            # 内容模块
│   ├── content_level_design.py
│   ├── content_dialogue.py
│   ├── content_localization.py
│   ├── content_dependency.py
│   ├── art_asset_gen.py                 # 美术模块
│   ├── workflow_requirement.py          # 工作流
│   ├── workflow_precommit.py
│   └── git_panel.py                     # 辅助
│
├── config/
│   ├── settings.py                      # 全局配置（含多模型配置 + 引擎映射）
│   └── logger.py
│
├── database/
│   ├── db.py                            # SQLite（3 张表）
│   └── checkpoint.py                    # LangGraph Checkpoint
│
├── scanner/
│   ├── base.py                          # BaseScanner 抽象基类 + ProjectContext
│   └── unity_scanner.py                 # Unity 实现（继承 BaseScanner）
│
├── agents/
│   └── llm.py                           # LLM 封装（模型无关，按任务选模型）
│
├── mcp_tools/
│   ├── mcp_server_gamedev.py            # 自建 GameDev MCP Server（5 工具）
│   └── mcp_client.py                    # MCPClientManager（动态发现 + 引擎映射）
│
├── context/                             # 两层知识注入
│   ├── patterns/                        # 预置 Pattern（~8 个 JSON，跨项目通用）
│   │   ├── modify_config.json
│   │   ├── modify_code.json
│   │   ├── generate_system.json
│   │   ├── generate_content.json
│   │   ├── continue_content.json
│   │   ├── review_code.json
│   │   ├── analyze_project.json
│   │   └── translate_content.json
│   ├── project_schemas/                 # 扫描自动生成（项目特有）
│   │   └── (运行时生成)
│   └── loader.py                        # Pattern 加载 + Schema 匹配 + 上下文组合
│
├── prompts/                             # 13 个 Prompt（瘦身：角色 + 工具策略 + 输出格式）
│   ├── router.py
│   ├── code_review.py, code_gen.py, test_gen.py, shader_gen.py
│   ├── config_gen.py, level_design.py, dialogue.py, localization.py
│   ├── art_gen.py, performance.py, dependency.py
│   └── supervisor.py
│
├── schemas/
│   └── outputs.py                       # 所有 Pydantic 输出模型
│
├── graphs/
│   ├── base.py                          # PipelineState + MCP 工具包装 + 上下文构建
│   ├── router.py                        # Intent Router（意图分类 + Pattern 匹配）
│   ├── deterministic.py                 # 确定性修改执行器
│   ├── safety.py                        # 安全层
│   ├── code_review.py, code_gen.py      # ReAct
│   ├── test_gen.py, shader_gen.py       # 固定
│   ├── config_gen.py, level_design.py   # 固定 / ReAct
│   ├── dialogue.py, localization.py     # 固定
│   ├── art_gen.py, performance.py       # 固定 / ReAct
│   ├── dependency.py                    # 固定
│   ├── supervisor_base.py               # SupervisorState
│   ├── supervisor_requirement.py        # Supervisor + evaluate
│   └── supervisor_precommit.py          # Supervisor
│
├── logs/, output/
├── test_env.py, create_test_project.py
```

约 55 个源文件，预估 5500-6500 行代码。

---

# 十、开发计划

| 阶段 | 模块 | 内容 | 预估(AI辅助) |
|------|------|------|-------------|
| 0 | 环境准备 | Python/Node.js/Docker/API Key/MCP Server 安装 | 0.5天 |
| 1 | 基础设施 | settings + logger + db + checkpoint | 0.5天 |
| 2 | 扫描器 | BaseScanner + UnityScanner + auto_generate_project_schemas + 测试项目 | 0.5天 |
| 3 | MCP 层 | GameDev Server + MCPClientManager（动态发现 + 引擎映射）+ LLM 封装 | 1.5天 |
| 4 | Pattern + Prompt | 8 个 Pattern JSON + loader.py + 13 个瘦身 Prompt | 1.5天 |
| 5 | Schema | 所有 Pydantic 模型 | 0.5天 |
| 6 | Pipeline | base + router + deterministic + safety + 10 条 Pipeline | 3天 |
| 7 | Supervisor | 2 个工作流 + evaluate + Journal | 2天 |
| 8 | 前端 | app.py + _common.py + 15 个页面（代码/内容/美术/工作流/Git） | 2天 |
| 9 | 测试部署 | Chop Chop 测试 + Docker + 文档 | 1天 |
| **合计** | | | **约13天** |

---

# 十一、竞品对比

| 维度 | Bezi (Unity) | Aura (UE) | GameDev |
|------|-------------|-----------|---------|
| 多Agent协作 | 单Agent | 多Agent | Supervisor + Journal + evaluate |
| 策划工具 | 无 | 无 | 配置/关卡/对话/本地化 |
| 确定性修改 | LLM改代码 | LLM改代码 | 意图解析 + 代码执行分离 |
| 知识注入 | Pages 系统 | 无 | Pattern + Project Schema 自动适配 |
| 执行链路 | 黑盒 | 黑盒 | 完整链路记录 + LangSmith |
| 引擎绑定 | Unity | UE | 引擎无关（三层抽象） |
| 验证闭环 | 无 | 自我修正 | 4层验证 + 引擎编译 |
| Git集成 | 无 | 无 | 完整 |

---

# 十二、能力体现

| 能力 | 具体体现 |
|------|---------|
| LangGraph | 10 条 StateGraph + 2 个 Supervisor + ReAct + 条件边 + ToolNode + evaluate |
| 上下文工程 | 7 层分层注入 + Pattern/Schema 两层知识注入 + 80:1 C# 压缩 + token 预算 |
| MCP | 4 个 Server + 动态工具发现 + 引擎映射层 + 引擎无关路由 |
| Pattern + Schema | 8 个通用 Pattern + 自动生成 Project Schema + 运行时组合 |
| 记忆处理 | 6 层记忆（State / Journal / task_logs / project_context / Checkpoint / feedback） |
| 安全工程 | 确定性执行 + 验证闭环 + Git auto-save + 10 项安全机制 |
| Agentic RL（预留） | 验证闭环 = Action-Observation-Feedback + 数据收集 + DPO 方案设计 |

---

# 十三、工作内容总结

1. 设计引擎无关的多 Agent 游戏研发平台架构，通过 Scanner 抽象基类 + 抽象工具名 + MCPClientManager 引擎映射三层抽象实现引擎解耦
2. 基于 LangGraph 实现 10 条专家 Pipeline + 2 个 Supervisor 协作工作流 + Intent Router 统一入口
3. 4 条 Pipeline 采用 ReAct 推理（Agent 自主调用 MCP 工具探索项目），6 条采用固定流水线
4. 设计 Pattern + Project Schema 两层知识注入：8 个通用操作模式跨项目复用，扫描器自动为每个配置文件生成 Schema，运行时组合为 LLM 提供精确操作指南
5. 实现 Supervisor 多 Agent 编排：需求拆解、依赖调度、Project Journal 信息传递、evaluate 反馈评估
6. 构建 MCP 多 Server 架构，连接后动态工具发现替代硬编码路由，自建 5 个游戏开发专用分析工具
7. 设计确定性修改机制：LLM 解析意图输出操作指令，代码精确执行修改，old_value 校验防静默覆盖
8. 实现 4 层验证闭环（语法 → 一致性 → Agent 自审 → 引擎编译），失败自动修复最多 3 轮
9. 开发代码静态分析器，正则提取结构实现 80:1 上下文压缩比
10. 设计 7 层上下文分层注入策略（概览/目录树/骨架/参考文件/Pattern+Schema/Prompt/Journal）
11. 实现 10 项安全机制（Git auto-save、diff 预览、文件冲突检测、占位符保护、Journal 文件锁等）
12. 模型无关设计，按任务类型配置不同 LLM
13. 生产级工程：Checkpoint 持久化、指数退避重试、LangSmith 可观测、Docker 部署
