from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Protocol, cast

from redis import Redis


@dataclass(frozen=True, slots=True)
class MemoryJobEnvelope:
    job_id: str
    job_type: str
    dedupe_key: str


class MemoryQueue(Protocol):
    def enqueue(self, envelope: MemoryJobEnvelope) -> None: ...
    def dequeue(self) -> MemoryJobEnvelope | None: ...


class RedisMemoryQueue:
    def __init__(self, client: Redis, *, queue_name: str = "coding-deepgent:memory-jobs") -> None:
        self.client = client
        self.queue_name = queue_name

    def enqueue(self, envelope: MemoryJobEnvelope) -> None:
        self.client.rpush(self.queue_name, json.dumps(asdict(envelope)))

    def dequeue(self) -> MemoryJobEnvelope | None:
        item = cast(Any, self.client.lpop(self.queue_name))
        if item is None:
            return None
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        payload = json.loads(item)
        return MemoryJobEnvelope(**payload)


class InMemoryQueue:
    def __init__(self) -> None:
        self._items: Deque[MemoryJobEnvelope] = deque()

    def enqueue(self, envelope: MemoryJobEnvelope) -> None:
        self._items.append(envelope)

    def dequeue(self) -> MemoryJobEnvelope | None:
        if not self._items:
            return None
        return self._items.popleft()
