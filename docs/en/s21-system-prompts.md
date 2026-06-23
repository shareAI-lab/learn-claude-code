# s21: System Prompts Analysis

[中文](../../s21_system_prompts_analysis/README.md) · [English](../../s21_system_prompts_analysis/README.en.md)

s21 directly analyzes the Piebald-AI/claude-code-system-prompts repository, using code.py to dynamically fetch, classify, and count 515+ real prompts.

## Key Points

- Data source: Piebald-AI repository (Claude Code v2.1.181, 515+ prompts)
- Method: code.py dynamically fetches README.md, parses with regex, aggregates by category
- Design patterns: multi-stage decomposition, conditional assembly, safety constraints, memory management, schema-driven

## Run

```sh
python s21_system_prompts_analysis/code.py
```

See [s21_system_prompts_analysis/README.en.md](../../s21_system_prompts_analysis/README.en.md)
