from config.logger import logger
from graphs.local_tools import LOCAL_TOOL_NAMES
from mcp_tools.mcp_client import get_all_mcp_tools
from mcp_tools.unity_coplay import is_engine_tool_available


READ_ONLY_TOOLS = {
    "read_file",
    "list_directory",
    "search_files",
    "scan_asset_sizes",
    "scan_texture_info",
    "read_project_settings",
    "parse_meta_file",
    "find_references",
    "validate_all_configs",
    "engine_compile",
    "engine_run_tests",
    "engine_get_logs",
}

WRITE_ENABLED_SKILLS = {
    "generate_test",
    "generate_system",
    "generate_shader",
    "generate_ui",
    "generate_editor_tool",
    "translate",
    "code_agent",
    "config_agent",
    "art_agent",
}

_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取项目文件内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入文件（自动备份和验证）",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出目录内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "目录路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "搜索包含关键字的文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}},
                "required": ["path", "pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_asset_sizes",
            "description": "统计资源文件大小",
            "parameters": {"type": "object", "properties": {"relative_path": {"type": "string", "default": "Assets"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_texture_info",
            "description": "扫描纹理文件信息",
            "parameters": {"type": "object", "properties": {"relative_path": {"type": "string", "default": "Assets"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_project_settings",
            "description": "读取 ProjectSettings 配置文件",
            "parameters": {
                "type": "object",
                "properties": {"settings_file": {"type": "string"}},
                "required": ["settings_file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_meta_file",
            "description": "解析 .meta 获取 GUID",
            "parameters": {
                "type": "object",
                "properties": {"relative_path": {"type": "string"}},
                "required": ["relative_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_references",
            "description": "搜索 GUID 引用",
            "parameters": {
                "type": "object",
                "properties": {"guid": {"type": "string"}},
                "required": ["guid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_all_configs",
            "description": "校验项目所有配置文件，返回问题列表",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "engine_compile",
            "description": "调用引擎编译当前项目，返回错误和警告列表。需要 Unity Server 连接。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "engine_run_tests",
            "description": "运行项目的单元测试，返回 passed/failed 统计和失败详情",
            "parameters": {
                "type": "object",
                "properties": {"test_filter": {"type": "string", "description": "可选的测试名过滤器"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "engine_get_logs",
            "description": "读取最近的引擎日志（用于查看编译/运行历史输出）",
            "parameters": {"type": "object", "properties": {"lines": {"type": "integer", "default": 100}}},
        },
    },
]


def build_tool_definitions(skill_id: str) -> list[dict]:
    registered = set(get_all_mcp_tools())
    available_names = registered | LOCAL_TOOL_NAMES
    allowed_tools = set(READ_ONLY_TOOLS)
    if skill_id in WRITE_ENABLED_SKILLS:
        allowed_tools.add("write_file")

    available = []
    for tool in _TOOL_DEFINITIONS:
        name = tool["function"]["name"]
        if name not in allowed_tools:
            continue
        if name in LOCAL_TOOL_NAMES:
            available.append(tool)
            continue
        if name in registered:
            available.append(tool)
            continue
        if name.startswith("engine_") and is_engine_tool_available(name, available_names):
            available.append(tool)

    logger.debug(f"可用工具: skill={skill_id}, count={len(available)}")
    return available
