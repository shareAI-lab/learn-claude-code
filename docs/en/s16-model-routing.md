# s16: Model Routing / Tier Selection

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > [ s16 ] s17 > s18 > s19`

> *"Most tasks don't need the smartest model"* -- route by complexity.
>
> **Harness layer**: Tier selection -- the harness picks the right model per task.

## Problem

By s15, workflows spawn many agents. If every agent uses Opus, cost explodes. If every agent uses Haiku, quality drops. The right answer: match the model to the task.

## Solution

```
User: "Fix typo in README"
 |
 v
[Classifier]  keyword: "typo" -> simple
 |
 v
[Haiku]  (fast, cheap) -----------------> result

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
```

## How It Works

1. **Classify the task.** Keyword-based heuristic (production uses learned classifiers).

```python
SIMPLE_KEYWORDS = {"typo", "rename", "format", "indent", "trivial"}
COMPLEX_KEYWORDS = {"architect", "refactor", "design", "debug", "security audit"}

def classify_task(query):
    q = query.lower()
    for kw in SIMPLE_KEYWORDS:
        if kw in q: return "haiku"
    for kw in COMPLEX_KEYWORDS:
        if kw in q: return "opus"
    return "sonnet"  # default
```

2. **Execute with fallback.** If the cheaper model fails, escalate.

```python
def run_with_fallback(prompt, tier):
    tiers = ["haiku", "sonnet", "opus"]
    for t in tiers[tiers.index(tier):]:
        result = run_agent(prompt, model=M[TIER[t]])
        if len(result) > 50:
            return result
```

## Try It

```sh
cd learn-claude-code
python agents/s16_model_routing.py
```

Try these:

1. `/classify "Fix the typo in line 42"` -- see tier routing
2. `/cost "Refactor the authentication module"` -- see cost estimates
3. `/route "What files are in src/?"` -- execute with auto-routed tier
4. `/demo` -- batch classify multiple queries
