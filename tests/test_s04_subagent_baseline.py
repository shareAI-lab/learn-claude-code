from __future__ import annotations

import importlib


def test_s04_build_subagents_describes_the_child_agent_surface() -> None:
    s04 = importlib.import_module("agents_deepagents.s04_subagent")
    model = object()

    subagents = s04.build_subagents(model)

    assert subagents == [
        {
            "name": s04.SUBAGENT_TYPE,
            "description": s04.SUBAGENT_DESCRIPTION,
            "system_prompt": s04.SUBAGENT_SYSTEM,
            "model": model,
            "tools": s04.TOOLS,
        }
    ]


def test_s04_build_agent_uses_subagent_middleware_instead_of_legacy_helpers(
    monkeypatch,
) -> None:
    s04 = importlib.import_module("agents_deepagents.s04_subagent")
    captured: dict[str, object] = {}

    class FakeSubAgentMiddleware:
        def __init__(self, *, backend, subagents):
            captured["backend"] = backend
            captured["subagents"] = subagents

    def fake_create_agent(*, model, tools, system_prompt, middleware):
        captured["model"] = model
        captured["tools"] = tools
        captured["system_prompt"] = system_prompt
        captured["middleware"] = middleware
        return object()

    main_model = object()
    child_model = object()

    monkeypatch.setattr(s04, "create_agent", fake_create_agent)
    monkeypatch.setattr(s04, "SubAgentMiddleware", FakeSubAgentMiddleware)

    agent = s04.build_agent(model=main_model, subagent_model=child_model)

    assert agent is not None
    assert captured["model"] is main_model
    assert captured["tools"] == s04.TOOLS
    assert captured["system_prompt"] == s04.SYSTEM
    assert len(captured["middleware"]) == 1
    assert captured["backend"] is s04.StateBackend
    assert captured["subagents"] == s04.build_subagents(child_model)
    assert not hasattr(s04, "run_subagent")
    assert not hasattr(s04, "task")
    assert not hasattr(s04, "PARENT_TOOLS")
    assert not hasattr(s04, "CHILD_TOOLS")


def test_s04_build_agent_defaults_child_model_to_parent_model(
    monkeypatch,
) -> None:
    s04 = importlib.import_module('agents_deepagents.s04_subagent')
    main_model = object()
    captured: dict[str, object] = {}
    main_model = object()

    class FakeSubAgentMiddleware:
        def __init__(self, *, backend, subagents):
            captured["backend"] = backend
            captured["subagents"] = subagents

    monkeypatch.setattr(s04, "build_openai_model", lambda: main_model)
    monkeypatch.setattr(s04, "SubAgentMiddleware", FakeSubAgentMiddleware)
    monkeypatch.setattr(
        s04,
        "create_agent",
        lambda **kwargs: kwargs,
    )

    agent = s04.build_agent()

    assert agent["model"] is main_model
    assert captured["backend"] is s04.StateBackend
    assert captured["subagents"] == s04.build_subagents(main_model)


def test_s04_agent_loop_appends_only_parent_summary(monkeypatch) -> None:
    s04 = importlib.import_module("agents_deepagents.s04_subagent")

    class FakeAgent:
        def __init__(self) -> None:
            self.payloads = []

        def invoke(self, payload):
            self.payloads.append({"messages": [*payload["messages"]]})
            return {
                "messages": [
                    *payload["messages"],
                    {"role": "assistant", "content": "delegated findings"},
                ]
            }

    fake = FakeAgent()
    monkeypatch.setattr(s04, "build_agent", lambda: fake)

    history = [{"role": "user", "content": "continue"}]

    assert s04.agent_loop(history) == "delegated findings"
    assert fake.payloads == [
        {"messages": [{"role": "user", "content": "continue"}]}
    ]
    assert history == [
        {"role": "user", "content": "continue"},
        {"role": "assistant", "content": "delegated findings"},
    ]
