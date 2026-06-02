#!/usr/bin/env python3
# Harness: structured output — the model returns parseable data, not prose.
"""
s17_structured_output.py - Structured Output

Force the model to return schema-validated JSON instead of free text.
This enables the harness to programmatically consume agent results.

    Without structured output:
    Model: "I found 3 issues: first, the discount function doesn't handle
    negative values. Second, there's no input validation. Third, the
    variable naming could be clearer..."
         -> harness must parse prose (unreliable)

    With structured output:
    Model: {"findings": [{"severity": "critical", "line": 5, "message": "..."}, ...]}
         -> harness reads JSON directly (reliable)

    Validation loop:
    1. Send prompt + schema instructions
    2. Parse JSON response
    3. Validate against schema
    4. If invalid: send error back to model, retry
    5. Max 3 retries, then return best-effort

Key insight: "JSON Schema constraints turn prose into data the harness can use."
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
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. When asked for structured output, return valid JSON."


# -- Schema definition & validation (no external deps) --

# Simple schema format: {"type": "...", "properties": {...}, "required": [...]}
# Supports: object, array, string, integer, boolean, number

def validate_schema(data, schema, path: str = "$", errors: list = None) -> list:
    """
    Validate data against a simple JSON Schema.

    Supports: type checking, required fields, array item schemas.
    Returns list of error strings (empty = valid).
    """
    if errors is None:
        errors = []

    expected_type = schema.get("type")

    if expected_type == "object":
        if not isinstance(data, dict):
            errors.append(f"{path}: expected object, got {type(data).__name__}")
            return errors
        # Check required fields
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"{path}: missing required field '{req}'")
        # Validate properties
        props = schema.get("properties", {})
        for key, val_schema in props.items():
            if key in data:
                validate_schema(data[key], val_schema, f"{path}.{key}", errors)

    elif expected_type == "array":
        if not isinstance(data, list):
            errors.append(f"{path}: expected array, got {type(data).__name__}")
            return errors
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(data):
                validate_schema(item, items_schema, f"{path}[{i}]", errors)

    elif expected_type == "string":
        if not isinstance(data, str):
            errors.append(f"{path}: expected string, got {type(data).__name__}")
        # Enum validation
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: value '{data}' not in enum {schema['enum']}")

    elif expected_type == "integer":
        if not isinstance(data, int):
            errors.append(f"{path}: expected integer, got {type(data).__name__}")

    elif expected_type == "number":
        if not isinstance(data, (int, float)):
            errors.append(f"{path}: expected number, got {type(data).__name__}")

    elif expected_type == "boolean":
        if not isinstance(data, bool):
            errors.append(f"{path}: expected boolean, got {type(data).__name__}")

    return errors


# -- Common schemas for teaching --

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

TASK_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "in_progress", "blocked"]},
        "completed": {"type": "integer"},
        "total": {"type": "integer"},
        "blockers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_steps": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["status", "completed", "total"],
}

SEARCH_RESULTS_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "snippet": {"type": "string"},
                    "relevance": {"type": "number"},
                },
                "required": ["file", "snippet"],
            },
        },
    },
    "required": ["query", "results"],
}


def structured_query(prompt: str, schema: dict, system_msg: str = None, max_retries: int = 3) -> dict:
    """
    Query the model and enforce JSON Schema output.

    Sends the schema as instructions, validates the response,
    and retries with error feedback if validation fails.
    """
    if system_msg is None:
        system_msg = SYSTEM

    schema_json = json.dumps(schema, indent=2)
    structured_system = (
        f"{system_msg}\n\n"
        f"IMPORTANT: Return your response as valid JSON matching this schema:\n"
        f"```json\n{schema_json}\n```\n\n"
        f"Return ONLY the JSON object. No markdown, no explanation, no code fences."
    )

    last_errors = []
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            # Retry with error feedback
            error_text = "\n".join(f"  - {e}" for e in last_errors)
            retry_prompt = (
                f"Your previous response failed schema validation:\n{error_text}\n\n"
                f"Fix these errors and return valid JSON matching the schema.\n\n"
                f"Original request: {prompt}"
            )
        else:
            retry_prompt = prompt

        messages = [{"role": "user", "content": retry_prompt}]
        response = client.messages.create(
            model=MODEL, system=structured_system, messages=messages, max_tokens=4000,
        )
        text = "".join(b.text for b in response.content if hasattr(b, "text")).strip()

        # Strip markdown code fences if present
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.startswith("```"):
            text = text[len("```"):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        # Parse JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            last_errors = [f"JSON parse error: {e}"]
            print(f"  [attempt {attempt}/{max_retries}] JSON parse failed, retrying...")
            continue

        # Validate schema
        errors = validate_schema(data, schema)
        if errors:
            last_errors = errors
            print(f"  [attempt {attempt}/{max_retries}] Schema validation failed, retrying...")
            for err in errors[:3]:
                print(f"    {err}")
            continue

        return data

    # All retries exhausted
    print(f"  [warning] Schema validation failed after {max_retries} attempts.")
    return {"_error": "validation failed", "_errors": last_errors, "_raw": text}


# -- Base tools --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


# -- Agent loop --
TOOL_HANDLERS = {
    "bash":      lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
]


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=4000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    print("Structured Output demo.")
    print("Commands: /review <code> /status <text> /demo\n")

    sample_code = """
def calculate_discount(price, quantity):
    if quantity > 100:
        discount = 0.5
    elif quantity > 50:
        discount = 0.3
    elif quantity > 10:
        discount = 0.1
    else:
        discount = 0
    total = price * quantity * (1 - discount)
    return total
"""

    while True:
        try:
            query = input("\033[36ms17 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        cmd = query.strip()

        if cmd.startswith("/review"):
            code = cmd[len("/review"):].strip() or sample_code
            print("Running structured code review...\n")
            prompt = f"Review this Python code for issues. Be specific with line numbers.\n\n```python\n{code}\n```"
            result = structured_query(prompt, CODE_REVIEW_SCHEMA)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()
            continue

        if cmd.startswith("/status"):
            text = cmd[len("/status"):].strip()
            if not text:
                text = "I've finished setting up the database and API. Next I need to add auth and write tests."
            print("Extracting structured status...\n")
            prompt = (
                "Extract task status information from this text.\n"
                "Output: status (done/in_progress/blocked), completed items, total items, blockers, next steps.\n\n"
                f"Text: {text}"
            )
            result = structured_query(prompt, TASK_STATUS_SCHEMA)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()
            continue

        if cmd.startswith("/demo"):
            # Demo: show validation in action with bad input
            print("=== Demo: Schema validation ===\n")

            # Show what the schema looks like
            print("CODE_REVIEW_SCHEMA:")
            print(json.dumps(CODE_REVIEW_SCHEMA, indent=2))
            print()

            # Test with a manually crafted bad result
            bad_data = {"findings": "not an array", "summary": 123}
            errors = validate_schema(bad_data, CODE_REVIEW_SCHEMA)
            print(f"Validating bad data: {bad_data}")
            print(f"Errors: {errors}\n")

            # Test with good data
            good_data = {
                "findings": [
                    {"severity": "warning", "line": 1, "message": "Missing docstring"},
                    {"severity": "info", "message": "Consider using a dict for discount tiers"},
                ],
                "summary": "Code works but could be more maintainable.",
            }
            errors = validate_schema(good_data, CODE_REVIEW_SCHEMA)
            print(f"Validating good data: {json.dumps(good_data)}")
            print(f"Errors: {errors}\n")

            continue

        if cmd.startswith("/validate"):
            # Let user test validation with their own JSON
            rest = cmd[len("/validate"):].strip()
            if not rest:
                print("Usage: /validate <json> (e.g., /validate {'findings': [], 'summary': 'ok'})")
                continue
            try:
                data = json.loads(rest)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                continue
            errors = validate_schema(data, CODE_REVIEW_SCHEMA)
            if errors:
                print("Validation errors:")
                for e in errors:
                    print(f"  - {e}")
            else:
                print("Valid! No errors.")
            print()
            continue

        # Normal chat
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
