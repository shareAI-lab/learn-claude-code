#!/usr/bin/env python3
# Harness: model routing — the harness picks the right model tier per task.
"""
s16_model_routing.py - Model Routing / Tier Selection

Route tasks to different model tiers based on complexity.
The harness — not the user — decides which model handles each request.

    User: "Fix typo in README"
         |
         v
    [Classifier]  keyword: "typo" -> simple
         |
         v
    [Haiku]  (fast, cheap)  -----------------> result

    User: "Refactor auth module"
         |
         v
    [Classifier]  keyword: "refactor" -> complex
         |
         v
    [Opus]  (slow, expensive, smart) ---------> result

    Tier comparison:
    +--------+--------+---------+---------+-----------+
    | Tier   | Model  | Speed   | Cost    | Use for   |
    +--------+--------+---------+---------+-----------+
    | Haiku  | fast   | ~1x     | ~1x     | lookups,  |
    |        |        |         |         | simple    |
    +--------+--------+---------+---------+           |
    | Sonnet | medium | ~3x     | ~5x     | standard  |
    |        |        |         |         | work      |
    +--------+--------+---------+---------+-----------+
    | Opus   | smart  | ~10x    | ~50x    | complex   |
    |        |        |         |         | analysis  |
    +--------+--------+---------+---------+-----------+

    With fallback:
    Haiku attempt -> failed? -> Sonnet attempt -> failed? -> Opus

Key insight: "Most tasks don't need the smartest model."
"""

import json
import os
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))

# Model tiers — resolve from env, fall back to default MODEL_ID
# In production: Haiku=claude-haiku-4-20250921, Sonnet=claude-sonnet-4-20250514, Opus=claude-opus-4-20250514
# For teaching with a single provider, we use env vars or defaults.
DEFAULT_MODEL = os.environ["MODEL_ID"]

MODEL_TIERS = {
    "haiku": os.getenv("MODEL_HAIKU", DEFAULT_MODEL),
    "sonnet": os.getenv("MODEL_SONNET", DEFAULT_MODEL),
    "opus": os.getenv("MODEL_OPUS", DEFAULT_MODEL),
}

# If all tiers resolve to the same model, note that for the user
ALL_SAME = len(set(MODEL_TIERS.values())) == 1
if ALL_SAME:
    print("[info] All tiers use the same model ({MODEL_TIERS['haiku']}). "
          "Set MODEL_HAIKU/MODEL_SONNET/MODEL_OPUS env vars for real routing.")

# Task classification rules
SIMPLE_KEYWORDS = {"typo", "rename", "format", "indent", "remove", "delete",
                   "add comment", "update readme", "spell", "trivial", "simple"}
COMPLEX_KEYWORDS = {"architect", "refactor", "design", "strategy", "performance",
                    "optimize", "debug", "root cause", "security audit", "complex"}

TIER_DESCRIPTIONS = {
    "haiku":  "Fast, cheap — simple edits, lookups, formatting",
    "sonnet": "Balanced — standard implementation, code review",
    "opus":   "Slow, expensive — complex analysis, architecture, debugging",
}


def classify_task(query: str) -> str:
    """
    Classify a task into a model tier based on keywords.

    Simple heuristic for teaching purposes. A production harness would
    use an LLM call or learned classifier.
    """
    q = query.lower()

    for kw in SIMPLE_KEYWORDS:
        if kw in q:
            return "haiku"
    for kw in COMPLEX_KEYWORDS:
        if kw in q:
            return "opus"

    # Default to sonnet
    return "sonnet"


def run_agent(prompt: str, system_msg: str, model_id: str, tools=None) -> str:
    """Run one agent loop, return final text."""
    messages = [{"role": "user", "content": prompt}]
    for _ in range(15):
        kwargs = {"model": model_id, "system": system_msg, "messages": messages, "max_tokens": 4000}
        if tools:
            kwargs["tools"] = tools
        response = client.messages.create(**kwargs)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = f"Tool '{block.name}' not available in routing demo"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "(no output)"


def run_with_tier(prompt: str, tier: str, system_msg: str = "") -> str:
    """Run with a specific tier."""
    model_id = MODEL_TIERS[tier]
    if not system_msg:
        system_msg = f"You are a helpful coding assistant at {WORKDIR}."
    print(f"  [routing] tier={tier}, model={model_id}")
    return run_agent(prompt, system_msg, model_id)


def run_with_fallback(prompt: str, tier: str, system_msg: str = "") -> dict:
    """
    Try with the given tier. If result is empty/short, retry with next tier.

    Returns {"result": str, "tier_used": str, "fallbacks": int}
    """
    tiers = ["haiku", "sonnet", "opus"]
    start_idx = tiers.index(tier)
    fallbacks = 0

    for i in range(start_idx, len(tiers)):
        current_tier = tiers[i]
        result = run_with_tier(prompt, current_tier, system_msg)

        # Check if result is adequate (heuristic: > 50 chars, not an error)
        if len(result.strip()) > 50 and not result.startswith("(no output)"):
            return {"result": result, "tier_used": current_tier, "fallbacks": fallbacks}

        fallbacks += 1
        print(f"  [routing] tier {current_tier} produced weak result, escalating...")

    # All tiers failed
    return {"result": result, "tier_used": tiers[-1], "fallbacks": fallbacks}


# -- Cost estimator --
def estimate_cost(prompt_len: int, expected_response: int, tier: str) -> dict:
    """Rough cost estimate per tier ( Anthropic per-token pricing, approximate)."""
    prices = {
        "haiku":  {"input": 0.0008 / 1000, "output": 0.004 / 1000},
        "sonnet": {"input": 0.03 / 1000, "output": 0.15 / 1000},
        "opus":   {"input": 0.15 / 1000, "output": 0.75 / 1000},
    }
    p = prices.get(tier, prices["sonnet"])
    tokens_in = prompt_len // 4  # rough: 4 chars ~ 1 token
    tokens_out = expected_response // 4
    cost = tokens_in * p["input"] + tokens_out * p["output"]
    return {
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "estimated_cost_usd": round(cost, 4),
    }


def show_cost_comparison(prompt: str):
    """Show estimated cost for all tiers."""
    print(f"\nCost estimate for: {prompt[:60]}...")
    print(f"{'Tier':<10} {'Input Tokens':<15} {'Output Tokens':<15} {'Est. Cost ($)':<15}")
    print("-" * 55)
    for tier in ["haiku", "sonnet", "opus"]:
        est = estimate_cost(len(prompt), 2000, tier)
        print(f"{tier:<10} {est['input_tokens']:<15} {est['output_tokens']:<15} {est['estimated_cost_usd']:<15}")
    print()


SYSTEM = (
    f"You are a model routing agent at {WORKDIR}.\n"
    f"Commands:\n"
    f"  /classify <query> — Show which tier a query routes to\n"
    f"  /cost <query>     — Show estimated cost for all tiers\n"
    f"  /route <query>    — Execute with classified tier\n"
    f"  /route <tier> <query> — Execute with specific tier\n"
    f"  /fallback <query> — Execute with fallback chain\n"
)


if __name__ == "__main__":
    history = []
    print("Model Routing demo. Commands: /classify /cost /route /fallback\n")
    print(f"Tiers available: {MODEL_TIERS}\n")

    while True:
        try:
            query = input("\033[36ms16 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        cmd = query.strip()

        if cmd.startswith("/classify"):
            text = cmd[len("/classify"):].strip()
            tier = classify_task(text)
            print(f"  Query: {text}")
            print(f"  -> Tier: {tier} ({TIER_DESCRIPTIONS[tier]})")
            print(f"  -> Model: {MODEL_TIERS[tier]}")
            print()
            continue

        if cmd.startswith("/cost"):
            text = cmd[len("/cost"):].strip()
            show_cost_comparison(text)
            continue

        if cmd.startswith("/route"):
            rest = cmd[len("/route"):].strip()
            # Check if first word is a tier name
            parts = rest.split(None, 1)
            if parts[0] in MODEL_TIERS and len(parts) > 1:
                tier, text = parts[0], parts[1]
            else:
                text = rest
                tier = classify_task(text)
            print(f"Routing to {tier}...")
            result = run_with_tier(text, tier)
            print(f"\nResult:\n{result}\n")
            continue

        if cmd.startswith("/fallback"):
            text = cmd[len("/fallback"):].strip()
            tier = classify_task(text)
            print(f"Starting at tier: {tier} (with fallback)...")
            result = run_with_fallback(text, tier)
            print(f"\nTier used: {result['tier_used']}, fallbacks: {result['fallbacks']}")
            print(f"\nResult:\n{result['result']}\n")
            continue

        if cmd.startswith("/demo"):
            # Demo: show routing for various queries
            test_queries = [
                "Fix the typo in line 42",
                "Refactor the authentication module",
                "What files are in src/?",
                "Debug the memory leak in the worker process",
            ]
            for q in test_queries:
                tier = classify_task(q)
                est = estimate_cost(len(q), 1000, tier)
                print(f"  [{tier:<7}] ${est['estimated_cost_usd']:<7} -> {q}")
            print()
            continue

        # Normal chat — route automatically
        tier = classify_task(query)
        print(f"[auto-route: {tier}]")
        history.append({"role": "user", "content": query})
        # For simplicity, run as single-turn in REPL
        model_id = MODEL_TIERS[tier]
        response = client.messages.create(
            model=model_id,
            system=f"You are a helpful coding assistant at {WORKDIR}.",
            messages=[{"role": "user", "content": query}],
            max_tokens=4000,
        )
        text_out = "".join(b.text for b in response.content if hasattr(b, "text"))
        print(text_out)
        print()
