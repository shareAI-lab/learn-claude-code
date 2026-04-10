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
def fake_langchain_openai(monkeypatch: pytest.MonkeyPatch) -> type[FakeChatOpenAI]:
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

    common = importlib.import_module("agents_langchain.common")

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

    common = importlib.import_module("agents_langchain._common")

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
