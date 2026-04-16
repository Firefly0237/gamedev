from langchain_core.messages import AIMessage, AIMessageChunk


def extract_total_tokens(response) -> int:
    usage = response.response_metadata.get("token_usage", {}) if getattr(response, "response_metadata", None) else {}
    if "total_tokens" in usage:
        return usage["total_tokens"] or 0
    usage2 = getattr(response, "usage_metadata", None) or {}
    return usage2.get("total_tokens", 0) or 0


def content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content or "")


def merge_response_chunks(chunks: list[AIMessageChunk]) -> AIMessage:
    """合并流式响应 chunk，恢复成完整 AIMessage。"""
    if not chunks:
        return AIMessage(content="")

    merged = chunks[0]
    for chunk in chunks[1:]:
        merged += chunk
    return AIMessage(
        content=merged.content,
        additional_kwargs=getattr(merged, "additional_kwargs", {}),
        response_metadata=getattr(merged, "response_metadata", {}),
        tool_calls=getattr(merged, "tool_calls", []),
        invalid_tool_calls=getattr(merged, "invalid_tool_calls", []),
        usage_metadata=getattr(merged, "usage_metadata", None),
    )
