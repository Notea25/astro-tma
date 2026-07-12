"""Contract tests for the provider-neutral OpenAI-compatible LLM adapter."""

import json
from types import SimpleNamespace

import pytest

from services import llm_client


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _response(*, text=None, tool_args=None):
    tool_calls = None
    if tool_args is not None:
        tool_calls = [
            SimpleNamespace(
                function=SimpleNamespace(name="publish", arguments=tool_args)
            )
        ]
    message = SimpleNamespace(content=text, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(
        choices=[choice], usage=SimpleNamespace(total_tokens=12), model="test-model"
    )


def _install_fake(monkeypatch, responses):
    completions = FakeCompletions(responses)
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=completions)

    monkeypatch.setattr(llm_client, "AsyncOpenAI", FakeOpenAI)
    return completions, captured


@pytest.mark.asyncio
async def test_client_uses_env_config_and_returns_text(monkeypatch):
    completions, captured = _install_fake(monkeypatch, [_response(text="готово")])
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "secret-value")
    monkeypatch.setattr(llm_client.settings, "LLM_BASE_URL", "https://provider.test/v1")
    monkeypatch.setattr(llm_client.settings, "LLM_MODEL", "provider-model")
    monkeypatch.setattr(llm_client.settings, "LLM_TIMEOUT_SECONDS", 42.0)

    result = await llm_client.create_llm_client().messages.create(
        model="ignored-legacy-model",
        max_tokens=100,
        messages=[{"role": "user", "content": "Привет"}],
    )

    assert captured == {
        "api_key": "secret-value",
        "base_url": "https://provider.test/v1",
        "timeout": 42.0,
    }
    assert result.content[0].text == "готово"
    assert completions.calls[0]["model"] == "provider-model"
    assert completions.calls[0]["extra_body"] is None


@pytest.mark.asyncio
async def test_deepseek_thinking_is_disabled(monkeypatch):
    completions, _ = _install_fake(monkeypatch, [_response(text="готово")])
    monkeypatch.setattr(llm_client.settings, "LLM_BASE_URL", "https://api.deepseek.com")
    await llm_client.create_llm_client("key").messages.create(
        model="any", max_tokens=10, messages=[{"role": "user", "content": "test"}]
    )
    assert completions.calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}


@pytest.mark.asyncio
async def test_tool_schema_is_translated_and_parsed(monkeypatch):
    completions, _ = _install_fake(
        monkeypatch, [_response(tool_args=json.dumps({"value": "ok"}))]
    )
    result = await llm_client.create_llm_client("key").messages.create(
        model="any",
        max_tokens=100,
        messages=[{"role": "user", "content": "Return JSON"}],
        tools=[{
            "name": "publish",
            "description": "Publish result",
            "input_schema": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        }],
        tool_choice={"type": "tool", "name": "publish"},
    )

    assert result.content[0].type == "tool_use"
    assert result.content[0].input == {"value": "ok"}
    assert completions.calls[0]["tools"][0]["function"]["name"] == "publish"


@pytest.mark.asyncio
async def test_malformed_tool_arguments_are_retried_once(monkeypatch):
    completions, _ = _install_fake(
        monkeypatch,
        [_response(tool_args="{"), _response(tool_args='{"value":"ok"}')],
    )
    result = await llm_client.create_llm_client("key").messages.create(
        model="any",
        max_tokens=100,
        messages=[{"role": "user", "content": "Return JSON"}],
        tools=[{"name": "publish", "input_schema": {"type": "object"}}],
        tool_choice={"type": "tool", "name": "publish"},
    )

    assert len(completions.calls) == 2
    assert result.content[0].input == {"value": "ok"}


def test_missing_key_is_rejected(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "")
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        llm_client.create_llm_client()
