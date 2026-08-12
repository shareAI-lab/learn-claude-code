from homework.agent_app.features.worktrees import WorktreeState, create_worktree


def test_create_worktree_uses_injected_runner(tmp_path):
    calls = []
    state = WorktreeState(
        workdir=tmp_path,
        root=tmp_path / ".worktrees",
        run_git=lambda args: calls.append(args) or (True, "ok"),
    )

    result = create_worktree(state, "feature-a")

    assert "feature-a" in result
    assert calls[0][:2] == ["worktree", "add"]
