"""Small helpers shared by LLM integrations."""

from typing import Any


def first_text_block(content: Any) -> str:
    """Return the first text block from the provider-neutral response."""
    for block in content or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            return text
    return ""
