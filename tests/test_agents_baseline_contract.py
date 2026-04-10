from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# This snapshot makes the handwritten `agents/*.py` teaching baseline explicit.
# If a future change intentionally revises the baseline, update the hashes in the
# same commit so the diff clearly shows that the teaching reference moved.
EXPECTED_BASELINE_SHA256 = {
    "agents/__init__.py": "3858b50108eb569a9347b6d63eba5b70a9e839875989c55d4f2bcd2bde7a46cd",
    "agents/s01_agent_loop.py": "f767394084f609c80d54ef500b8cbd558b8f2a86df301b275726a028bc47b9a3",
    "agents/s02_tool_use.py": "6a683a9d3f6176226173e335bd39c906f4fa16fffdda564f7350e6aa43fb807b",
    "agents/s03_todo_write.py": "d574586bee2122cf61fce8ae7ca0af552c1dd63b5900e90a01a1558f2dde6a4c",
    "agents/s04_subagent.py": "4f005f32d87b14b25c5605b7e87caca3f07c4f63d80381ddbe8f7491e7749020",
    "agents/s05_skill_loading.py": "ee4c3849db5379fb7f5d12f05d853b960797adfbde0bd4e089ef2754ac2e95e2",
    "agents/s06_context_compact.py": "2fde97749962daf9d34e8cacc4469e4d916b10243247ba9c2ffe9e07e2e8430c",
    "agents/s07_permission_system.py": "da5995910fda061cf9471f2dd1dc9322840e5e16a38f545c6a84b7e5896c0e22",
    "agents/s08_hook_system.py": "6ff869c7d5d003f01b02ba84687e3a6053a6c314923dad1d8c4f48de78bc9ccd",
    "agents/s09_memory_system.py": "7b6186774149879dd727347c0ecaf4010e62f765e089b43774f84966abdf1c16",
    "agents/s10_system_prompt.py": "b02560b9bbaea8907d1316ac104bd8e7dcfb7abccbbc38fb623c0f192388e15d",
    "agents/s11_error_recovery.py": "05729b2b75a24cb79e1bb8f7c121ed6e8c96da6f1432545dac091f780c30254a",
    "agents/s12_task_system.py": "b002c0e771b0402ba10150ccf02d7b93e8c0e7a6414823e6e7c2ae855e5400e7",
    "agents/s13_background_tasks.py": "3ca96351975f8755dd4ec47245f7cf51d779c1a9fb043573115ad53743a1ccbc",
    "agents/s14_cron_scheduler.py": "165f9f9b010fa31b897f20f0c9f0b37ba42674cb29bd25e4ec3d9c561e9d9d5a",
    "agents/s15_agent_teams.py": "15799489adb7edc68a810351cc281bf5ac4641f46c0e8a491bcad9a4a544caf4",
    "agents/s16_team_protocols.py": "e4830a68fd733f4dd709edf27303712dfd7517da13b26d773ec21cfe4b77cfa9",
    "agents/s17_autonomous_agents.py": "f847b6dbebf3a90a7ec8ff57b3a8db50f7d199331e635ed3a998b9fd0cf212d2",
    "agents/s18_worktree_task_isolation.py": "310a5f0dc334c960aa6210979d86178f7ea2e0f050b5010584299a240f25e758",
    "agents/s19_mcp_plugin.py": "eb7f7e7019de840f82767a673b4630430c0f41355e0e798a4270908b191af0e2",
    "agents/s_full.py": "854efdcdc4372da4d0dc4eed3baa0cf2348d21ae97489506d8c11cd27894a9b2",
}


def sha256_for(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_agents_baseline_files_still_exist() -> None:
    actual_files = {
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "agents").glob("*.py"))
    }
    assert actual_files == set(EXPECTED_BASELINE_SHA256)


def test_agents_baseline_hashes_have_not_changed() -> None:
    mismatches: list[str] = []
    for relative_path, expected_hash in EXPECTED_BASELINE_SHA256.items():
        actual_hash = sha256_for(ROOT / relative_path)
        if actual_hash != expected_hash:
            mismatches.append(
                f"{relative_path}: expected {expected_hash}, got {actual_hash}"
            )

    assert not mismatches, "Handwritten agents baseline changed:\n" + "\n".join(mismatches)
