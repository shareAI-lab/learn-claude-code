"""M5-3: 队友 loop 录制回归。

用 respx 拦截 OpenAI Chat Completions 请求,让真实的 start_teammate_loop
在线程里跑起来,验证:
1. WORKING 阶段: 模型返回无 tool_calls → 进入 IDLE
2. IDLE 阶段: 收到消息 → 回 WORKING
3. 收到 shutdown_request → 进 SHUTDOWN,线程退出
"""
from __future__ import annotations

import json
import time

import httpx
import pytest
import respx

from oai_code.config import load_config
from oai_code.llm.client import LLMClient
from oai_code.team import MessageBus, TeammateManager
from oai_code.team.loop import start_teammate_loop
from oai_code.tools.registry import ToolRegistry


def _make_completion(content: str = "", tool_calls: list | None = None) -> dict:
    """构造一个 Chat Completions API 的非流式响应 JSON。"""
    msg: dict = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": msg,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(
        cli_overrides={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
        }
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    return cfg


@respx.mock
def test_teammate_completes_work_then_idles_then_shuts_down(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)

    # 预置 LLM 响应: 第一轮直接 stop(无 tool_calls),队友进 IDLE
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_make_completion("ready to idle"))
    )

    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    parent = ToolRegistry(cfg)
    llm = LLMClient(cfg)

    mgr.register("alice", "dev")
    t = start_teammate_loop(
        name="alice",
        role="dev",
        prompt="do your thing",
        cfg=cfg,
        llm=llm,
        parent_registry=parent,
        bus=bus,
        manager=mgr,
        read_only=True,
        max_work_iterations=3,
        idle_poll_sec=0.1,
        idle_timeout_sec=1.0,  # 短超时,测试快
        autonomous=False,
    )

    # 等队友自然走完: WORK → IDLE → SHUTDOWN
    t.join(timeout=5)
    assert not t.is_alive(), "teammate thread did not exit"
    # 状态最后应为 shutdown
    m = mgr.find("alice")
    assert m["status"] == "shutdown"


@respx.mock
def test_teammate_wakes_from_idle_on_inbox(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)

    # 两轮: 第一轮 stop 进 idle,醒来第二轮再 stop
    responses = [
        httpx.Response(200, json=_make_completion("first turn done")),
        httpx.Response(200, json=_make_completion("woke up, done again")),
    ]
    respx.post("https://api.openai.com/v1/chat/completions").mock(side_effect=responses)

    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    parent = ToolRegistry(cfg)
    llm = LLMClient(cfg)

    mgr.register("alice", "dev")
    t = start_teammate_loop(
        name="alice",
        role="dev",
        prompt="start",
        cfg=cfg,
        llm=llm,
        parent_registry=parent,
        bus=bus,
        manager=mgr,
        read_only=True,
        max_work_iterations=3,
        idle_poll_sec=0.1,
        idle_timeout_sec=5.0,  # 放宽防 flaky
        autonomous=False,
    )

    # 等 alice 进入 idle(在第一轮 stop 之后)
    deadline = time.time() + 5
    while time.time() < deadline:
        if mgr.find("alice")["status"] == "idle":
            break
        time.sleep(0.05)
    assert mgr.find("alice")["status"] == "idle", (
        f"alice did not reach idle state in time, got {mgr.find('alice')}"
    )

    # 发消息唤醒
    bus.send("lead", "alice", "wake up please")

    t.join(timeout=10)
    assert not t.is_alive()
    # 最终 shutdown(第二轮 stop 后 idle 超时)
    assert mgr.find("alice")["status"] == "shutdown"


@respx.mock
def test_teammate_shutdown_request_terminates_immediately(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_make_completion("working..."))
    )

    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    parent = ToolRegistry(cfg)
    llm = LLMClient(cfg)

    mgr.register("bob", "dev")
    t = start_teammate_loop(
        name="bob",
        role="dev",
        prompt="work",
        cfg=cfg,
        llm=llm,
        parent_registry=parent,
        bus=bus,
        manager=mgr,
        read_only=True,
        max_work_iterations=5,
        idle_poll_sec=0.1,
        idle_timeout_sec=5.0,
        autonomous=False,
    )

    # 立刻发 shutdown_request
    bus.send(
        "lead", "bob", "please stop",
        msg_type="shutdown_request",
        extra={"request_id": "x1"},
    )

    t.join(timeout=5)
    assert not t.is_alive()
    assert mgr.find("bob")["status"] == "shutdown"


@respx.mock
def test_teammate_autoclaim_task(tmp_path, monkeypatch):
    """autonomous=True 时,idle 阶段应从 .oaic/tasks/ 认领未阻塞任务。"""
    cfg = _setup(tmp_path, monkeypatch)
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_make_completion("done"))
    )

    from oai_code.tools.tasks import TaskStore
    store = TaskStore(cfg)
    store.create("do the laundry", "desc")

    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    parent = ToolRegistry(cfg)
    llm = LLMClient(cfg)

    mgr.register("claire", "dev")
    t = start_teammate_loop(
        name="claire",
        role="dev",
        prompt="start",
        cfg=cfg,
        llm=llm,
        parent_registry=parent,
        bus=bus,
        manager=mgr,
        task_store=store,
        read_only=True,
        max_work_iterations=2,
        idle_poll_sec=0.1,
        idle_timeout_sec=1.5,
        autonomous=True,
    )

    t.join(timeout=5)
    # 任务应被 claire 认领
    claimed = json.loads(store.get(1))
    assert claimed["owner"] == "claire"
    assert claimed["status"] == "in_progress"
