# s14: Security Classifier

`s02 > s13 > [ s14 ] | s15 | s16 > s17`

> *"Regex sees patterns; the LLM sees intent"*
>
> **Harness layer**: Security classification -- judging command intent, not just shape.

## Problem

Regex patterns from s13 match shapes, not intent. `rm -rf build/` and `rm -rf /` look identical to a regex. The LLM itself can judge context: one is a normal build cleanup, the other is catastrophic.

## Solution

```
    Command
       |
       v
    +--------------------+
    | Layer 1: Quick Scan|   regex patterns (zero cost)
    +--------+-----------+
             |
        matched? --yes--> deny/ask
             |
            no
             v
    +--------------------+
    | Layer 2: LLM Class |   ~10 tokens per call
    +--------+-----------+
             |
      safe / moderate / dangerous
             |
        allow / ask / deny
```

Two-layer classification pipeline:

- **Layer 1** (regex): 15 known dangerous patterns, zero cost, instant match.
- **Layer 2** (LLM): classifies unknown commands by understanding intent.

## How It Works

1. `SecurityClassifier.quick_scan()` checks 15 regex patterns in O(1).

```python
DANGEROUS_PATTERNS = [
    (re.compile(r"rm\s+-rf\s+/(?!\w)"), "Root recursive delete"),
    (re.compile(r"sudo\s+"), "Elevated privileges"),
    (re.compile(r"curl.*\|\s*(ba)?sh"), "Remote code execution"),
    # ... 12 more patterns
]
```

2. `SecurityClassifier.llm_classify()` sends the command to the LLM for intent analysis.

```python
def llm_classify(self, command: str, context: str = "") -> str:
    resp = self.client.messages.create(
        model=self.model,
        messages=[{"role": "user", "content":
            f"Classify: {command}\nContext: {context}\n"
            f"Reply: safe, moderate, or dangerous"}],
        max_tokens=10,
    )
    return resp.content[0].text.strip().lower()
```

3. `classify()` runs the full pipeline: quick-scan -> whitelist -> LLM.

## What Changed From s13

| Component | Before (s13) | After (s14) |
|-----------|-------------|-------------|
| Classification | Regex pattern matching only | Regex quick-scan + LLM classification |
| Unknown commands | Default allow | LLM judges safe/moderate/dangerous |
| False positives | High (`rm -rf build/` blocked) | Low (LLM understands intent) |
| Cost | Zero | Whitelist zero + LLM ~10 tokens/call |

## Try It

```sh
cd learn-claude-code
python agents/s14_security_classifier.py
```

1. `delete the build/ directory` (LLM should judge as moderate -> ask)
2. `list all python files` (whitelist -> allow)
3. `run git push --force origin main` (regex pattern -> deny)
4. `run pip install numpy` (LLM should judge as moderate -> ask)
5. `create a new file called test.py` (LLM should judge as safe -> allow)
