from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import TextIO

from coding_deepgent.settings import Settings, load_settings

from coding_deepgent.frontend.producer import (
    BridgeSession,
    PermissionResumeRunner,
    PromptRunner,
    build_default_bridge_runners,
    build_default_prompt_runner,
    build_fake_bridge_runners,
)
from coding_deepgent.frontend.protocol import (
    FrontendEvent,
    parse_frontend_input,
    protocol_error_from_exception,
    serialize_frontend_event,
)


def run_jsonl_bridge(
    input_stream: Iterable[str],
    output_stream: TextIO,
    *,
    settings: Settings | None = None,
    prompt_runner: PromptRunner | None = None,
    permission_resume_runner: PermissionResumeRunner | None = None,
) -> None:
    active_settings = settings or load_settings()
    active_prompt_runner = prompt_runner
    active_permission_resume_runner = permission_resume_runner
    if active_prompt_runner is None and active_permission_resume_runner is None:
        (
            active_prompt_runner,
            active_permission_resume_runner,
        ) = build_default_bridge_runners(active_settings, hitl=True)
    session = BridgeSession(
        settings=active_settings,
        prompt_runner=active_prompt_runner or build_default_prompt_runner(active_settings),
        permission_resume_runner=active_permission_resume_runner,
    )
    for line in input_stream:
        if not line.strip():
            continue
        try:
            request = parse_frontend_input(line)
        except Exception as exc:
            _emit(output_stream, protocol_error_from_exception(exc))
            continue
        should_exit = session.handle(request, lambda event: _emit(output_stream, event))
        if should_exit:
            break


def run_stdio_bridge(*, fake: bool = False) -> None:
    if fake:
        runner, resume_runner = build_fake_bridge_runners()
        run_jsonl_bridge(
            sys.stdin,
            sys.stdout,
            prompt_runner=runner,
            permission_resume_runner=resume_runner,
        )
        return
    runner, resume_runner = build_default_bridge_runners(load_settings(), hitl=True)
    run_jsonl_bridge(
        sys.stdin,
        sys.stdout,
        prompt_runner=runner,
        permission_resume_runner=resume_runner,
    )


def _emit(output_stream: TextIO, event: FrontendEvent) -> None:
    output_stream.write(serialize_frontend_event(event) + "\n")
    output_stream.flush()
