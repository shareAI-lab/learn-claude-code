from __future__ import annotations

from langgraph.store.memory import InMemoryStore

from coding_deepgent.continuity import get_artifact, list_artifacts, save_artifact
from coding_deepgent.event_stream import ack_event, append_event, list_events
from coding_deepgent.extension_lifecycle import (
    disable_extension,
    enable_extension,
    register_extension,
    rollback_extension,
)
from coding_deepgent.mailbox import ack_message, list_messages, send_message
from coding_deepgent.remote import (
    close_remote_session,
    register_remote_session,
    replay_remote_events,
    send_remote_control,
)
from coding_deepgent.teams import assign_worker, complete_team, create_team
from coding_deepgent.worker_runtime import (
    complete_worker,
    create_worker,
    heartbeat_worker,
    request_worker_stop,
)


def test_event_stream_appends_replays_and_acks() -> None:
    store = InMemoryStore()

    first = append_event(store, stream_id="session-1", kind="started")
    second = append_event(store, stream_id="session-1", kind="progress")
    acked = ack_event(store, stream_id="session-1", event_id=first.event_id)

    assert [event.sequence for event in list_events(store, stream_id="session-1")] == [
        1,
        2,
    ]
    assert list_events(store, stream_id="session-1", after_sequence=1)[0].event_id == second.event_id
    assert acked.acked is True


def test_worker_runtime_records_heartbeat_stop_and_completion() -> None:
    store = InMemoryStore()

    worker = create_worker(store, kind="assistant", session_id="session-1")
    running = heartbeat_worker(store, worker.worker_id)
    stopping = request_worker_stop(store, worker.worker_id)
    completed = complete_worker(store, worker.worker_id, result_summary="done")

    assert running.status == "running"
    assert stopping.stop_requested is True
    assert completed.status == "completed"


def test_mailbox_send_is_idempotent_and_ackable() -> None:
    store = InMemoryStore()

    first = send_message(
        store,
        sender="coordinator",
        recipient="worker-1",
        subject="task",
        body="do it",
        delivery_key="delivery-1",
    )
    second = send_message(
        store,
        sender="coordinator",
        recipient="worker-1",
        subject="task",
        body="do it",
        delivery_key="delivery-1",
    )
    acked = ack_message(store, first.message_id)

    assert first.message_id == second.message_id
    assert acked.status == "acked"
    assert len(list_messages(store, recipient="worker-1")) == 1


def test_team_remote_extension_and_continuity_records() -> None:
    store = InMemoryStore()

    worker = create_worker(store, kind="assistant", session_id="session-1")
    team = create_team(store, title="Ship feature")
    team = assign_worker(store, team_id=team.team_id, worker_id=worker.worker_id)
    team = complete_team(store, team_id=team.team_id, summary="done")
    remote = register_remote_session(
        store,
        session_id="session-1",
        client_name="ide",
    )
    event = send_remote_control(store, remote_id=remote.remote_id, command="stop")
    extension = register_extension(
        store,
        name="demo",
        kind="plugin",
        source="local",
    )
    enabled = enable_extension(store, extension.extension_id)
    disabled = disable_extension(store, extension.extension_id)
    rolled_back = rollback_extension(store, extension.extension_id)
    artifact = save_artifact(
        store,
        title="Next step",
        content="Continue implementation.",
        session_id="session-1",
    )

    assert team.status == "completed"
    assert replay_remote_events(store, remote_id=remote.remote_id)[-1].event_id == event.event_id
    assert close_remote_session(store, remote.remote_id).status == "closed"
    assert enabled.status == "enabled"
    assert disabled.status == "disabled"
    assert rolled_back.status == "enabled"
    assert get_artifact(store, artifact.artifact_id).title == "Next step"
    assert list_artifacts(store)[0].artifact_id == artifact.artifact_id
