from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage

from graphs.llm_utils import content_to_text
from schemas.outputs import WorkerAgentResult, try_parse


def extract_json_payload(text: str) -> str:
    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"```\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def parse_worker_payload(text: str) -> WorkerAgentResult | None:
    result, _ = try_parse(text, WorkerAgentResult)
    if result:
        return result

    try:
        parsed = json.loads(extract_json_payload(text))
        return WorkerAgentResult(**parsed)
    except Exception:
        return None


def latest_worker_payload(messages: list, worker_names: set[str]) -> WorkerAgentResult | None:
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue
        if not message.name or message.name not in worker_names:
            continue
        if getattr(message, "response_metadata", {}).get("__is_handoff_back"):
            continue
        payload = parse_worker_payload(content_to_text(message.content))
        if payload:
            return payload
    return None
