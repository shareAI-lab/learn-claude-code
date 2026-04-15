from __future__ import annotations

from pathlib import Path
from typing import Any

from coding_deepgent.sessions.contributions import (
    CompactAssistContribution,
    CompactSummaryUpdateContribution,
    RecoveryBriefContribution,
    RecoveryBriefSection,
    RuntimeStateContribution,
    apply_compact_summary_update_contributions,
    build_recovery_brief_sections,
    coerce_runtime_state_contributions,
    compact_assist_text,
)
from coding_deepgent.sessions.records import (
    CompactedHistorySource,
    LoadedSession,
    SessionContext,
    SessionSummary,
)
from coding_deepgent.sessions.session_memory import (
    SESSION_MEMORY_STATE_KEY,
    compact_summary_update_contribution,
    should_refresh_session_memory,
    session_memory_metrics,
)


def _loaded_session(state: dict[str, Any] | None = None) -> LoadedSession:
    workdir = Path("/tmp/work")
    return LoadedSession(
        context=SessionContext(
            session_id="session-1",
            workdir=workdir,
            store_dir=Path("/tmp/store"),
            transcript_path=Path("/tmp/store/session-1.jsonl"),
        ),
        history=[{"role": "user", "content": "hello"}],
        compacted_history=[{"role": "user", "content": "hello"}],
        compacted_history_source=CompactedHistorySource(
            mode="raw",
            reason="no_compacts",
            compact_index=None,
        ),
        state=state or {},
        evidence=[],
        compacts=[],
        summary=SessionSummary(
            session_id="session-1",
            workdir=workdir,
            transcript_path=Path("/tmp/store/session-1.jsonl"),
            created_at="2026-04-15T00:00:00Z",
            updated_at="2026-04-15T00:00:00Z",
            first_prompt="hello",
            message_count=1,
        ),
    )


def test_runtime_state_contributions_coerce_only_valid_values() -> None:
    contributions = (
        RuntimeStateContribution(
            key="valid",
            coerce=lambda state: state.get("valid") if state.get("valid") else None,
        ),
        RuntimeStateContribution(key="missing", coerce=lambda state: None),
    )

    assert coerce_runtime_state_contributions(
        {"valid": {"ok": True}},
        contributions,
    ) == {"valid": {"ok": True}}


def test_recovery_brief_contributions_skip_empty_sections() -> None:
    contributions = (
        RecoveryBriefContribution(
            name="empty",
            render=lambda loaded: None,
        ),
        RecoveryBriefContribution(
            name="visible",
            render=lambda loaded: RecoveryBriefSection(
                title="Visible:",
                lines=("- one",),
            ),
        ),
    )

    assert build_recovery_brief_sections(
        _loaded_session(),
        contributions,
    ) == (RecoveryBriefSection(title="Visible:", lines=("- one",)),)


def test_compact_assist_contributions_join_non_blank_text() -> None:
    contributions = (
        CompactAssistContribution(name="blank", render=lambda loaded: " "),
        CompactAssistContribution(name="first", render=lambda loaded: "First assist."),
        CompactAssistContribution(name="none", render=lambda loaded: None),
        CompactAssistContribution(name="second", render=lambda loaded: "Second assist."),
    )

    assert (
        compact_assist_text(_loaded_session(), contributions)
        == "First assist.\n\nSecond assist."
    )


def test_compact_summary_update_contributions_report_updated_names() -> None:
    seen: list[str] = []

    def update(loaded: LoadedSession, summary: str) -> bool:
        del loaded
        seen.append(summary)
        return True

    contributions = (
        CompactSummaryUpdateContribution(
            name="skip",
            update=lambda loaded, summary: False,
        ),
        CompactSummaryUpdateContribution(
            name="update",
            update=update,
        ),
    )

    assert apply_compact_summary_update_contributions(
        _loaded_session(),
        summary="Generated summary.",
        contributions=contributions,
    ) == ("update",)
    assert seen == ["Generated summary."]


def test_session_memory_refresh_policy_detects_missing_and_stale_artifacts() -> None:
    assert should_refresh_session_memory({}, current_message_count=1)
    assert should_refresh_session_memory(
        {
            SESSION_MEMORY_STATE_KEY: {
                "content": "old",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            }
        },
        current_message_count=5,
    )
    assert not should_refresh_session_memory(
        {
            SESSION_MEMORY_STATE_KEY: {
                "content": "recent",
                "source": "manual",
                "message_count": 4,
                "updated_at": "2026-04-15T00:00:00Z",
            }
        },
        current_message_count=5,
    )


def test_session_memory_refresh_policy_uses_token_and_tool_call_pressure() -> None:
    state = {
        SESSION_MEMORY_STATE_KEY: {
            "content": "recent",
            "source": "manual",
            "message_count": 10,
            "token_count": 100,
            "tool_call_count": 1,
            "updated_at": "2026-04-15T00:00:00Z",
        }
    }

    assert should_refresh_session_memory(
        state,
        current_message_count=10,
        current_token_count=5100,
        current_tool_call_count=1,
    )
    assert should_refresh_session_memory(
        state,
        current_message_count=10,
        current_token_count=100,
        current_tool_call_count=4,
    )
    assert not should_refresh_session_memory(
        state,
        current_message_count=10,
        current_token_count=200,
        current_tool_call_count=2,
    )


def test_session_memory_metrics_estimates_tokens_and_tool_calls() -> None:
    metrics = session_memory_metrics(
        [
            {"role": "user", "content": "abcd"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "abcdefgh"},
                    {"type": "tool_use", "id": "tool-1"},
                ],
            },
            {"role": "assistant", "content": "", "tool_calls": [{"name": "demo"}]},
        ]
    )

    assert metrics.message_count == 3
    assert metrics.estimated_token_count == 3
    assert metrics.tool_call_count == 2


def test_session_memory_compact_summary_update_provider_refreshes_state() -> None:
    loaded = _loaded_session()

    assert compact_summary_update_contribution().update(
        loaded,
        "Generated compact summary.",
    )

    assert loaded.state[SESSION_MEMORY_STATE_KEY]["content"] == (
        "Generated compact summary."
    )
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["source"] == "generated_compact"
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["message_count"] == 1
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["token_count"] == 2
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["tool_call_count"] == 0


def test_session_memory_compact_summary_update_provider_skips_recent_state() -> None:
    loaded = _loaded_session(
        {
            SESSION_MEMORY_STATE_KEY: {
                "content": "Recent memory.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            }
        }
    )

    assert not compact_summary_update_contribution().update(
        loaded,
        "Generated compact summary.",
    )
    assert loaded.state[SESSION_MEMORY_STATE_KEY]["content"] == "Recent memory."
