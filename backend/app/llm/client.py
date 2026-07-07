"""OpenRouter LLM client — sole gateway to model APIs (P7, D-009)."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

logger = logging.getLogger("oce.llm")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class NodeFailure(Exception):
    """Raised when structured output cannot be produced after repair."""


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    status: str = "ok"  # ok | repaired | failed
    output_digest: str = ""


class LLMClient:
    """Structured chat-completions via OpenRouter. No other module may call OpenRouter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _model_for(self, node_name: str) -> str:
        return self._settings.llm_models.get(node_name, "anthropic/claude-sonnet-4.6")

    def _max_tokens_for(self, node_name: str) -> int:
        return self._settings.llm_max_tokens.get(node_name, 4096)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://oce.local",
            "X-Title": "Operational Context Engine",
        }

    def _digest(self, payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _api_schema(schema: dict[str, Any]) -> dict[str, Any]:
        """Anthropic structured output rejects maxItems — enforce via Pydantic post-parse."""
        out = json.loads(json.dumps(schema))

        def _walk(obj: object) -> None:
            if isinstance(obj, dict):
                obj.pop("maxItems", None)
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v)

        _walk(out)
        return out

    def _parse_json_content(self, content: str, schema: type[BaseModel]) -> BaseModel:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        return schema.model_validate(data)

    def _request(
        self,
        *,
        node_name: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        repair: bool,
    ) -> tuple[BaseModel, LLMUsage]:
        model = self._model_for(node_name)
        started = datetime.now(UTC)
        t0 = time.perf_counter()

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._max_tokens_for(node_name),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": self._api_schema(schema.model_json_schema()),
                },
            },
        }

        last_exc: Exception | None = None
        for attempt in range(self._settings.llm_max_retries + 1):
            try:
                with httpx.Client(timeout=self._settings.llm_timeout_seconds) as client:
                    resp = client.post(OPENROUTER_URL, headers=self._headers(), json=body)
                    resp.raise_for_status()
                    payload = resp.json()
                break
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt >= self._settings.llm_max_retries:
                    raise NodeFailure(f"transport error after retries: {exc}") from exc
                time.sleep(random.uniform(0.3, 1.0) * (attempt + 1))
        else:
            raise NodeFailure(f"transport error: {last_exc}")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        usage_raw = payload.get("usage") or {}
        prompt_tokens = int(usage_raw.get("prompt_tokens") or 0)
        completion_tokens = int(usage_raw.get("completion_tokens") or 0)

        content = payload["choices"][0]["message"]["content"]
        status = "ok"
        try:
            parsed = self._parse_json_content(content, schema)
        except (json.JSONDecodeError, ValidationError) as first_err:
            if not repair:
                raise NodeFailure(f"parse/validation failed: {first_err}") from first_err
            status = "repaired"
            repair_messages = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        f"Your JSON failed validation: {first_err}. "
                        "Return corrected JSON only, conforming exactly to the schema."
                    ),
                },
            ]
            repair_body = {**body, "messages": repair_messages}
            with httpx.Client(timeout=self._settings.llm_timeout_seconds) as client:
                resp = client.post(OPENROUTER_URL, headers=self._headers(), json=repair_body)
                resp.raise_for_status()
                payload2 = resp.json()
            content2 = payload2["choices"][0]["message"]["content"]
            usage2 = payload2.get("usage") or {}
            prompt_tokens += int(usage2.get("prompt_tokens") or 0)
            completion_tokens += int(usage2.get("completion_tokens") or 0)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            try:
                parsed = self._parse_json_content(content2, schema)
            except (json.JSONDecodeError, ValidationError) as second_err:
                raise NodeFailure(f"repair failed: {second_err}") from second_err

        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status,
            output_digest=self._digest(parsed.model_dump()),
        )
        _ = started  # ponytail: started_at recorded by caller from wall clock
        return parsed, usage

    def complete_structured(
        self,
        node_name: str,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
    ) -> tuple[BaseModel, LLMUsage]:
        """One structured completion with a single repair round-trip on parse failure."""
        if not self._settings.openrouter_api_key:
            raise NodeFailure("OPENROUTER_API_KEY not configured")
        return self._request(node_name=node_name, messages=messages, schema=schema, repair=True)
