from homework.agent_app.features.memory import (
    MemoryStore,
    list_memory_files,
    read_memory_index,
    write_memory_file,
)
from homework.agent_app.features.skills import SkillState, scan_skills


def test_skill_scan_has_no_import_time_side_effect(tmp_path):
    state = SkillState(root=tmp_path / "skills")

    assert state.registry == {}
    assert not state.root.exists()


def test_skill_scan_populates_explicit_state(tmp_path):
    root = tmp_path / "skills"
    manifest = root / "review" / "SKILL.md"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "---\nname: review\ndescription: Review code\n---\n\nInstructions",
        encoding="utf-8",
    )
    state = SkillState(root=root)

    scan_skills(state)

    assert state.registry["review"]["content"].endswith("Instructions")


def test_memory_store_writes_and_indexes_under_its_root(tmp_path):
    store = MemoryStore(
        root=tmp_path / "memory",
        index_path=tmp_path / "memory" / "MEMORY.md",
    )

    path = write_memory_file(
        store,
        "project constraints",
        "project",
        "keep tests offline",
        "Never make live API calls in tests.",
    )

    assert path.is_relative_to(store.root)
    assert [item["filename"] for item in list_memory_files(store)] == [
        "project-constraints.md"
    ]
    assert "keep tests offline" in read_memory_index(store)
