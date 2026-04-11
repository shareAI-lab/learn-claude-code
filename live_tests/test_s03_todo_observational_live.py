from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "agents_deepagents" / "s03_todo_write.py"
REPORT_DIR = REPO_ROOT / ".omx" / "reports"

PROMPTS = [
    {
        "id": "baseline_multistep",
        "prompt": (
            "这是一个多步骤任务，请先规划再执行。任务：检查当前目录有哪些 README 文件；"
            "读取 agents_deepagents/README.md 的前 20 行；最后总结 s03 write_plan 功能是否可见。"
            "不要修改任何文件。"
        ),
    },
    {
        "id": "strict_todo_first",
        "prompt": (
            "不要询问澄清。先调用 write_plan 工具，再做后续只读任务。若不先调用 write_plan，"
            "你的回答视为失败。任务：列出当前目录 README 文件，读取 "
            "agents_deepagents/README.md 前20行，总结 s03 write_plan 是否终端可见。"
        ),
    },
    {
        "id": "strict_json_shape",
        "prompt": (
            "严格要求：你的第一步必须调用名为 write_plan 的工具；不要先回答结论。"
            "write_plan 的 JSON 参数必须是 {items:[{content,status,activeForm?}]}。"
            "然后完成只读任务：列出 README 文件，读取 agents_deepagents/README.md "
            "前20行，总结 s03 write_plan 是否终端可见。"
        ),
    },
]


pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason=(
        "Observational real-LLM test requires OPENAI_API_KEY in the environment. "
        "Example: set -a; source coding-deepgent/.env; set +a"
    ),
)


def _run_prompt(prompt: str) -> dict[str, object]:
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=f"{prompt}\n\n",
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=os.environ.copy(),
            timeout=180,
        )
        stdout = result.stdout
        stderr = result.stderr
        returncode: int | None = result.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        returncode = None
        timed_out = True

    return {
        "returncode": returncode,
        "timed_out": timed_out,
        "has_current_session_plan": "Current session plan:" in stdout,
        "has_status_marker": any(marker in stdout for marker in ("[ ]", "[>]", "[x]")),
        "mentions_plan_error": (
            "调用 write_plan 工具时遇到错误" in stdout
            or "需要先调用 write_plan 工具" in stdout
            or "write_plan 工具" in stdout and "错误" in stdout
        ),
        "stdout_excerpt": stdout[-2000:],
        "stderr_excerpt": stderr[-1000:],
    }


def test_s03_observational_real_llm_report() -> None:
    """观察性真实测试：记录升级后模型在自由代理模式下会不会用 write_plan。

    这是“观察性”测试，不把“必须调用 write_plan”写死成断言。
    它的目标是：
    1. 用真实模型跑几组 prompt；
    2. 记录终端是否出现 `Current session plan:`；
    3. 记录是否出现工具相关错误提示；
    4. 输出一份 JSON 报告，便于后续比较不同模型/提示词。
    """

    observations: list[dict[str, object]] = []
    for case in PROMPTS:
        observation = {"id": case["id"], **_run_prompt(case["prompt"])}
        observations.append(observation)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / (
        f"s03-write-plan-observational-live-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    report = {
        "script": str(SCRIPT.relative_to(REPO_ROOT)),
        "model": os.getenv("OPENAI_MODEL", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", ""),
        "observations": observations,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # 这条测试只保证“真实调用过程（含超时观测）和报告落盘”完成，
    # 不把模型行为本身固定成硬断言。
    assert len(observations) == len(PROMPTS)
    assert report_path.exists()

    print(f"\n[observational-report] {report_path}")
    for item in observations:
        print(
            f"[{item['id']}] timeout={item['timed_out']} "
            f"plan={item['has_current_session_plan']} "
            f"markers={item['has_status_marker']} "
            f"plan_error={item['mentions_plan_error']}"
        )
