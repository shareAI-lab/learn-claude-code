"""M2-1: Session 持久化与 resume 测试。"""
from __future__ import annotations

import re
import time

from oai_code.config import load_config
from oai_code.session import SessionStore


def _store(tmp_path, monkeypatch, **over):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom", **over})
    return SessionStore(cfg)


def test_new_session_creates_file(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    sid = s.new_session()
    assert re.match(r"^\d{8}-\d{6}-[0-9a-f]{4}$", sid)
    assert s.path().exists()


def test_append_new_messages(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.new_session()
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    wrote = s.append_new_messages(msgs)
    assert wrote == 3
    # 追加第二轮
    msgs.append({"role": "user", "content": "again"})
    wrote = s.append_new_messages(msgs)
    assert wrote == 1
    # 再次调用不写重复
    wrote = s.append_new_messages(msgs)
    assert wrote == 0


def test_load_roundtrip(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    sid = s.new_session()
    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    s.append_new_messages(msgs)

    # 新 store 加载
    s2 = _store(tmp_path, monkeypatch)
    loaded = s2.load(sid)
    assert len(loaded) == 2
    assert loaded[0]["content"] == "hello"
    assert s2.session_id == sid


def test_load_missing_raises(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    try:
        s.load("20990101-000000-dead")
    except FileNotFoundError:
        return
    assert False, "expected FileNotFoundError"


def test_list_ids_sorted_by_mtime(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    sid1 = s.new_session()
    s.append_new_messages([{"role": "user", "content": "a"}])
    time.sleep(0.02)
    sid2 = s.new_session()
    s.append_new_messages([{"role": "user", "content": "b"}])
    ids = s.list_ids()
    assert ids[0] == sid2
    assert sid1 in ids


def test_latest_id(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    assert s.latest_id() is None
    sid = s.new_session()
    assert s.latest_id() == sid


def test_summary(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    sid = s.new_session()
    s.append_new_messages(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "real user question"},
            {"role": "assistant", "content": "ok"},
        ]
    )
    summ = s.summary(sid)
    assert summ["messages"] == 3
    assert "real user question" in summ["first_user"]


def test_auto_save_false_no_write(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch, session={"auto_save": False})
    s.new_session()
    wrote = s.append_new_messages([{"role": "user", "content": "x"}])
    assert wrote == 0


def test_redact_on_write(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.new_session()
    s.append_new_messages(
        [
            {
                "role": "user",
                "content": "Authorization: Bearer fb-abcdef0123456789",
            }
        ]
    )
    raw = s.path().read_text()
    assert "fb-abcdef0123456789" not in raw
    assert "[REDACTED]" in raw
