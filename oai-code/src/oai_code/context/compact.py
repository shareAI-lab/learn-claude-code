"""上下文压缩: microcompact + auto-compact。

对齐 DESIGN §4.3:
- microcompact: 每轮调用前,把超过 keep_recent_tool_results 的、
  且体积 > evict_threshold_bytes 的 tool_result 外置到 .oaic/blobs/<hash>.txt
- auto-compact: 超 context_window * threshold_pct% 时,让 summarize role 压缩
  messages(保留 system / 最近若干轮) 为单条 user 提示
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from ..config.models import Config


def _blobs_dir(cfg: Config) -> Path:
    d = cfg.workspace_root() / ".oaic" / "blobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _transcripts_dir(cfg: Config) -> Path:
    d = cfg.workspace_root() / ".oaic" / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """粗略按 ~4 字符/token 估算。"""
    return len(json.dumps(messages, default=str, ensure_ascii=False)) // 4


def microcompact(messages: list[dict[str, Any]], cfg: Config) -> int:
    """就地修改 messages: 外置过旧的大 tool_result。

    返回被外置的条目数。
    """
    keep = cfg.compact.keep_recent_tool_results
    thresh = cfg.compact.evict_threshold_bytes

    # 找出所有 tool_result 消息的索引
    tool_msg_idx = [
        i for i, m in enumerate(messages) if m.get("role") == "tool"
    ]
    if len(tool_msg_idx) <= keep:
        return 0

    evictable = tool_msg_idx[:-keep] if keep > 0 else tool_msg_idx
    evicted = 0
    for i in evictable:
        content = messages[i].get("content", "")
        if not isinstance(content, str):
            continue
        if len(content.encode("utf-8")) <= thresh:
            continue
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        blob_path = _blobs_dir(cfg) / f"{h}.txt"
        if not blob_path.exists():
            blob_path.write_text(content, encoding="utf-8")
        messages[i]["content"] = (
            f"[evicted to {blob_path}; "
            f"original {len(content)} chars; use Read tool to retrieve]"
        )
        evicted += 1
    return evicted


def auto_compact(
    messages: list[dict[str, Any]],
    cfg: Config,
    summarize_llm,  # LLMClient 走 summarize role
) -> list[dict[str, Any]]:
    """将 messages 压成: [system] + [summary as user] + [最近若干条消息]。

    summary 由 summarize_llm 单次非流式调用生成。
    完整 messages 先落盘到 .oaic/transcripts/。
    """
    # 落盘
    ts = int(time.time())
    dump_path = _transcripts_dir(cfg) / f"transcript_{ts}.jsonl"
    with dump_path.open("w", encoding="utf-8") as f:
        for m in messages:
            f.write(json.dumps(m, default=str, ensure_ascii=False) + "\n")

    # 拆出 system + 最近一段保留
    system_msgs = [m for m in messages if m.get("role") == "system"]
    tail_keep = 6  # 保留最近 6 条 non-system 消息,避免摘要后立即上下文断裂
    non_system = [m for m in messages if m.get("role") != "system"]
    tail = non_system[-tail_keep:] if len(non_system) > tail_keep else non_system
    head = non_system[:-tail_keep] if len(non_system) > tail_keep else []

    # 对 head 生成摘要
    if head:
        head_text = json.dumps(head, default=str, ensure_ascii=False)[-40000:]
        prompt = (
            "Summarize the following conversation for continuity. Preserve:\n"
            "- user intent & pending tasks\n"
            "- files/paths already read or edited\n"
            "- key findings and tool outputs\n"
            "- any errors the assistant hit\n\n"
            f"Conversation JSON:\n{head_text}"
        )
        try:
            resp = summarize_llm.call(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
            )
            summary = resp.content or "(summarize returned empty)"
        except Exception as e:
            summary = f"(summarize failed: {type(e).__name__}: {e})"
    else:
        summary = "(no earlier messages to summarize)"

    new_messages: list[dict[str, Any]] = []
    new_messages.extend(system_msgs)
    new_messages.append(
        {
            "role": "user",
            "content": (
                f"<compacted transcript=\"{dump_path}\">\n{summary}\n</compacted>"
            ),
        }
    )
    new_messages.extend(tail)
    return new_messages


def should_auto_compact(messages: list[dict[str, Any]], cfg: Config) -> bool:
    estimated = estimate_tokens(messages)
    limit = int(cfg.context_window * cfg.compact.threshold_pct / 100)
    return estimated >= limit
