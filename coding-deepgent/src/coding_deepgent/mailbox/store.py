from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from coding_deepgent.event_stream import append_event

MAILBOX_NAMESPACE = ("coding_deepgent_mailbox",)
MessageStatus = Literal["pending", "acked", "cancelled"]


class MailboxStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class MailboxMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    sender: str = Field(..., min_length=1)
    recipient: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    status: MessageStatus = "pending"
    delivery_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    acked_at: str | None = None


def send_message(
    store: MailboxStore,
    *,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    delivery_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MailboxMessage:
    if delivery_key:
        existing = _message_by_delivery_key(store, delivery_key)
        if existing is not None:
            return existing
    created_at = _now()
    message = MailboxMessage(
        message_id=_message_id(sender=sender, recipient=recipient, created_at=created_at),
        sender=sender.strip(),
        recipient=recipient.strip(),
        subject=subject.strip(),
        body=body.strip(),
        delivery_key=delivery_key,
        metadata=metadata or {},
        created_at=created_at,
    )
    store.put(MAILBOX_NAMESPACE, message.message_id, message.model_dump())
    append_event(
        store,
        stream_id=f"mailbox:{message.recipient}",
        kind="mailbox_message_sent",
        payload=message.model_dump(),
    )
    return message


def get_message(store: MailboxStore, message_id: str) -> MailboxMessage:
    item = store.get(MAILBOX_NAMESPACE, message_id)
    if item is None:
        raise KeyError(f"Unknown mailbox message: {message_id}")
    return MailboxMessage.model_validate(_item_value(item))


def list_messages(
    store: MailboxStore,
    *,
    recipient: str | None = None,
    status: MessageStatus | None = None,
) -> list[MailboxMessage]:
    records = [
        MailboxMessage.model_validate(_item_value(item))
        for item in store.search(MAILBOX_NAMESPACE)
    ]
    if recipient is not None:
        records = [record for record in records if record.recipient == recipient]
    if status is not None:
        records = [record for record in records if record.status == status]
    return sorted(records, key=lambda record: record.created_at)


def ack_message(store: MailboxStore, message_id: str) -> MailboxMessage:
    message = get_message(store, message_id)
    updated = message.model_copy(update={"status": "acked", "acked_at": _now()})
    store.put(MAILBOX_NAMESPACE, updated.message_id, updated.model_dump())
    append_event(
        store,
        stream_id=f"mailbox:{updated.recipient}",
        kind="mailbox_message_acked",
        payload={"message_id": updated.message_id},
    )
    return updated


def _message_by_delivery_key(
    store: MailboxStore,
    delivery_key: str,
) -> MailboxMessage | None:
    for message in list_messages(store):
        if message.delivery_key == delivery_key:
            return message
    return None


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _message_id(*, sender: str, recipient: str, created_at: str) -> str:
    digest = sha256(f"{sender}\0{recipient}\0{created_at}".encode("utf-8")).hexdigest()
    return f"msg-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
