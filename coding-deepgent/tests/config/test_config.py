from __future__ import annotations

from coding_deepgent import settings as config


def test_model_name_ignores_anthropic_model_id(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("MODEL_ID", "claude-sonnet-4-6")

    assert config.deepgent_model_name() == config.DEFAULT_OPENAI_MODEL

    monkeypatch.setenv("MODEL_ID", "glm-5")

    assert config.deepgent_model_name() == "glm-5"

    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-mini")

    assert config.deepgent_model_name() == "gpt-test-mini"
