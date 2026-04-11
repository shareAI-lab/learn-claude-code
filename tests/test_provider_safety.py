from __future__ import annotations

import importlib
import socket
import sys
import types

import pytest

import conftest


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def fake_langchain_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> type[FakeChatOpenAI]:
    module = types.ModuleType("langchain_openai")
    module.ChatOpenAI = FakeChatOpenAI
    monkeypatch.setitem(sys.modules, "langchain_openai", module)
    return FakeChatOpenAI


def test_network_access_is_blocked_in_tests() -> None:
    with pytest.raises(AssertionError, match="Network access is disabled"):
        socket.create_connection(("example.com", 443))


def test_provider_credential_guard_covers_live_auth_env_vars() -> None:
    assert {
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    }.issubset(conftest.PROVIDER_ENV_VARS)


def test_common_build_openai_model_uses_stubbed_client(
    monkeypatch: pytest.MonkeyPatch,
    fake_langchain_openai: type[FakeChatOpenAI],
) -> None:
    del fake_langchain_openai

    common = importlib.import_module("agents_deepagents.common")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-mini")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.delenv("MODEL_ID", raising=False)

    model = common.build_openai_model(temperature=0.25, timeout=9)

    assert isinstance(model, FakeChatOpenAI)
    assert model.kwargs == {
        "model": "gpt-test-mini",
        "temperature": 0.25,
        "timeout": 9,
        "base_url": "https://example.invalid/v1",
    }


def test_private_common_build_openai_chat_model_uses_stubbed_client(
    monkeypatch: pytest.MonkeyPatch,
    fake_langchain_openai: type[FakeChatOpenAI],
) -> None:
    del fake_langchain_openai

    common = importlib.import_module("agents_deepagents._common")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-nano")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.delenv("MODEL_ID", raising=False)

    model = common.build_openai_chat_model(temperature=0.1, timeout=7)

    assert isinstance(model, FakeChatOpenAI)
    assert model.kwargs == {
        "model": "gpt-test-nano",
        "temperature": 0.1,
        "timeout": 7,
        "base_url": "https://example.invalid/v1",
    }


def test_deepagents_model_resolution_does_not_reuse_anthropic_model_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = importlib.import_module("agents_deepagents.common")
    private_common = importlib.import_module("agents_deepagents._common")

    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("MODEL_ID", "claude-sonnet-4-6")

    assert common.deepagents_model_name() == common.DEFAULT_OPENAI_MODEL
    assert (
        private_common.resolve_openai_model()
        == private_common.DEFAULT_OPENAI_MODEL
    )

    monkeypatch.setenv("MODEL_ID", "glm-5")

    assert common.deepagents_model_name() == "glm-5"
    assert private_common.resolve_openai_model() == "glm-5"
