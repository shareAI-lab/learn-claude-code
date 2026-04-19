from __future__ import annotations

from typing import Literal
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from .file_store import FileStore

CheckpointerBackend = Literal["none", "memory"]
StoreBackend = Literal["none", "memory", "file"]


def select_checkpointer(backend: CheckpointerBackend):
    if backend == "none":
        return None
    if backend == "memory":
        return InMemorySaver()
    raise ValueError(f"Unsupported checkpointer backend: {backend}")


def select_store(backend: StoreBackend, *, store_path: Path | None = None):
    if backend == "none":
        return None
    if backend == "memory":
        return InMemoryStore()
    if backend == "file":
        if store_path is None:
            raise ValueError("file store backend requires store_path")
        return FileStore(store_path)
    raise ValueError(f"Unsupported store backend: {backend}")
