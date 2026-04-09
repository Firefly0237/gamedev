# 🎮 GameDev

AI-powered game development workbench. Natural language -> automated code review,
config modification, test generation, and more.

## Features

- **Agent Loop + Skill**: One agent loop handles all tasks, guided by Skill .md files
- **Deterministic Modification**: Config/code changes via LLM intent parsing + Pydantic validation + code execution
- **MCP Multi-Server**: Dynamic tool discovery across FileSystem, Git, and custom game dev tools
- **Progressive Disclosure UI**: Chat-first interface, smart recommendations after scan
- **Engine Agnostic**: Abstract scanner + tool mapping (Unity first)

## Quick Start

```bash
git clone https://github.com/Firefly0237/GameDev.git
cd GameDev
python -m venv venv
source venv/bin/activate
cp .env.example .env  # Fill in DEEPSEEK_API_KEY
pip install -r requirements.txt
npm install -g @modelcontextprotocol/server-filesystem
pip install mcp-server-git
python create_test_project.py
streamlit run app.py
```

## Architecture

User Input -> Skill Match -> Intent Router (3-way):
  ├── Deterministic (modify_config / modify_code)
  │   -> LLM parse -> Pydantic validate -> code execute
  ├── Agent Loop (review / test / translate / analyze)
  │   -> Plan-Execute: LLM plans steps -> tool calls -> verify
  └── Supervisor (generate_system / summarize_requirement)
      -> Agent Loop with multi-step planning

## Tech Stack

Python · LangGraph (Checkpoint) · MCP · DeepSeek API · Pydantic · Streamlit · SQLite · Docker

## Project Structure

- `app.py`: Streamlit main entry with scan, chat, recommendations, and history
- `pages/`: Shared action helpers, skill execution page, and Git panel
- `config/`: Environment settings and logger
- `database/`: SQLite task logs and LangGraph checkpoint storage
- `scanner/`: Engine-agnostic base scanner and Unity scanner implementation
- `agents/`: LLM client factory
- `mcp_tools/`: Custom GameDev MCP server and multi-server client manager
- `context/`: Skill loading, project schema loading, and built-in Skill .md files
- `schemas/`: Pydantic output models for structured execution
- `graphs/`: Router, agent loop, deterministic executor, and safety layer
- `logs/`: Runtime logs
- `output/`: Generated output artifacts
- `test_project/`: Sample Unity project for validation

## License

MIT
