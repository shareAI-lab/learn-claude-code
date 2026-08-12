"""Agent-turn orchestration over explicit runtime state."""

from __future__ import annotations

import copy
import json
import time

from homework.agent_app.core.compaction import (
    compact_history,
    estimate_size,
    micro_compact,
    persist_large_output,
    reactive_compact,
    snip_compact,
    tool_result_budget,
)
from homework.agent_app.core.context import append_user_text_blocks, build_context
from homework.agent_app.core.recovery import (
    PartialStreamError,
    RecoveryState,
    append_unrecoverable_error,
    is_prompt_too_long_error,
    with_retry,
)
from homework.agent_app.features.background import (
    collect_background_results,
    start_background_task,
)
from homework.agent_app.features.mcp import snapshot_mcp_tools
from homework.agent_app.features.memory import (
    build_request_messages_with_memories,
    consolidate_memories,
    extract_memories,
)
from homework.agent_app.features.scheduler import consume_cron_queue
from homework.agent_app.features.teams.protocol import collect_lead_inbox
from homework.agent_app.runtime import RuntimeContext
from homework.agent_app.tools.builtin import resolve_tool_cwd
from homework.agent_app.tools.executor import execute_tool, should_run_background


CONTINUATION_PROMPT = (
    "Output token limit hit. Resume directly — "
    "no apology, no recap. Pick up mid-thought."
)
TEAM_GUARDED_TOOLS = {"bash", "write_file"}


def _block_value(block, name, default=None):
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def _has_tool_use(content) -> bool:
    return any(_block_value(block, "type") == "tool_use" for block in content)


def _extract_text(content) -> str:
    return "\n".join(
        str(_block_value(block, "text", ""))
        for block in content
        if _block_value(block, "type") == "text"
    ).strip()


def _summarize(runtime: RuntimeContext, payload, max_tokens: int = 2_000) -> str:
    if isinstance(payload, list):
        conversation = json.dumps(payload, default=str)[:80_000]
        prompt = (
            "Summarize this coding-agent conversation so work can continue.\n"
            "Preserve: 1. current goal, 2. key findings/decisions, "
            "3. files read/changed, 4. remaining work, 5. user constraints.\n"
            "Be compact but concrete.\n\n" + conversation
        )
    else:
        prompt = str(payload)
    response = runtime.llm.create(
        model=runtime.config.primary_model,
        system=None,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        tools=None,
    )
    return _extract_text(response.content) or "(empty summary)"


def _format_team_inbox(messages: list[dict]) -> str:
    lines = ["[Team inbox]"]
    for message in messages:
        content = message.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        lines.append(
            f"From {message.get('from')}"
            f"({message.get('type')})"
            f"{content}"
        )
    return "\n".join(lines)


def _collect_team_messages(runtime: RuntimeContext) -> list[dict]:
    return collect_lead_inbox(
        runtime.bus,
        runtime.protocols,
        hook=runtime.hooks.trigger,
        cwd_resolver=lambda cwd: resolve_tool_cwd(runtime.config.workdir, cwd),
        guarded_tools=TEAM_GUARDED_TOOLS,
        clock=time.time,
        sleep=time.sleep,
    )


def _has_active_teammates(runtime: RuntimeContext) -> bool:
    with runtime.team.lock:
        return bool(runtime.team.active)


def _wait_for_team_activity(runtime: RuntimeContext) -> bool:
    deadline = time.time() + runtime.config.permission_timeout
    while True:
        messages = _collect_team_messages(runtime)
        if messages:
            append_user_text_blocks(
                runtime.session.history,
                [_format_team_inbox(messages)],
            )
            return True
        if not _has_active_teammates(runtime):
            return False
        if time.time() >= deadline:
            print(
                "  \033[33m[team] wait timed out; "
                "teammates remain active\033[0m"
            )
            return False
        time.sleep(runtime.config.permission_poll_interval)


def _update_context(runtime: RuntimeContext, tools: list[dict] | None = None) -> None:
    if tools is None:
        tools, _handlers = snapshot_mcp_tools(
            runtime.mcp, *runtime.tools.snapshot()
        )
    runtime.session.context = build_context(runtime, tools)


def run_agent_loop(runtime: RuntimeContext) -> None:
    """Run one agent turn, mutating only the supplied runtime's owned state."""
    session = runtime.session
    messages = session.history
    state = RecoveryState(
        current_model=runtime.config.primary_model,
        fallback_model=runtime.config.fallback_model,
    )
    max_tokens = runtime.config.default_max_tokens
    summarize = lambda payload, max_tokens=2_000: _summarize(
        runtime, payload, max_tokens
    )

    while True:
        fired_jobs = consume_cron_queue(runtime.scheduler)
        pending_texts = [
            f"[Scheduled: {job.id}] {job.prompt}" for job in fired_jobs
        ]
        pending_texts.extend(collect_background_results(runtime.background))
        team_messages = _collect_team_messages(runtime)
        if team_messages:
            pending_texts.append(_format_team_inbox(team_messages))
        append_user_text_blocks(messages, pending_texts)

        pre_compact_messages = copy.deepcopy(messages)
        messages[:] = tool_result_budget(runtime.config, messages)
        messages[:] = snip_compact(messages)
        messages[:] = micro_compact(runtime.config, messages)
        if estimate_size(messages) > runtime.config.context_limit:
            print("[auto compact]")
            messages[:] = compact_history(runtime.config, summarize, messages)

        if session.rounds_since_todo >= 3:
            messages.append(
                {
                    "role": "user",
                    "content": "<reminder> Update your todos.</reminder>",
                }
            )
            session.rounds_since_todo = 0

        tools, handlers = snapshot_mcp_tools(
            runtime.mcp, *runtime.tools.snapshot()
        )
        _update_context(runtime, tools)
        system = runtime.prompt_builder.build(session.context)
        request_messages = build_request_messages_with_memories(
            runtime.memory, messages, summarize
        )

        try:
            response = with_retry(
                lambda: runtime.llm.create_streaming(
                    system=system,
                    messages=request_messages,
                    model=state.current_model,
                    max_tokens=max_tokens,
                    tools=tools,
                ),
                state,
                max_transient_retries=runtime.config.max_transient_retries,
                max_consecutive_529=runtime.config.max_consecutive_529,
                base_delay_ms=runtime.config.base_delay_ms,
            )
        except PartialStreamError as stream_exc:
            state.has_escalated = True
            max_tokens = runtime.config.escalated_max_tokens
            partial_text = stream_exc.partial_text
            if state.continuation_count < runtime.config.max_continuations:
                messages.append(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": partial_text}],
                    }
                )
                state.continuation_count += 1
                messages.append({"role": "user", "content": CONTINUATION_PROMPT})
                print(
                    f"  \033[33m[stream interrupted] continuation "
                    f"{state.continuation_count}/"
                    f"{runtime.config.max_continuations} with "
                    f"{runtime.config.escalated_max_tokens} tokens\033[0m"
                )
                continue
            cause_text = (
                f"{type(stream_exc.cause).__name__}: "
                f"{str(stream_exc.cause)[:300]}"
            )
            marker = f"[Stream interrupted: {cause_text}]"
            separator = "" if partial_text.endswith("\n") else "\n"
            print(marker)
            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{partial_text}{separator}{marker}",
                        }
                    ],
                }
            )
            _update_context(runtime)
            return
        except Exception as exc:
            if (
                is_prompt_too_long_error(exc)
                and state.reactive_compact_count
                < runtime.config.max_reactive_compacts
            ):
                state.reactive_compact_count += 1
                try:
                    messages[:] = reactive_compact(
                        runtime.config, summarize, messages
                    )
                except Exception as compact_exc:
                    append_unrecoverable_error(messages, compact_exc)
                    _update_context(runtime)
                    return
                print("[recovery] reactive compact")
                continue
            append_unrecoverable_error(messages, exc)
            _update_context(runtime)
            return

        if response.stop_reason == "max_tokens":
            messages.append({"role": "assistant", "content": response.content})
            truncated_tool_uses = [
                block
                for block in response.content
                if _block_value(block, "type") == "tool_use"
            ]
            if truncated_tool_uses:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": _block_value(block, "id"),
                                "content": (
                                    "Tool call was not executed because the "
                                    "response hit the output token limit."
                                ),
                                "is_error": True,
                            }
                            for block in truncated_tool_uses
                        ],
                    }
                )
            state.has_escalated = True
            max_tokens = runtime.config.escalated_max_tokens
            if state.continuation_count < runtime.config.max_continuations:
                state.continuation_count += 1
                if truncated_tool_uses:
                    messages[-1]["content"].append(
                        {"type": "text", "text": CONTINUATION_PROMPT}
                    )
                else:
                    messages.append(
                        {"role": "user", "content": CONTINUATION_PROMPT}
                    )
                print(
                    f"  \033[33m[max_tokens] continuation "
                    f"{state.continuation_count}/"
                    f"{runtime.config.max_continuations} with "
                    f"{runtime.config.escalated_max_tokens} tokens\033[0m"
                )
                continue
            print("  \033[31m[max_tokens] recovery limit reached\033[0m")
            _update_context(runtime)
            return

        messages.append({"role": "assistant", "content": response.content})
        if not _has_tool_use(response.content):
            force = runtime.hooks.trigger("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            if _wait_for_team_activity(runtime):
                continue
            extract_memories(runtime.memory, pre_compact_messages, summarize)
            consolidate_memories(runtime.memory, summarize)
            _update_context(runtime)
            return

        session.rounds_since_todo += 1
        results = []
        compacted_now = False
        for block in response.content:
            if _block_value(block, "type") != "tool_use":
                continue
            name = _block_value(block, "name")
            tool_input = _block_value(block, "input", {})
            tool_use_id = _block_value(block, "id")
            print(f"\033[36m> {name}\033[0m")
            if name == "compact":
                messages[:] = compact_history(runtime.config, summarize, messages)
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[Compacted. Continue with summarized context.]"
                        ),
                    }
                )
                compacted_now = True
                break

            blocked = runtime.hooks.trigger("PreToolUse", block)
            if blocked:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": str(blocked),
                    }
                )
                continue

            if should_run_background(name, tool_input):
                background_id = start_background_task(
                    runtime.background,
                    block,
                    handlers,
                    post_tool=lambda used_block, output: runtime.hooks.trigger(
                        "PostToolUse", used_block, output
                    ),
                    persist_output=lambda used_id, output: persist_large_output(
                        runtime.config, used_id, output
                    ),
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": (
                            f"[Background task {background_id} started] "
                            f"Command: {tool_input.get('command', '')}. "
                            "Result will be available when complete."
                        ),
                    }
                )
                continue

            output = execute_tool(block, handlers)
            runtime.hooks.trigger("PostToolUse", block, output)
            if name == "todo_write":
                session.rounds_since_todo = 0
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": output,
                }
            )

        if compacted_now:
            continue
        user_content = list(results)
        background_notifications = collect_background_results(runtime.background)
        user_content.extend(
            {"type": "text", "text": notification}
            for notification in background_notifications
        )
        print(
            f"  \033[32m[inject] {len(background_notifications)} "
            "background notification(s)\033[0m"
        )
        messages.append({"role": "user", "content": user_content})
