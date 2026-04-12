from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers


class SessionsContainer(containers.DeclarativeContainer):
    session_store: Any = providers.Singleton(dict)
