from types import SimpleNamespace

from homework.agent_app.config import AppConfig
from homework.agent_app.core.compaction import (
    persist_large_output,
    snip_compact,
    write_transcript,
)


def config_for(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    return AppConfig.from_env(tmp_path)


def test_snip_compact_preserves_tool_pair():
    messages = [
        {"role": "user", "content": "start"},
        {
            "role": "assistant",
            "content": [
                SimpleNamespace(type="tool_use", id="tool-1", name="bash")
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tool-1", "content": "ok"}
            ],
        },
        *[
            {"role": "assistant", "content": f"message-{index}"}
            for index in range(10)
        ],
    ]

    compacted = snip_compact(messages, max_messages=6)

    assert messages[1] in compacted
    assert messages[2] in compacted


def test_write_transcript_writes_below_configured_root(tmp_path, monkeypatch):
    config = config_for(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": "remember this"}]

    path = write_transcript(config, messages)

    assert path.is_relative_to(config.transcripts_dir)
    assert path.read_text(encoding="utf-8") == (
        '{"role": "user", "content": "remember this"}\n'
    )


def test_persist_large_output_writes_below_configured_root(
    tmp_path,
    monkeypatch,
):
    config = config_for(tmp_path, monkeypatch)
    output = "x" * (config.persist_threshold + 1)

    persisted = persist_large_output(config, "tool-1", output)
    path = config.tool_result_dir / "tool-1.txt"

    assert path.is_relative_to(config.tool_result_dir)
    assert path.read_text(encoding="utf-8") == output
    assert str(path) in persisted
