from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    MatchCondition,
    Op,
    PutOp,
    Result,
    SearchItem,
    SearchOp,
)


@dataclass(frozen=True, slots=True)
class _StoredValue:
    value: dict[str, Any]
    created_at: str
    updated_at: str


class FileStore(BaseStore):
    """Small JSON-backed LangGraph store for local durable task/plan state."""

    _locks: dict[Path, RLock] = {}

    def __init__(self, path: Path) -> None:
        self._path = path.expanduser().resolve()
        self._lock = self._locks.setdefault(self._path, RLock())

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        with self._lock:
            payload = self._load_payload()
            results: list[Result] = []
            dirty = False
            for op in ops:
                if isinstance(op, GetOp):
                    results.append(self._get(payload, op))
                    continue
                if isinstance(op, SearchOp):
                    results.append(self._search(payload, op))
                    continue
                if isinstance(op, ListNamespacesOp):
                    results.append(self._list_namespaces(payload, op))
                    continue
                if isinstance(op, PutOp):
                    self._put(payload, op)
                    results.append(None)
                    dirty = True
                    continue
                raise TypeError(f"Unsupported store op: {type(op).__name__}")
            if dirty:
                self._save_payload(payload)
            return results

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        return self.batch(ops)

    def _get(self, payload: dict[str, Any], op: GetOp) -> Item | None:
        namespace_key = _namespace_key(op.namespace)
        records = payload.get("records", {})
        namespace_records = records.get(namespace_key, {})
        raw = namespace_records.get(op.key)
        if not isinstance(raw, dict):
            return None
        stored = _coerce_stored_value(raw)
        if stored is None:
            return None
        return Item(
            namespace=op.namespace,
            key=op.key,
            value=stored.value,
            created_at=_parse_timestamp(stored.created_at),
            updated_at=_parse_timestamp(stored.updated_at),
        )

    def _search(self, payload: dict[str, Any], op: SearchOp) -> list[SearchItem]:
        matched: list[SearchItem] = []
        records = payload.get("records", {})
        for namespace_key, namespace_records in records.items():
            namespace = _split_namespace_key(namespace_key)
            if not _has_prefix(namespace, op.namespace_prefix):
                continue
            if not isinstance(namespace_records, dict):
                continue
            for key, raw in namespace_records.items():
                if not isinstance(key, str):
                    continue
                stored = _coerce_stored_value(raw)
                if stored is None or not _matches_filter(stored.value, op.filter):
                    continue
                matched.append(
                    SearchItem(
                        namespace=namespace,
                        key=key,
                        value=stored.value,
                        created_at=_parse_timestamp(stored.created_at),
                        updated_at=_parse_timestamp(stored.updated_at),
                        score=None,
                    )
                )
        matched.sort(key=lambda item: (item.namespace, item.key))
        return matched[op.offset : op.offset + op.limit]

    def _list_namespaces(
        self,
        payload: dict[str, Any],
        op: ListNamespacesOp,
    ) -> list[tuple[str, ...]]:
        candidates: set[tuple[str, ...]] = set()
        records = payload.get("records", {})
        for namespace_key in records:
            if not isinstance(namespace_key, str):
                continue
            namespace = _split_namespace_key(namespace_key)
            if not _matches_namespace_conditions(namespace, op.match_conditions):
                continue
            if op.max_depth is not None:
                namespace = namespace[: op.max_depth]
            candidates.add(namespace)
        ordered = sorted(candidates)
        return ordered[op.offset : op.offset + op.limit]

    def _put(self, payload: dict[str, Any], op: PutOp) -> None:
        records = payload.setdefault("records", {})
        namespace_key = _namespace_key(op.namespace)
        namespace_records = records.setdefault(namespace_key, {})
        if op.value is None:
            if isinstance(namespace_records, dict):
                namespace_records.pop(op.key, None)
            if not namespace_records:
                records.pop(namespace_key, None)
            return
        now = _timestamp_now()
        raw_existing = namespace_records.get(op.key) if isinstance(namespace_records, dict) else None
        existing = _coerce_stored_value(raw_existing) if isinstance(raw_existing, dict) else None
        namespace_records[op.key] = {
            "value": json.loads(json.dumps(op.value)),
            "created_at": existing.created_at if existing is not None else now,
            "updated_at": now,
        }

    def _load_payload(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"records": {}}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid file store payload: {self._path}") from exc
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid file store payload: {self._path}")
        records = raw.get("records", {})
        if not isinstance(records, dict):
            raise RuntimeError(f"Invalid file store records: {self._path}")
        return {"records": records}

    def _save_payload(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )


def _namespace_key(namespace: tuple[str, ...]) -> str:
    return "\u241f".join(namespace)


def _split_namespace_key(namespace_key: str) -> tuple[str, ...]:
    if not namespace_key:
        return ()
    return tuple(namespace_key.split("\u241f"))


def _coerce_stored_value(raw: object) -> _StoredValue | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    created_at = raw.get("created_at")
    updated_at = raw.get("updated_at")
    if not isinstance(value, dict):
        return None
    if not isinstance(created_at, str) or not isinstance(updated_at, str):
        return None
    return _StoredValue(value=value, created_at=created_at, updated_at=updated_at)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _timestamp_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _has_prefix(namespace: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return namespace[: len(prefix)] == prefix


def _matches_filter(value: dict[str, Any], expected: dict[str, Any] | None) -> bool:
    if not expected:
        return True
    return all(value.get(key) == candidate for key, candidate in expected.items())


def _matches_namespace_conditions(
    namespace: tuple[str, ...],
    conditions: tuple[MatchCondition, ...] | None,
) -> bool:
    if not conditions:
        return True
    return all(_matches_namespace_condition(namespace, condition) for condition in conditions)


def _matches_namespace_condition(
    namespace: tuple[str, ...],
    condition: MatchCondition,
) -> bool:
    path = tuple(str(part) for part in condition.path)
    if condition.match_type == "prefix":
        return _matches_namespace_pattern(namespace[: len(path)], path)
    if condition.match_type == "suffix":
        return _matches_namespace_pattern(namespace[-len(path) :], path)
    return False


def _matches_namespace_pattern(
    namespace: tuple[str, ...],
    pattern: tuple[str, ...],
) -> bool:
    if len(namespace) != len(pattern):
        return False
    return all(target == candidate or candidate == "*" for target, candidate in zip(namespace, pattern, strict=True))
