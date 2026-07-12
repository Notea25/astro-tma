"""Provider-neutral adapter for OpenAI-compatible chat-completion APIs.

The public shape mirrors the project's historical ``messages.create`` subset.
This keeps domain
prompts and response parsers stable while the transport is fully provider
agnostic. DeepSeek, Gemini, Groq, OpenAI, MiniMax, Qwen and Kimi can be selected
with ``LLM_BASE_URL``, ``LLM_API_KEY`` and ``LLM_MODEL`` only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

from openai import AsyncOpenAI

from core.settings import settings


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


class _MessagesAdapter:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    @staticmethod
    def _tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _tool_choice(choice: dict[str, Any] | None) -> Any:
        if not choice:
            return None
        kind = choice.get("type")
        if kind == "tool":
            return {"type": "function", "function": {"name": choice["name"]}}
        return {"any": "required"}.get(str(kind), kind)

    async def create(
        self,
        *,
        model: str | None = None,
        max_tokens: int,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        temperature: float | None = None,
        **_: Any,
    ) -> Any:
        request_messages = list(messages)
        if system:
            request_messages = [{"role": "system", "content": system}, *request_messages]
        openai_tools = self._tools(tools)
        openai_choice = self._tool_choice(tool_choice)

        # A malformed forced-tool payload is safe to retry once: callers use
        # idempotent generation and perform their own semantic validation.
        attempts = 2 if openai_tools and openai_choice else 1
        last_error: Exception | None = None
        for _attempt in range(attempts):
            extra_body = None
            if urlparse(settings.LLM_BASE_URL).hostname == "api.deepseek.com":
                # V4 can default to thinking mode. These content-generation
                # paths do not need paid reasoning tokens.
                extra_body = {"thinking": {"type": "disabled"}}
            response = await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                max_tokens=max_tokens,
                messages=request_messages,  # type: ignore[arg-type]
                tools=openai_tools,  # type: ignore[arg-type]
                tool_choice=openai_choice,
                temperature=temperature,
                extra_body=extra_body,
            )
            choice = response.choices[0]
            output: list[TextBlock | ToolUseBlock] = []
            if choice.message.content:
                output.append(TextBlock(choice.message.content))
            try:
                for call in choice.message.tool_calls or []:
                    function = getattr(call, "function", None)
                    if function is None:
                        continue
                    output.append(
                        ToolUseBlock(
                            name=function.name,
                            input=json.loads(function.arguments),
                        )
                    )
            except (json.JSONDecodeError, TypeError) as exc:
                last_error = exc
                continue
            return SimpleNamespace(
                content=output,
                stop_reason={"length": "max_tokens", "stop": "end_turn"}.get(
                    choice.finish_reason, choice.finish_reason
                ),
                usage=response.usage,
                model=response.model,
            )
        assert last_error is not None
        raise ValueError("LLM returned malformed tool arguments") from last_error


class LLMClient:
    def __init__(self, api_key: str | None = None) -> None:
        client = AsyncOpenAI(
            api_key=api_key or settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        self.messages = _MessagesAdapter(client)


def create_llm_client(api_key: str | None = None) -> LLMClient:
    if not (api_key or settings.LLM_API_KEY):
        raise RuntimeError("LLM_API_KEY is not configured")
    return LLMClient(api_key)
