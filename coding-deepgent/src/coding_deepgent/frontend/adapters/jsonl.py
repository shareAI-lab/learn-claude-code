from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import TextIO

from coding_deepgent.settings import Settings, load_settings

from coding_deepgent.frontend.producer import (
    BridgeSession,
    PromptRunner,
    build_default_prompt_runner,
    build_fake_prompt_runner,
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
) -> None:
    active_settings = settings or load_settings()
    session = BridgeSession(
        settings=active_settings,
        prompt_runner=prompt_runner or build_default_prompt_runner(active_settings),
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
    runner = build_fake_prompt_runner() if fake else None
    run_jsonl_bridge(sys.stdin, sys.stdout, prompt_runner=runner)


def _emit(output_stream: TextIO, event: FrontendEvent) -> None:
    output_stream.write(serialize_frontend_event(event) + "\n")
    output_stream.flush()

