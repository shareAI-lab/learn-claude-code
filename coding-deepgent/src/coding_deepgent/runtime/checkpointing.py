from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

CheckpointerBackend = Literal["none", "memory"]
StoreBackend = Literal["none", "memory"]


def select_checkpointer(backend: CheckpointerBackend):
    if backend == "none":
        return None
    if backend == "memory":
        return InMemorySaver()
    raise ValueError(f"Unsupported checkpointer backend: {backend}")


def select_store(backend: StoreBackend):
    if backend == "none":
        return None
    if backend == "memory":
        return InMemoryStore()
    raise ValueError(f"Unsupported store backend: {backend}")
