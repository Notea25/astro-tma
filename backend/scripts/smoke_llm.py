"""Read-only smoke test for the configured OpenAI-compatible LLM provider.

Runs three synthetic calls (short text, forced structured output, long Russian
text) and never touches the database. Usage is printed when the provider
returns it. Run inside the backend container:

    python scripts/smoke_llm.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.settings import settings
from services.llm_client import create_llm_client
from services.llm_utils import first_text_block


def _usage(message: Any) -> str:
    usage = getattr(message, "usage", None)
    return str(usage) if usage is not None else "usage unavailable"


async def main() -> None:
    if not settings.LLM_API_KEY:
        raise SystemExit("LLM_API_KEY is missing")
    client = create_llm_client()

    short = await client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=120,
        messages=[{"role": "user", "content": "Ответь одной фразой по-русски: тест успешен."}],
    )
    print("short:", first_text_block(short.content), _usage(short))

    structured = await client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=180,
        messages=[{"role": "user", "content": "Передай короткий результат через функцию."}],
        tools=[{
            "name": "publish_smoke_result",
            "description": "Publish smoke-test result",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["status", "message"],
                "additionalProperties": False,
            },
        }],
        tool_choice={"type": "tool", "name": "publish_smoke_result"},
    )
    tool = next((b for b in structured.content if b.type == "tool_use"), None)
    if tool is None:
        raise RuntimeError("provider did not return the forced structured result")
    print("structured:", tool.input, _usage(structured))

    long = await client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                "Напиши связный текст на русском языке объёмом 350–450 слов о том, "
                "как человеку планировать неделю. Без эзотерики, markdown и повторов."
            ),
        }],
    )
    text = first_text_block(long.content)
    if len(text.split()) < 250:
        raise RuntimeError("long-text response is unexpectedly short")
    print("long:", len(text.split()), "words", _usage(long))


if __name__ == "__main__":
    asyncio.run(main())
