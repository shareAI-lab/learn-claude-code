from __future__ import annotations

from coding_deepgent import cli


def test_main_runs_one_integrated_prompt(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_once(prompt: str, *, history=None) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        return "done"

    monkeypatch.setattr(cli, "run_once", fake_run_once)

    assert cli.main(["--prompt", "continue"]) == 0
    output = capsys.readouterr().out.strip()

    assert captured == {"prompt": "continue", "history": None}
    assert output == "done"
