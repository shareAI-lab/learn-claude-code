from homework.agent_app.config import AppConfig
from homework.agent_app.runtime import SessionState


def test_app_config_derives_all_paths_without_creating_them(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "primary")
    monkeypatch.setenv("FALLBACK_MODEL_ID", "fallback")

    config = AppConfig.from_env(tmp_path)

    assert config.workdir == tmp_path
    assert config.skills_dir == tmp_path / "skills"
    assert config.memory_dir == tmp_path / ".memory"
    assert config.task_dir == tmp_path / ".tasks"
    assert config.mailbox_dir == tmp_path / ".mailboxes"
    assert config.primary_model == "primary"
    assert config.fallback_model == "fallback"
    assert not config.memory_dir.exists()
    assert not config.task_dir.exists()
    assert not config.mailbox_dir.exists()


def test_session_state_is_fresh_per_instance():
    first = SessionState()
    second = SessionState()

    first.history.append({"role": "user", "content": "one"})

    assert second.history == []
    assert second.context == {}
    assert second.todos == []
