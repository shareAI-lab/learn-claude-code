"""
orchestrator.py — 七阶段编排器

触发 → 发现 → 分配 → 执行(Maker) → 验证(Checker) → 集成 → 持久化
"""

import time
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from config import MAX_CHECKER_RETRIES, WORKDIR
from loop_agent import _s20_code
from triggers import TriggerEvent, check_all_triggers, check_goal, _is_shell_command
from task_discovery import TaskItem, discover_from_trigger, filter_already_processed
from loop_agent import run_maker, run_checker, MakerResult, CheckerResult
from state import LoopState, load_state, save_state, record_cycle, mark_processed, add_error, remove_worktree


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class CycleResult:
    cycle_id: int
    task_id: str
    trigger_source: str
    maker_result: MakerResult | None = None
    checker_result: CheckerResult | None = None
    final_status: str = "pending"  # "approved" | "rejected" | "needs_human" | "skipped"
    feedback: str = ""
    duration: float = 0.0
    total_tokens: int = 0


# ── 编排逻辑 ──────────────────────────────────────────────

def _merge_worktree(worktree_name: str) -> bool:
    """将 worktree 的修改合并回主分支。

    Args:
        worktree_name: worktree 名称

    Returns:
        True if merge succeeded, False otherwise
    """
    if not worktree_name:
        return False
    wt_path = _s20_code.WORKTREES_DIR / worktree_name
    if not wt_path.exists():
        return False

    try:
        # 先在 worktree 中提交所有修改
        subprocess.run(
            ["git", "add", "-A"],
            cwd=wt_path, capture_output=True, timeout=30,
        )
        commit_result = subprocess.run(
            ["git", "commit", "-m", f"loop-agent: auto-commit from {worktree_name}"],
            cwd=wt_path, capture_output=True, text=True, timeout=30,
        )
        # 检查是否有实际修改可提交
        if "nothing to commit" in commit_result.stdout:
            print(f"\033[33m[Merge] No changes to merge from {worktree_name}\033[0m")
            return True

        # 获取 worktree 的分支名
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=wt_path, capture_output=True, text=True, timeout=30,
        )
        branch_name = branch_result.stdout.strip()
        if not branch_name:
            print(f"\033[33m[Merge] Could not determine branch name for {worktree_name}\033[0m")
            return False

        # 在主分支上合并 worktree 的分支
        merge_result = subprocess.run(
            ["git", "merge", branch_name, "--no-ff", "-m", f"loop-agent: merge {worktree_name}"],
            capture_output=True, text=True, timeout=30,
        )
        if merge_result.returncode == 0:
            print(f"\033[32m[Merge] Successfully merged {worktree_name} into main\033[0m")
            return True
        else:
            # 合并冲突，尝试 abort 并用 checkout 方式
            subprocess.run(["git", "merge", "--abort"], capture_output=True, timeout=30)
            # 直接从 worktree 复制修改的文件
            diff_result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", branch_name],
                capture_output=True, text=True, timeout=30,
            )
            if diff_result.returncode == 0 and diff_result.stdout.strip():
                # 从 worktree 分支 checkout 文件到主分支
                files = diff_result.stdout.strip().split("\n")
                for f in files:
                    subprocess.run(
                        ["git", "checkout", branch_name, "--", f],
                        capture_output=True, timeout=30,
                    )
                # 提交
                subprocess.run(["git", "add", "-A"], capture_output=True, timeout=30)
                subprocess.run(
                    ["git", "commit", "-m", f"loop-agent: apply changes from {worktree_name}"],
                    capture_output=True, timeout=30,
                )
                print(f"\033[32m[Merge] Applied changes from {worktree_name} via checkout\033[0m")
                return True
            print(f"\033[33m[Merge] No diff found between main and {branch_name}\033[0m")
            return False
    except Exception as e:
        print(f"\033[31m[Merge] Error merging {worktree_name}: {e}\033[0m")
        return False


def _cleanup_worktree(worktree_name: str, state: LoopState) -> None:
    """清理 worktree 目录。"""
    if not worktree_name:
        return
    wt_path = _s20_code.WORKTREES_DIR / worktree_name
    if wt_path.exists():
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt_path)],
                capture_output=True, timeout=30,
            )
            remove_worktree(state, worktree_name, _save=False)
        except Exception as e:
            print(f"\033[33m[Warning] Failed to cleanup worktree {worktree_name}: {e}\033[0m")


def orchestrate_cycle(event: TriggerEvent, state: LoopState) -> CycleResult:
    """
    执行一次完整的七阶段循环。

    Phase 1: TRIGGER   — 接收触发事件
    Phase 2: DISCOVER  — 转换为任务项，过滤已处理
    Phase 3: ALLOCATE  — 创建 worktree（在 maker 中完成）
    Phase 4: EXECUTE   — Maker 子代理实现代码
    Phase 5: VERIFY    — Checker 子代理审查代码
    Phase 6: INTEGRATE — approved→记录, rejected→反馈
    Phase 7: PERSIST   — 保存状态（单次原子写入）
    """
    start_time = time.time()
    cycle_id = len(state.history) + 1
    maker_result = None

    try:
        # Phase 2: DISCOVER
        task = discover_from_trigger(event)
        if task.id in state.processed_items:
            return CycleResult(
                cycle_id=cycle_id,
                task_id=task.id,
                trigger_source=event.source,
                final_status="skipped",
                feedback="Already processed",
                duration=time.time() - start_time,
            )

        print(f"\n\033[36m[Cycle {cycle_id}] Processing: {task.title}\033[0m")

        # Phase 4: EXECUTE (Maker)
        print(f"\033[33m[Maker] Starting implementation...\033[0m")
        maker_result = run_maker(
            task_description=task.description,
            branch_hint=task.branch_hint,
        )

        if not maker_result.success:
            add_error(state, task.id, maker_result.summary, _save=False)
            record_cycle(state, task.id, "needs_human", maker_result.summary, _save=False)
            return CycleResult(
                cycle_id=cycle_id,
                task_id=task.id,
                trigger_source=event.source,
                maker_result=maker_result,
                final_status="needs_human",
                feedback=maker_result.summary,
                duration=time.time() - start_time,
                total_tokens=maker_result.tokens_used or 0,
            )

        # Phase 5: VERIFY (Checker)
        print(f"\033[33m[Checker] Reviewing changes...\033[0m")
        checker_result = run_checker(maker_result)

        # Phase 6: INTEGRATE
        if checker_result.approved:
            # 合并 worktree 修改回主分支
            if maker_result.worktree_name:
                merged = _merge_worktree(maker_result.worktree_name)
                if not merged:
                    print(f"\033[33m[Warning] Merge failed, changes may be lost\033[0m")

            print(f"\033[32m[Approved] {checker_result.feedback[:100]}\033[0m")
            mark_processed(state, task.id, _save=False)
            record_cycle(state, task.id, "approved", checker_result.feedback, _save=False)
            return CycleResult(
                cycle_id=cycle_id,
                task_id=task.id,
                trigger_source=event.source,
                maker_result=maker_result,
                checker_result=checker_result,
                final_status="approved",
                feedback=checker_result.feedback,
                duration=time.time() - start_time,
                total_tokens=(maker_result.tokens_used or 0) + (checker_result.tokens_used or 0),
            )
        else:
            # 检查拒绝次数
            reject_count = sum(
                1 for h in state.history
                if h.get("task_id") == task.id and h.get("status") == "rejected"
            )

            if reject_count >= MAX_CHECKER_RETRIES:
                # 达到最大重试次数，标记需人工处理
                feedback = f"Rejected {MAX_CHECKER_RETRIES + 1} times. Last: {checker_result.feedback}"
                add_error(state, task.id, feedback, _save=False)
                record_cycle(state, task.id, "needs_human", feedback, _save=False)
                return CycleResult(
                    cycle_id=cycle_id,
                    task_id=task.id,
                    trigger_source=event.source,
                    maker_result=maker_result,
                    checker_result=checker_result,
                    final_status="needs_human",
                    feedback=feedback,
                    duration=time.time() - start_time,
                    total_tokens=(maker_result.tokens_used or 0) + (checker_result.tokens_used or 0),
                )
            else:
                # 记录拒绝，下次重试时注入反馈
                feedback = "; ".join(checker_result.issues) if checker_result.issues else checker_result.feedback
                record_cycle(state, task.id, "rejected", feedback, _save=False)
                return CycleResult(
                    cycle_id=cycle_id,
                    task_id=task.id,
                    trigger_source=event.source,
                    maker_result=maker_result,
                    checker_result=checker_result,
                    final_status="rejected",
                    feedback=feedback,
                    duration=time.time() - start_time,
                    total_tokens=(maker_result.tokens_used or 0) + (checker_result.tokens_used or 0),
                )
    finally:
        # Phase 7: PERSIST — 单次原子写入 + worktree 清理
        if maker_result:
            _cleanup_worktree(maker_result.worktree_name, state)
        save_state(state)


def run_loop(
    mode: str = "once",
    verify_command: str | None = None,
    max_cycles: int = 10,
) -> list[CycleResult]:
    """
    持续运行循环。

    Args:
        mode: "once" | "goal" | "daemon"
        verify_command: Goal 模式的验证命令
        max_cycles: 最大循环次数

    Returns:
        所有 cycle 结果
    """
    state = load_state()
    results = []

    try:
        for i in range(max_cycles):
            # 获取触发事件
            if mode == "goal" and verify_command:
                event = check_goal(verify_command)
                if event is None:
                    print("\033[32m[Goal] Condition met! Stopping.\033[0m")
                    break
            else:
                event = check_all_triggers()
                if event is None:
                    if mode == "once":
                        print("\033[33m[Once] No triggers. Stopping.\033[0m")
                        break
                    # daemon 模式：等待
                    time.sleep(1)
                    continue

            # 执行 cycle
            result = orchestrate_cycle(event, state)
            results.append(result)

            # 打印状态
            status_icon = {
                "approved": "\033[32mOK\033[0m",
                "rejected": "\033[31mFAIL\033[0m",
                "needs_human": "\033[33mHUMAN\033[0m",
                "skipped": "\033[90mSKIP\033[0m",
            }.get(result.final_status, "?")
            print(f"[Cycle {result.cycle_id}] {status_icon} {result.final_status} ({result.duration:.1f}s)")

            # approved 后停止（goal 模式下 checker 批准 = 目标达成）
            if result.final_status == "approved":
                if mode == "goal":
                    print("\033[32m[Goal] Task approved — goal achieved!\033[0m")
                break
            # needs_human → 停止（无论 goal 还是 once）
            if result.final_status == "needs_human":
                break
    except KeyboardInterrupt:
        print("\n\033[33m[Loop] Interrupted by user. Stopping.\033[0m")

    return results


def run_task(task_prompt: str, max_retries: int = 0) -> CycleResult:
    """
    直接执行单个任务（不经过触发器）。

    Args:
        task_prompt: 任务描述
        max_retries: 最大重试次数（0 = 使用 MAX_CHECKER_RETRIES）

    Returns:
        最后一次的 CycleResult
    """
    retries = max_retries if max_retries > 0 else MAX_CHECKER_RETRIES
    event = TriggerEvent(source="manual", prompt=task_prompt)
    state = load_state()
    result = None

    for attempt in range(retries + 1):
        result = orchestrate_cycle(event, state)

        # approved 或 needs_human → 停止
        if result.final_status in ("approved", "needs_human"):
            break

        # rejected → 重试（orchestrate_cycle 内部会跟踪拒绝次数）
        if result.final_status == "rejected" and attempt < retries:
            print(f"\033[33m[Loop] Rejected, retrying ({attempt + 1}/{retries})...\033[0m")
            continue

    return result
