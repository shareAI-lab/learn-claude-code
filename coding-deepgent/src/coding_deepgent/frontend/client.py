from __future__ import annotations

import queue
import threading
from collections.abc import Generator

from coding_deepgent.settings import Settings, load_settings

from .producer import (
    BridgeSession,
    PermissionResumeRunner,
    PromptRunner,
    build_default_bridge_runners,
    build_default_prompt_runner,
    build_fake_bridge_runners,
    build_fake_prompt_runner,
)
from .protocol import FrontendEvent, FrontendInput, SubmitPromptInput


class FrontendClient:
    """Embedded Python client for frontend events.

    This client consumes the same `FrontendEvent` contract as the React/Ink CLI
    without going through the JSONL transport. It is intended for tests,
    scripts, and future non-HTTP adapters.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        prompt_runner: PromptRunner | None = None,
        permission_resume_runner: PermissionResumeRunner | None = None,
        fake: bool = False,
    ) -> None:
        active_settings = settings or load_settings()
        runner = prompt_runner
        resume_runner = permission_resume_runner
        if runner is None and resume_runner is None:
            if fake:
                runner, resume_runner = build_fake_bridge_runners()
            else:
                runner, resume_runner = build_default_bridge_runners(
                    active_settings, hitl=True
                )
        active_runner = runner or (
            build_fake_prompt_runner()
            if fake
            else build_default_prompt_runner(active_settings)
        )
        self._session = BridgeSession(
            settings=active_settings,
            prompt_runner=active_runner,
            permission_resume_runner=resume_runner,
        )
        self._lock = threading.Lock()

    def send(self, request: FrontendInput) -> Generator[FrontendEvent, None, None]:
        """Send one frontend input and yield resulting events synchronously."""
        with self._lock:
            yield from _stream_session_events(self._session, request)

    def stream_prompt(self, prompt: str) -> Generator[FrontendEvent, None, None]:
        """Convenience wrapper around `send({"type":"submit_prompt", ...})`."""
        yield from self.send(SubmitPromptInput(text=prompt))

    def chat(self, prompt: str) -> str:
        """Run one prompt and return the final assistant text."""
        final_text = ""
        for event in self.stream_prompt(prompt):
            if event.type == "assistant_message":
                final_text = event.text
        return final_text


def _stream_session_events(
    session: BridgeSession,
    request: FrontendInput,
) -> Generator[FrontendEvent, None, None]:
    events: queue.Queue[FrontendEvent | Exception | None] = queue.Queue()

    def worker() -> None:
        try:
            session.handle(request, lambda event: events.put(event))
        except Exception as exc:  # pragma: no cover - defensive background propagation
            events.put(exc)
        finally:
            events.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    while True:
        item = events.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item
    thread.join()
