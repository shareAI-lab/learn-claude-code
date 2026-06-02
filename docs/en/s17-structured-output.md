# s17: Structured Output

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > [ s17 ] s18 > s19`

> *"JSON Schema constraints turn prose into data"* -- the harness reads structured output, not free text.
>
> **Harness layer**: Schema validation -- force the model to return parseable data.

## Problem

By s16, the harness routes tasks intelligently. But the model still returns free text. To use the result programmatically, the harness must parse prose -- unreliable and expensive.

If the model returns validated JSON, the harness reads it directly.

## Solution

```
Without structured output:
Model: "I found 3 issues: first, the discount function doesn't handle
negative values..."
 -> harness must parse prose (unreliable)

With structured output:
Model: {"findings": [{"severity": "critical", "line": 5, "message": "..."}]}
 -> harness reads JSON directly (reliable)

Validation loop:
1. Send prompt + schema
2. Parse JSON response
3. Validate against schema
4. If invalid: send error back, retry
5. Max 3 retries
```

## How It Works

1. **Define a schema.** JSON Schema subset (object, array, string, integer, enum).

```python
CODE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                    "line": {"type": "integer"},
                    "message": {"type": "string"},
                },
                "required": ["severity", "message"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["findings", "summary"],
}
```

2. **Validate against schema.** Simple type + required check.

```python
def validate_schema(data, schema, errors=None):
    if schema.get("type") == "object":
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"missing required field '{req}'")
        for key, val_schema in schema.get("properties", {}).items():
            if key in data:
                validate_schema(data[key], val_schema, errors)
    return errors
```

3. **Retry with feedback.** On validation failure, send errors back to the model.

```python
for attempt in range(1, max_retries + 1):
    if attempt > 1:
        prompt = f"Validation failed: {errors}\nFix and retry.\n{original_prompt}"
    data = json.loads(response_text)
    errors = validate_schema(data, schema)
    if not errors:
        return data
```

## Try It

```sh
cd learn-claude-code
python agents/s17_structured_output.py
```

Try these:

1. `/review` -- structured code review with JSON output
2. `/status "Finished database setup, need auth next"` -- extract status as JSON
3. `/demo` -- show schema validation with good and bad data
4. `/validate {"findings": [], "summary": "ok"}` -- test your own JSON
