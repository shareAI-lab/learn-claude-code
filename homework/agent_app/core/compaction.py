import json
import time
from pathlib import Path

from homework.agent_app.config import AppConfig


def estimate_size(messages: list) -> int:
    return len(str(messages))


def _block_get(block, key, default=None):
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _block_type(block) -> str:
    return _block_get(block, "type")


def _message_has_tool_use(msg: list) -> bool:
    if msg.get("role") != "assistant":
        return False
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(_block_type(block) == "tool_use" for block in content)


def _is_tool_result_message(msg):
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return all(
        isinstance(block, dict) and block.get("type") == "tool_result"
        for block in content
    )


def snip_compact(messages, max_messages=500):
    if len(messages) <= max_messages:
        return messages
    keep_head, keep_tail = 3, max_messages - 3
    head_end, tail_start = keep_head, len(messages) - keep_tail
    if head_end > 0 and _message_has_tool_use(messages[head_end - 1]):
        while head_end < len(messages) and _is_tool_result_message(messages[head_end]):
            head_end += 1
    if (
        tail_start > 0
        and tail_start < len(messages)
        and _message_has_tool_use(messages[tail_start - 1])
        and _is_tool_result_message(messages[tail_start])
    ):
        tail_start -= 1
    if head_end >= tail_start:
        return messages
    snipped = tail_start - head_end
    return (
        messages[:head_end]
        + [{"role": "user", "content": f"[snipped {snipped} messages]"}]
        + messages[tail_start:]
    )


PRESERVE_TOOL_RESULTS = ["task", "load_skill"]


def collect_tool_results(messages: list) -> list:
    blocks = []
    for message_index, message in enumerate(messages):
        if (
            message.get("role") != "user"
            or not isinstance(message.get("content"), list)
        ):
            continue
        for block_index, block in enumerate(message["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                blocks.append((message_index, block_index, block))
    return blocks


def build_tool_use_name_map(messages: list) -> dict[str, str]:
    mapping = {}
    for message in messages:
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if _block_type(block) == "tool_use":
                tool_id = _block_get(block, "id", None)
                tool_name = _block_get(block, "name", None)
                if tool_id and tool_name:
                    mapping[str(tool_id)] = tool_name
    return mapping


def micro_compact(config: AppConfig, messages):
    tool_results = collect_tool_results(messages)
    if len(tool_results) < config.keep_recent:
        return messages

    tool_name = build_tool_use_name_map(messages)
    for _, _, block in tool_results[:-config.keep_recent]:
        content = str(block.get("content", ""))
        tool_id = block.get("tool_use_id")
        name = tool_name.get(tool_id)

        if "<persisted-output>" in content:
            continue
        if name in PRESERVE_TOOL_RESULTS:
            continue
        if len(content) > 120:
            block["content"] = "[Earlier tool result compacted. Re-run if needed.]"
    return messages


def _path_below(root: Path, filename: str) -> Path:
    path = (root / filename).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Persistence path escapes configured root: {filename}")
    return path


def persist_large_output(config: AppConfig, tool_use_id: str, output: str) -> str:
    if len(output) <= config.persist_threshold:
        return output
    config.tool_result_dir.mkdir(parents=True, exist_ok=True)
    path = _path_below(config.tool_result_dir, f"{tool_use_id}.txt")
    if not path.exists():
        path.write_text(output, encoding="utf-8")
    return (
        f"<persisted-output>\nFull output: {path}\nPreview:\n"
        f"{output[:2000]}\n</persisted-output>"
    )


def tool_result_budget(config: AppConfig, messages, max_bytes=20_000):
    last = messages[-1] if messages else None
    if (
        not last
        or last.get("role") != "user"
        or not isinstance(last.get("content"), list)
    ):
        return messages
    blocks = [
        (index, block)
        for index, block in enumerate(last["content"])
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]
    total = sum(len(str(block.get("content", ""))) for _, block in blocks)
    if total <= max_bytes:
        return messages
    ranked = sorted(
        blocks,
        key=lambda pair: len(str(pair[1].get("content", ""))),
        reverse=True,
    )
    for _, block in ranked:
        if total <= max_bytes:
            break
        content = str(block.get("content", ""))
        if len(content) <= config.persist_threshold:
            continue
        tool_use_id = block.get("tool_use_id", "unknown")
        block["content"] = persist_large_output(config, tool_use_id, content)
        total = sum(len(str(block.get("content", ""))) for _, block in blocks)
    return messages


def write_transcript(config: AppConfig, messages: list) -> Path:
    config.transcripts_dir.mkdir(parents=True, exist_ok=True)
    path = _path_below(
        config.transcripts_dir,
        f"transcript_{int(time.time())}.jsonl",
    )
    with path.open("w") as transcript:
        for message in messages:
            transcript.write(json.dumps(message, default=str) + "\n")
    return path


def summarize_history(summarize, messages: list) -> str:
    return summarize(messages)


def compact_history(config: AppConfig, summarize, messages: list) -> list:
    transcript_path = write_transcript(config, messages)
    print(f"[transcript saved: {transcript_path}]")
    summary = summarize_history(summarize, messages)
    return [{"role": "user", "content": f"[Compacted]\n\n{summary}"}]


def reactive_compact(config: AppConfig, summarize, messages: list) -> list:
    write_transcript(config, messages)
    tail_start = max(0, len(messages) - 5)
    if (
        tail_start > 0
        and tail_start < len(messages)
        and _is_tool_result_message(messages[tail_start])
        and _message_has_tool_use(messages[tail_start - 1])
    ):
        tail_start -= 1
    summary = summarize_history(summarize, messages[:tail_start])
    return [
        {"role": "user", "content": f"[Reactive compact]\n\n{summary}"},
        *messages[tail_start:],
    ]
