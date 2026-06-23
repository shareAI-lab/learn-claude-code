#!/usr/bin/env python3
"""
s21: System Prompts Analysis — Analyze Claude Code's real system prompts.

Fetches prompt listings from the Piebald-AI/claude-code-system-prompts repository
(at https://github.com/Piebald-AI/claude-code-system-prompts) and produces a
structured analysis: categorization, token distribution, design patterns.

Run:  python s21_system_prompts_analysis/code.py
Need: internet access (no API key required)

This script demonstrates the "dynamic analysis" approach: it pulls real data
from the Piebald-AI repo and generates live statistics, not static estimates.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Any


PIEBALD_REPO = "https://raw.githubusercontent.com/Piebald-AI/claude-code-system-prompts/main"
README_URL = f"{PIEBALD_REPO}/README.md"


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class PromptFile:
    """A single prompt file entry parsed from the Piebald-AI README."""
    name: str
    tokens: int
    category: str        # agent, sub_agent, slash_command, creation_assistant, utility, data, tool
    subcategory: str     # "Sub-agents", "Slash Commands", "Data", etc.
    url: str


@dataclass
class PromptAnalysis:
    """Aggregated analysis results."""
    total_files: int = 0
    total_tokens: int = 0
    categories: dict[str, dict[str, Any]] = field(default_factory=dict)
    top_by_tokens: list[PromptFile] = field(default_factory=list)
    design_patterns: dict[str, list[str]] = field(default_factory=dict)


# ── Fetch ────────────────────────────────────────────────────────────────────

def fetch_readme() -> str:
    """Fetch the Piebald-AI repo README.md from GitHub raw content.

    Returns:
        Raw markdown text of the README.
    """
    req = urllib.request.Request(README_URL, headers={"User-Agent": "s21-analyzer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


# ── Parse ────────────────────────────────────────────────────────────────────

def parse_prompts_from_readme(text: str) -> list[PromptFile]:
    """Parse all prompt file entries from the Piebald-AI README.

    The README lists prompts as markdown links with token counts, e.g.:
    - [Agent Prompt: Explore](.../agent-prompt-explore.md) (**575** tks)

    Args:
        text: Raw markdown of the README.

    Returns:
        List of parsed PromptFile entries with category and token count.
    """
    prompts: list[PromptFile] = []

    # Pattern: [display name](./path/to/file.md) (**N** tks)
    # The README uses relative URLs: ./system-prompts/agent-prompt-explore.md
    # Token count format: (**575** tks)
    pattern = re.compile(
        r'\[(.*?)\]\(\./(system-prompts|tools)/([^)]+)\)'
        r'\s*\(\s*\*\*\s*(\d+)\s*\*\*\s*tks',
    )

    current_category = "unknown"
    current_subcategory = "unknown"

    for line in text.split("\n"):
        # Track heading context for categorization
        heading_match = re.match(r'^#{1,4}\s+(.*)', line)
        if heading_match:
            heading = heading_match.group(1).strip().lower()
            if heading.startswith("agent prompts"):
                current_category = "agent"
            elif heading.startswith("sub-agents"):
                current_subcategory = "Sub-agents"
                current_category = "agent"
            elif heading.startswith("creation assistant"):
                current_subcategory = "Creation Assistants"
                current_category = "agent"
            elif heading.startswith("slash commands"):
                current_subcategory = "Slash Commands"
                current_category = "agent"
            elif heading.startswith("utilities"):
                current_subcategory = "Utilities"
                current_category = "agent"
            elif heading.startswith("data"):
                current_category = "data"
                current_subcategory = "Data"
            elif heading.startswith("tool description") or heading.startswith("tools"):
                current_category = "tool"
                current_subcategory = "Tools"
            elif heading.startswith("main system prompt"):
                current_category = "main"
                current_subcategory = "Main"
            continue

        match = pattern.search(line)
        if match:
            name = match.group(1).strip()
            url = match.group(0)  # Keep the full markdown link text
            tokens = int(match.group(4))

            # Determine sub-category for agent prompts
            sub_agent = "agent"
            if current_category == "agent":
                if "explore" in name.lower() or "plan" in name.lower():
                    sub_agent = "sub_agent"
                elif name.startswith("Agent Prompt: /"):
                    sub_agent = "slash_command"
                elif "creation" in name.lower() or "status line" in name.lower():
                    sub_agent = "creation_assistant"
                else:
                    sub_agent = "utility"
            # Override category based on name prefix for non-agent entries
            elif name.startswith("Data:") or name.startswith("Skill:"):
                sub_agent = "data"
            elif name.startswith("System Prompt:") or name.startswith("Main System Prompt"):
                # System prompts can be main or tool — check the description
                if "tool" in line.lower() or "powershell" in line.lower():
                    sub_agent = "tool"
                else:
                    sub_agent = "main"
            elif name.startswith("Tool:"):
                sub_agent = "tool"

            prompts.append(PromptFile(
                name=name,
                tokens=tokens,
                category=sub_agent if current_category == "agent" else current_category,
                subcategory=current_subcategory,
                url=url,
            ))

    return prompts


# ── Analyze ──────────────────────────────────────────────────────────────────

def analyze(prompts: list[PromptFile]) -> PromptAnalysis:
    """Run all analysis passes on the parsed prompts.

    Args:
        prompts: List of parsed PromptFile entries.

    Returns:
        PromptAnalysis with aggregated statistics.
    """
    analysis = PromptAnalysis()
    analysis.total_files = len(prompts)
    analysis.total_tokens = sum(p.tokens for p in prompts)

    # Category breakdown
    cat_tokens: dict[str, int] = {}
    cat_counts: dict[str, int] = {}
    for p in prompts:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
        cat_tokens[p.category] = cat_tokens.get(p.category, 0) + p.tokens

    for cat in sorted(cat_counts):
        avg = cat_tokens[cat] / cat_counts[cat]
        analysis.categories[cat] = {
            "count": cat_counts[cat],
            "total_tokens": cat_tokens[cat],
            "avg_tokens": round(avg),
            "pct_of_total": round(cat_tokens[cat] / analysis.total_tokens * 100, 1),
        }

    # Top 10 by token count
    analysis.top_by_tokens = sorted(prompts, key=lambda p: p.tokens, reverse=True)[:10]

    # Design patterns
    analysis.design_patterns = detect_design_patterns(prompts)

    return analysis


def detect_design_patterns(prompts: list[PromptFile]) -> dict[str, list[str]]:
    """Detect recurring design patterns across prompts.

    Returns:
        Dict mapping pattern name to list of example prompt names.
    """
    patterns: dict[str, list[str]] = {}

    # Pattern 1: Multi-phase prompts
    multi_phase = [p for p in prompts if re.search(r'part\s*\d', p.name, re.IGNORECASE)]
    if multi_phase:
        patterns["Multi-phase decomposition"] = [p.name for p in multi_phase[:5]]

    # Pattern 2: Conditional assembly (environment-aware)
    conditional = [p for p in prompts if any(kw in p.name.lower() for kw in [
        "condition", "override", "environment", "feature", "mode"
    ])]
    if conditional:
        patterns["Conditional assembly"] = [p.name for p in conditional[:5]]

    # Pattern 3: Security-focused prompts
    security = [p for p in prompts if any(kw in p.name.lower() for kw in [
        "security", "safety", "guard", "block", "allow"
    ])]
    if security:
        patterns["Security constraints"] = [p.name for p in security[:5]]

    # Pattern 4: Memory/context management
    memory = [p for p in prompts if any(kw in p.name.lower() for kw in [
        "memory", "summariz", "compaction", "context"
    ])]
    if memory:
        patterns["Memory & context management"] = [p.name for p in memory[:5]]

    # Pattern 5: Schema-driven prompts (with structured output)
    schema = [p for p in prompts if any(kw in p.name.lower() for kw in [
        "structured", "json", "schema", "classifier"
    ])]
    if schema:
        patterns["Schema-driven output"] = [p.name for p in schema[:5]]

    return patterns


# ── Report ───────────────────────────────────────────────────────────────────

def generate_report(analysis: PromptAnalysis) -> str:
    """Generate a human-readable analysis report.

    Args:
        analysis: Results from analyze().

    Returns:
        Formatted report string.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Claude Code System Prompts - Dynamic Analysis")
    lines.append(f"Source: {PIEBALD_REPO}")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    lines.append(f"Total prompts: {analysis.total_files}")
    lines.append(f"Total tokens:  {analysis.total_tokens:,}")
    lines.append("")

    # Category breakdown
    lines.append("-" * 70)
    lines.append("Category Breakdown")
    lines.append("-" * 70)
    lines.append(f"{'Category':<25} {'Count':>6} {'Tokens':>10} {'Avg':>6} {'%':>6}")
    lines.append("-" * 55)
    for cat, info in sorted(analysis.categories.items()):
        lines.append(
            f"{cat:<25} {info['count']:>6} {info['total_tokens']:>10,} "
            f"{info['avg_tokens']:>6} {info['pct_of_total']:>5}%"
        )
    lines.append("")

    # Top 10 by token count
    lines.append("-" * 70)
    lines.append("Top 10 Prompts by Token Count")
    lines.append("-" * 70)
    for i, p in enumerate(analysis.top_by_tokens[:10], 1):
        lines.append(f"  {i:>2}. [{p.category}] {p.name}")
        lines.append(f"      {p.tokens:,} tokens")
    lines.append("")

    # Design patterns
    lines.append("-" * 70)
    lines.append("Detected Design Patterns")
    lines.append("-" * 70)
    for pattern, examples in analysis.design_patterns.items():
        lines.append(f"\n  {pattern}:")
        for ex in examples[:3]:
            lines.append(f"    - {ex}")
    lines.append("")

    # Key insights
    lines.append("-" * 70)
    lines.append("Key Insights")
    lines.append("-" * 70)

    largest_cat = max(analysis.categories.items(), key=lambda x: x[1]["total_tokens"])
    most_files = max(analysis.categories.items(), key=lambda x: x[1]["count"])
    lines.append(f"  1. Largest category by tokens: {largest_cat[0]} "
                 f"({largest_cat[1]['total_tokens']:,} tokens)")
    lines.append(f"  2. Most files: {most_files[0]} ({most_files[1]['count']} files)")
    lines.append(f"  3. Avg prompt size: "
                 f"{analysis.total_tokens // analysis.total_files} tokens")

    high_avg = max(analysis.categories.items(), key=lambda x: x[1]["avg_tokens"])
    lines.append(f"  4. Highest avg tokens per prompt: {high_avg[0]} "
                 f"({high_avg[1]['avg_tokens']} avg)")

    if "Multi-phase decomposition" in analysis.design_patterns:
        lines.append(f"  5. Multi-phase prompts found: "
                     f"{len(analysis.design_patterns['Multi-phase decomposition'])} "
                     f"(e.g. /code-review splits into 9 parts)")

    lines.append("")
    lines.append("=" * 70)
    lines.append("Analysis complete. Run with --json for machine-readable output.")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    """Entry point — fetch, parse, analyze, report.

    Returns:
        Exit code (0 on success, 1 on error).
    """
    # Fix encoding for Windows terminals
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Analyze Claude Code system prompts from Piebald-AI repo."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output analysis as JSON instead of the report.",
    )
    parser.add_argument(
        "--raw", action="store_true",
        help="Output raw parsed prompt data as JSON.",
    )
    args = parser.parse_args()

    print("Fetching Piebald-AI/claude-code-system-prompts README...", file=sys.stderr)
    try:
        text = fetch_readme()
    except Exception as e:
        print(f"Error fetching README: {e}", file=sys.stderr)
        return 1

    prompts = parse_prompts_from_readme(text)
    print(f"Parsed {len(prompts)} prompt entries.", file=sys.stderr)

    if not prompts:
        print("Error: No prompts parsed. The README format may have changed.", file=sys.stderr)
        return 1

    if args.raw:
        data = [{"name": p.name, "tokens": p.tokens, "category": p.category,
                 "subcategory": p.subcategory} for p in prompts]
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    analysis = analyze(prompts)

    if args.json:
        output = {
            "total_files": analysis.total_files,
            "total_tokens": analysis.total_tokens,
            "categories": analysis.categories,
            "top_by_tokens": [
                {"name": p.name, "tokens": p.tokens, "category": p.category}
                for p in analysis.top_by_tokens[:10]
            ],
            "design_patterns": {
                k: v[:5] for k, v in analysis.design_patterns.items()
            },
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(generate_report(analysis))

    return 0


if __name__ == "__main__":
    sys.exit(main())