#!/usr/bin/env python3
"""
main.py — Loop Engineering Agent 入口

三种模式：
  REPL（默认）— 交互式命令行
  --once      — 单次执行（Maker-Checker 流水线）
  --goal      — 目标模式（持续运行直到验证通过）

REPL 命令:
  /loop <task>         — 通过 Maker-Checker 流水线执行任务
  /goal <cmd>          — 设置目标，持续运行直到验证通过
  /status              — 显示状态
  cron: <expr> <prompt> — 添加 cron 任务
  quit                 — 退出
  其他文本              — 直接对话（s20 全部能力）
"""

import sys
import argparse
from pathlib import Path

# 确保 loop-agent 目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from config import validate_config
from loop_agent import chat, init_context, run_maker, run_checker
from orchestrator import run_loop, run_task
from state import load_state


def repl():
    """交互式 REPL。"""
    print("\033[36mLoop Engineering Agent — REPL\033[0m")
    print("Commands:")
    print("  /loop <task>         — Maker-Checker pipeline")
    print("  /goal <cmd>          — Loop until verification passes")
    print("  /status              — Show state")
    print("  cron: <expr> <prompt> — Add cron job")
    print("  quit                 — Exit")
    print("  Other text           — Direct chat (full s20 capabilities)\n")

    # 初始化上下文和消息历史
    messages = []
    context = init_context()

    while True:
        try:
            query = input("\033[36mloop-agent >> \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue

        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # /status — 显示状态
        if query.lower() == "/status":
            state = load_state()
            print(f"Processed items: {len(state.processed_items)}")
            print(f"History entries: {len(state.history)}")
            print(f"Active worktrees: {len(state.active_worktrees)}")
            print(f"Error log: {len(state.error_log)}")
            print(f"Message history: {len(messages)} messages")
            continue

        # /loop <task> — Maker-Checker 流水线
        if query.startswith("/loop "):
            task_prompt = query[6:].strip()
            if not task_prompt:
                print("Usage: /loop <task>")
                continue
            print(f"\033[33m[Loop] Running Maker-Checker pipeline...\033[0m")
            result = run_task(task_prompt)
            print(f"\n[{result.final_status}] {result.feedback[:300]}")
            if result.maker_result:
                print(f"  Diff: {result.maker_result.diff_stat[:100]}")
            continue

        # /goal <cmd> — 目标模式
        if query.startswith("/goal "):
            verify_cmd = query[6:].strip()
            if not verify_cmd:
                print("Usage: /goal <verify_command>")
                continue
            print(f"\033[33m[Goal mode] Running until: {verify_cmd}\033[0m")
            results = run_loop(mode="goal", verify_command=verify_cmd, max_cycles=30)
            print(f"\nGoal mode completed. {len(results)} cycles executed.")
            continue

        # cron: <expr> <prompt> — 添加 cron 任务
        if query.startswith("cron:"):
            from triggers import add_cron_job
            parts = query[5:].strip().split(" ", 1)
            if len(parts) < 2:
                print("Usage: cron: <cron_expr> <prompt>")
                continue
            cron_expr, prompt = parts
            add_cron_job(cron_expr, prompt)
            print(f"\033[33m[Cron] Added: {cron_expr} → {prompt[:50]}\033[0m")
            continue

        # 默认：直接对话（s20 全部能力）
        messages.append({"role": "user", "content": query})
        response = chat(messages, context)
        if response:
            print(f"\n{response}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Loop Engineering Agent")
    parser.add_argument("--once", nargs="?", const="", default=None,
                        help="单次执行（Maker-Checker），可选传入任务描述")
    parser.add_argument("--goal", type=str, help="目标模式（验证命令）")
    parser.add_argument("--max-cycles", type=int, default=10, help="最大循环次数")
    args = parser.parse_args()

    # 验证配置
    try:
        validate_config()
    except RuntimeError as e:
        print(f"\033[31m{e}\033[0m")
        sys.exit(1)

    if args.goal:
        print(f"\033[33m[Goal mode] Running until: {args.goal}\033[0m")
        results = run_loop(mode="goal", verify_command=args.goal, max_cycles=args.max_cycles)
        print(f"\nGoal mode completed. {len(results)} cycles executed.")
    elif args.once is not None:
        task_prompt = args.once.strip()
        if task_prompt:
            # --once "fix the bug" → 直接执行指定任务
            print(f"\033[33m[Once mode] Running task: {task_prompt[:60]}\033[0m")
            result = run_task(task_prompt)
            print(f"\n[{result.final_status}] {result.feedback[:300]}")
            if result.maker_result:
                print(f"  Diff: {result.maker_result.diff_stat[:100]}")
        else:
            # --once 无参数 → 走原有 trigger 逻辑
            print("\033[33m[Once mode] Single Maker-Checker execution.\033[0m")
            results = run_loop(mode="once", max_cycles=args.max_cycles)
            print(f"\nOnce mode completed. {len(results)} cycles executed.")
    else:
        repl()


if __name__ == "__main__":
    main()
