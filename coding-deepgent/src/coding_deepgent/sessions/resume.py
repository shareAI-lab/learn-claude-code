from __future__ import annotations

from collections.abc import Callable, MutableMapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from .ports import SessionStore
from .records import LoadedSession


def apply_resume_state(
    runtime_state: MutableMapping[str, Any],
    loaded_session: LoadedSession,
) -> None:
    runtime_state.clear()
    runtime_state.update(deepcopy(loaded_session.state))


def resume_session(
    store: SessionStore,
    *,
    session_id: str,
    workdir: Path,
    runtime_state: MutableMapping[str, Any],
    default_state_factory: Callable[[], dict[str, Any]] | None = None,
) -> LoadedSession:
    loaded_session = store.load_session(
        session_id=session_id,
        workdir=workdir,
        default_state_factory=default_state_factory,
    )
    apply_resume_state(runtime_state, loaded_session)
    return loaded_session
