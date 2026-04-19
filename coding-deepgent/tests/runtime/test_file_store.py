from __future__ import annotations

from pathlib import Path

from coding_deepgent.runtime import FileStore, select_store
from coding_deepgent.settings import Settings


def test_file_store_roundtrips_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "store.json"
    first = FileStore(path)
    first.put(("tasks",), "task-1", {"title": "Implement"})

    second = FileStore(path)
    item = second.get(("tasks",), "task-1")
    results = second.search(("tasks",))

    assert item is not None
    assert item.value == {"title": "Implement"}
    assert len(results) == 1
    assert results[0].key == "task-1"
    assert results[0].value["title"] == "Implement"


def test_file_store_delete_and_namespace_listing(tmp_path: Path) -> None:
    store = FileStore(tmp_path / "store.json")
    store.put(("tasks", "active"), "task-1", {"title": "Implement"})
    store.put(("plans",), "plan-1", {"title": "Plan"})

    namespaces = store.list_namespaces(prefix=("tasks",))
    store.delete(("tasks", "active"), "task-1")

    assert namespaces == [("tasks", "active")]
    assert store.get(("tasks", "active"), "task-1") is None


def test_select_store_file_backend_uses_store_path(tmp_path: Path) -> None:
    store = select_store("file", store_path=tmp_path / "store.json")

    assert isinstance(store, FileStore)


def test_settings_default_store_backend_is_file_and_path_is_project_relative(
    tmp_path: Path,
) -> None:
    settings = Settings(workdir=tmp_path)

    assert settings.store_backend == "file"
    assert settings.store_path == (tmp_path / ".coding-deepgent" / "store.json").resolve()
