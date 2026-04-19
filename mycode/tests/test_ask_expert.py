"""M6-2: AskExpertModel 工具测试。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.tools.ask_expert import _run_ask_expert, register_ask_expert
from mycode.tools.registry import ToolRegistry


class _StubLLM:
    """假的 LLMClient,只实现 .call() 和 .cfg.model。"""

    def __init__(self, content: str = "Expert answer here", raises=None, model="test-expert"):
        self._content = content
        self._raises = raises

        class _Cfg:
            pass

        self.cfg = _Cfg()
        self.cfg.model = model

    def call(self, messages, tools=None):
        if self._raises:
            raise self._raises
        assert tools is None, "expert 不应收到 tools"
        # 校验 messages 结构:应有一条 system + 一条 user
        roles = [m["role"] for m in messages]
        assert roles == ["system", "user"]

        class R:
            pass
        r = R()
        r.content = self._content
        return r


# ---------- 行为 ----------


def test_answer_returned_with_model_prefix():
    out = _run_ask_expert(
        expert_llm=_StubLLM("42 is the answer", model="gpt-sonnet"),
        question="what is the answer?",
    )
    assert "42 is the answer" in out
    assert "gpt-sonnet" in out


def test_empty_question_rejected():
    out = _run_ask_expert(expert_llm=_StubLLM(), question="  ")
    assert out.startswith("Error: question is empty")


def test_empty_answer_rejected():
    out = _run_ask_expert(expert_llm=_StubLLM(content=""), question="x")
    assert out.startswith("Error: expert returned empty")


def test_context_is_passed_to_user_message():
    captured = {}

    class _CapLLM:
        def __init__(self):
            class _Cfg:
                pass
            self.cfg = _Cfg()
            self.cfg.model = "m"

        def call(self, messages, tools=None):
            captured["messages"] = messages

            class R:
                pass
            r = R()
            r.content = "ok"
            return r

    out = _run_ask_expert(
        expert_llm=_CapLLM(),
        question="why?",
        context="prior code: x = 1",
    )
    assert not out.startswith("Error")
    user_msg = captured["messages"][1]["content"]
    assert "prior code: x = 1" in user_msg
    assert "why?" in user_msg
    assert user_msg.startswith("Context:")


def test_no_context_no_prefix():
    captured = {}

    class _CapLLM:
        def __init__(self):
            class _Cfg:
                pass
            self.cfg = _Cfg()
            self.cfg.model = "m"

        def call(self, messages, tools=None):
            captured["messages"] = messages

            class R:
                pass
            r = R()
            r.content = "ok"
            return r

    _run_ask_expert(expert_llm=_CapLLM(), question="why?")
    user_msg = captured["messages"][1]["content"]
    # 不带 Context: 前缀,原样 question
    assert user_msg == "why?"


def test_llm_exception_returned_as_error():
    out = _run_ask_expert(
        expert_llm=_StubLLM(raises=RuntimeError("boom")),
        question="x",
    )
    assert out.startswith("Error: expert LLM failed")
    assert "RuntimeError" in out


def test_expert_gets_no_tools():
    """expert 应该不带 tools 调用(防止嵌套工具调用失控)。"""
    sentinel = {"tools_received": None}

    class _CheckLLM:
        def __init__(self):
            class _Cfg:
                pass
            self.cfg = _Cfg()
            self.cfg.model = "m"

        def call(self, messages, tools=None):
            sentinel["tools_received"] = tools

            class R:
                pass
            r = R()
            r.content = "ok"
            return r

    _run_ask_expert(expert_llm=_CheckLLM(), question="x")
    assert sentinel["tools_received"] is None


# ---------- roles.expert ----------


def test_roles_expert_field_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(
        cli_overrides={
            "provider": "fenbi",
            "roles": {"expert": {"provider": "fenbi-sonnet"}},
        }
    )
    expert_cfg = cfg.derive_for_role("expert")
    assert expert_cfg.model == "pa/claude-sonnet-4-6"


def test_roles_expert_inherits_when_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"provider": "fenbi"})
    expert_cfg = cfg.derive_for_role("expert")
    assert expert_cfg.model == cfg.model


# ---------- registry ----------


def test_registers_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_ask_expert(reg, cfg=cfg, expert_llm=_StubLLM())
    t = reg.get("AskExpertModel")
    assert t is not None
    assert "network" in t.requires
    schema = t.input_schema
    assert "question" in schema["properties"]
    assert "context" in schema["properties"]
    assert schema["required"] == ["question"]
