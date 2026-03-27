from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeVar

import requests
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from config.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class LLMResponse:
    model: str
    content: str
    raw: dict


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def select_model(self, task_type: str) -> str:
        mapping = {
            "router": self.settings.model.router_model,
            "review": self.settings.model.review_model,
            "supervisor": self.settings.model.supervisor_model,
        }
        return mapping.get(task_type, self.settings.model.generation_model)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=4), stop=stop_after_attempt(3), reraise=True)
    def invoke(self, prompt: str, system_prompt: str = "", task_type: str = "generation") -> LLMResponse:
        model = self.select_model(task_type)
        if self.settings.model.provider == "mock":
            content = self._mock_response(prompt=prompt, system_prompt=system_prompt, task_type=task_type)
            return LLMResponse(model=model, content=content, raw={"provider": "mock"})
        return self._invoke_openai_compatible(prompt, system_prompt, model)

    def invoke_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str = "",
        task_type: str = "generation",
    ) -> T:
        response = self.invoke(prompt=prompt, system_prompt=system_prompt, task_type=task_type)
        try:
            return schema.model_validate_json(response.content)
        except Exception:
            logger.warning("Structured response parse failed, falling back to plain JSON decode.")
            return schema.model_validate(json.loads(response.content))

    def _invoke_openai_compatible(self, prompt: str, system_prompt: str, model: str) -> LLMResponse:
        base_url = (self.settings.model.base_url or "").rstrip("/")
        if not base_url:
            raise ValueError("LLM_BASE_URL is required when provider is not mock.")
        headers = {"Content-Type": "application/json"}
        if self.settings.model.api_key:
            headers["Authorization"] = f"Bearer {self.settings.model.api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are GameDev."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(model=model, content=content, raw=data)

    def _mock_response(self, prompt: str, system_prompt: str, task_type: str) -> str:
        _ = system_prompt
        if task_type == "router":
            return json.dumps(
                {
                    "intent": "code_generate",
                    "confidence": 0.51,
                    "matched_pattern": "generate_system",
                    "target_pipeline": "code_generate",
                    "rationale": f"Mock router selected code_generate for input: {prompt[:80]}",
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "message": "Mock response",
                "task_type": task_type,
                "prompt_excerpt": prompt[:120],
            },
            ensure_ascii=False,
        )
