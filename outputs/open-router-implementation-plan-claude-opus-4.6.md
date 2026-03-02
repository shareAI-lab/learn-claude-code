# OpenRouter Integration — Design & Implementation Plan

## Executive Summary

This document describes the design and implementation plan for supporting **both Anthropic (Claude)** and **OpenRouter** as LLM providers in the learn-claude-code agent system. The plan introduces a **Provider Abstraction Layer** that normalizes the two different API protocols behind a common interface, enabling every agent stage (s01–s12 + s_full) to work with either backend via a single configuration switch.

---

## 1. Current Architecture Analysis

### 1.1 How Claude Is Integrated Today

Every agent stage follows the same pattern:

```python
from anthropic import Anthropic

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

**Key API surface used across all 12 stages:**

| Concern | Anthropic SDK |
|---------|--------------|
| Client init | `Anthropic(base_url=...)` |
| API call | `client.messages.create(model, system, messages, tools, max_tokens)` |
| System prompt | Separate `system=` parameter (string) |
| Tool schema | `{"name", "description", "input_schema": {...}}` |
| Stop signal | `response.stop_reason == "tool_use"` |
| Content blocks | `response.content` → list of `TextBlock` / `ToolUseBlock` objects |
| Tool use fields | `block.type == "tool_use"`, `block.name`, `block.input` (dict), `block.id` |
| Text fields | `block.type == "text"`, `block.text` |
| Tool result msg | `{"type": "tool_result", "tool_use_id": block.id, "content": "..."}` |
| Assistant msg | `{"role": "assistant", "content": response.content}` (raw block list) |

### 1.2 OpenRouter API Protocol (OpenAI-Compatible)

```python
from openrouter import OpenRouter

client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
response = client.chat.send(
    model="anthropic/claude-4.5-sonnet",
    messages=[...], tools=[...], max_tokens=8000,
)
```

| Concern | OpenRouter SDK |
|---------|---------------|
| Client init | `OpenRouter(api_key=...)` |
| API call | `client.chat.send(model, messages, tools, max_tokens)` |
| System prompt | Included as `{"role": "system", "content": "..."}` in messages list |
| Tool schema | `{"type": "function", "function": {"name", "description", "parameters": {...}}}` |
| Stop signal | `response.choices[0].finish_reason == "tool_calls"` |
| Content | `response.choices[0].message.content` (string or null) |
| Tool calls | `response.choices[0].message.tool_calls` → list of `{id, type, function: {name, arguments}}` |
| Tool use fields | `tc.function.name`, `json.loads(tc.function.arguments)`, `tc.id` |
| Tool result msg | `{"role": "tool", "tool_call_id": tc.id, "content": "..."}` |
| Assistant msg | `{"role": "assistant", "content": "...", "tool_calls": [...]}` |

### 1.3 Key Differences Summary

| Dimension | Anthropic | OpenRouter |
|-----------|-----------|------------|
| System prompt delivery | Separate `system=` param | System message in `messages` array |
| Tool definition wrapper | Flat `{name, description, input_schema}` | Nested `{type:"function", function:{name, description, parameters}}` |
| Tool input key | `input_schema` | `parameters` |
| Stop reason value | `"tool_use"` | `"tool_calls"` |
| Response shape | `response.content` (block list) | `response.choices[0].message` |
| Tool use in response | Block objects in `content` | Separate `tool_calls` list |
| Tool input format | `block.input` (dict) | `tc.function.arguments` (JSON string) |
| Tool result message | `{type:"tool_result", tool_use_id}` in user content list | `{role:"tool", tool_call_id}` as separate message |

---

## 2. Architecture Design

### 2.1 Design Goals

1. **Minimal loop change**: The `agent_loop()` function in each stage should need only ~3 lines changed (swap `client.messages.create(...)` for `provider.create_message(...)`).
2. **Provider-agnostic normalized types**: All agent code works with the same response objects regardless of backend.
3. **Easy configuration**: A single `LLM_PROVIDER` env var switches between backends.
4. **Backward-compatible**: Existing Anthropic-only usage continues to work with zero config change.
5. **Testable**: Each provider adapter is independently unit-testable with mocked API responses.

### 2.2 Architecture Diagram

```
                        .env
                        ├── LLM_PROVIDER=anthropic|openrouter
                        ├── ANTHROPIC_API_KEY=...
                        ├── OPENROUTER_API_KEY=...
                        └── MODEL_ID=...
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   create_provider()   │  Factory function
                     │   reads LLM_PROVIDER  │
                     └─────────┬─────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
    ┌───────────▼───────────┐    ┌────────────▼────────────┐
    │  AnthropicProvider    │    │  OpenRouterProvider      │
    │                       │    │                          │
    │  - anthropic.Anthropic│    │  - openrouter.OpenRouter │
    │  - pass-through tools │    │  - convert tools format  │
    │  - wrap response      │    │  - convert messages      │
    │                       │    │  - wrap response         │
    └───────────┬───────────┘    └────────────┬────────────┘
                │                             │
                └──────────────┬──────────────┘
                               │
                     ┌─────────▼─────────┐
                     │  LLMResponse      │   Normalized response
                     │  ├─ stop_reason   │   "tool_use" | "end_turn" | ...
                     │  ├─ content       │   List[ContentBlock]
                     │  └─ raw          │   Original provider response
                     └─────────┬─────────┘
                               │
                     ┌─────────▼─────────┐
                     │   agent_loop()    │   Unchanged logic
                     │   while True:     │
                     │     resp = provider│.create_message(...)
                     │     if stop...    │
                     │     exec tools    │
                     └───────────────────┘
```

### 2.3 Module Structure

```
agents/
├── llm_provider.py          # NEW: Provider abstraction + factory
├── s01_agent_loop.py        # MODIFIED: use provider
├── s02_tool_use.py          # MODIFIED: use provider
├── ...
├── s12_worktree_task_isolation.py  # MODIFIED: use provider
├── s_full.py                # MODIFIED: use provider
tests/
├── __init__.py
├── test_llm_provider.py     # NEW: Unit tests for provider layer
├── test_s01_agent_loop.py   # NEW: Integration tests per stage
├── ...
```

### 2.4 Decision Records

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **Single `llm_provider.py` module** | Keeps the "one file per stage" learning design intact; all provider logic in one place | Separate package (`providers/`) — over-engineered for a teaching repo |
| **Dataclass-based normalized response** | Simple, no extra deps, clear field names | Pydantic models — adds dependency; raw dicts — loses IDE support |
| **Normalize to Anthropic-style semantics** | The entire existing codebase uses Anthropic conventions (`stop_reason`, `tool_use`, content blocks); normalizing to this reduces changes | Normalize to OpenAI-style — would require rewriting all 12 stages |
| **Environment variable configuration** | Consistent with existing `.env` pattern | Config file — more complex; CLI args — different per stage |
| **Provider converts messages both ways** | Tool results in Anthropic format (list of `tool_result` dicts in user message) differ from OpenRouter format (`role: tool` messages); provider handles this transparently | Let agent code produce both formats — violates DRY |

---

## 3. Detailed Design

### 3.1 Normalized Types (`agents/llm_provider.py`)

```python
from dataclasses import dataclass, field
from typing import Any
from abc import ABC, abstractmethod

@dataclass
class TextBlock:
    """Normalized text content block."""
    type: str = "text"
    text: str = ""

@dataclass
class ToolUseBlock:
    """Normalized tool use block."""
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)

ContentBlock = TextBlock | ToolUseBlock

@dataclass
class LLMResponse:
    """Normalized LLM response, provider-agnostic."""
    stop_reason: str          # "tool_use" | "end_turn" | "max_tokens"
    content: list[ContentBlock]  # Mixed list of TextBlock / ToolUseBlock
    raw: Any = None           # Original provider response for debugging
```

### 3.2 Abstract Provider Interface

```python
class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def create_message(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 8000,
    ) -> LLMResponse:
        """Send a message to the LLM and return a normalized response.
        
        Args:
            model: Model identifier string.
            system: System prompt text.
            messages: Conversation history in Anthropic-style format.
                      The provider is responsible for converting to its native format.
            tools: Tool definitions in Anthropic-style format (flat {name, description, input_schema}).
                   The provider converts to its native format internally.
            max_tokens: Maximum tokens in the response.
            
        Returns:
            LLMResponse with normalized stop_reason and content blocks.
        """
        ...

    @abstractmethod
    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Format the assistant's response as a message dict for conversation history.
        
        Returns a dict suitable for appending to the messages list.
        For Anthropic: {"role": "assistant", "content": <block list>}
        For OpenRouter: {"role": "assistant", "content": "...", "tool_calls": [...]}
        
        The provider stores this in whatever format it needs, and `create_message`
        handles conversion when sending to the API.
        """
        ...

    @abstractmethod
    def format_tool_results(self, results: list[dict]) -> dict:
        """Format tool results for the conversation history.
        
        Args:
            results: List of {"tool_use_id": str, "content": str} dicts.
            
        Returns:
            Message(s) suitable for appending to messages list.
            For Anthropic: single {"role": "user", "content": [{"type": "tool_result", ...}]}
            For OpenRouter: list of {"role": "tool", "tool_call_id": ..., "content": ...}
        """
        ...
```

### 3.3 Anthropic Provider Implementation

```python
class AnthropicProvider(LLMProvider):
    """Provider using the Anthropic Python SDK (native Claude API)."""

    def __init__(self):
        from anthropic import Anthropic
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        self._client = Anthropic(base_url=base_url)

    def create_message(self, model, system, messages, tools=None, max_tokens=8000):
        kwargs = dict(model=model, system=system, messages=messages, max_tokens=max_tokens)
        if tools:
            kwargs["tools"] = tools  # Anthropic format passed through
        response = self._client.messages.create(**kwargs)
        return LLMResponse(
            stop_reason=response.stop_reason,
            content=[self._convert_block(b) for b in response.content],
            raw=response,
        )

    def _convert_block(self, block) -> ContentBlock:
        if block.type == "text":
            return TextBlock(text=block.text)
        elif block.type == "tool_use":
            return ToolUseBlock(id=block.id, name=block.name, input=block.input)
        return TextBlock(text=str(block))

    def format_assistant_message(self, response: LLMResponse) -> dict:
        # Anthropic stores raw content blocks in the assistant message
        return {"role": "assistant", "content": response.raw.content}

    def format_tool_results(self, results: list[dict]) -> dict:
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": r["tool_use_id"], "content": r["content"]}
                for r in results
            ],
        }
```

### 3.4 OpenRouter Provider Implementation

```python
import json as _json

class OpenRouterProvider(LLMProvider):
    """Provider using the OpenRouter Python SDK (OpenAI-compatible API)."""

    def __init__(self):
        from openrouter import OpenRouter
        self._client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY", ""))

    def create_message(self, model, system, messages, tools=None, max_tokens=8000):
        # Convert Anthropic-style messages to OpenAI-style
        oai_messages = self._convert_messages(system, messages)
        
        kwargs = dict(
            model=model,
            messages=oai_messages,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = self._client.chat.send(**kwargs)
        return self._normalize_response(response)

    def _convert_messages(self, system: str, messages: list[dict]) -> list[dict]:
        """Convert Anthropic-format messages to OpenAI-format messages."""
        oai = []
        if system:
            oai.append({"role": "system", "content": system})
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content")
            
            if role == "assistant":
                # Could be raw Anthropic block list or already OpenRouter format
                if isinstance(content, list) and content and hasattr(content[0], "type"):
                    # Anthropic SDK block objects — convert
                    oai.append(self._convert_assistant_blocks(content))
                elif isinstance(content, dict) and "tool_calls" in content:
                    oai.append(content)
                elif isinstance(content, str):
                    oai.append({"role": "assistant", "content": content})
                else:
                    # Already in OpenRouter format (from format_assistant_message)
                    oai.append(msg)
                    
            elif role == "user":
                if isinstance(content, list):
                    # Check if this is tool results (Anthropic format)
                    if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                        for tr in content:
                            oai.append({
                                "role": "tool",
                                "tool_call_id": tr["tool_use_id"],
                                "content": tr.get("content", ""),
                            })
                    else:
                        # Mixed content (e.g. text + tool_results from nag reminder)
                        # Separate tool results from text
                        tool_results = [c for c in content if isinstance(c, dict) and c.get("type") == "tool_result"]
                        text_parts = [c for c in content if isinstance(c, dict) and c.get("type") == "text"]
                        
                        for tr in tool_results:
                            oai.append({
                                "role": "tool",
                                "tool_call_id": tr["tool_use_id"],
                                "content": tr.get("content", ""),
                            })
                        if text_parts:
                            oai.append({"role": "user", "content": " ".join(t.get("text", "") for t in text_parts)})
                else:
                    oai.append({"role": "user", "content": content})
            else:
                oai.append(msg)
        
        return oai

    def _convert_assistant_blocks(self, blocks) -> dict:
        """Convert Anthropic assistant content blocks to OpenAI assistant message."""
        text_parts = []
        tool_calls = []
        for block in blocks:
            if hasattr(block, "type"):
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": _json.dumps(block.input),
                        },
                    })
        msg = {"role": "assistant", "content": " ".join(text_parts) if text_parts else None}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        return msg

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert Anthropic-style tool defs to OpenAI-style."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    def _normalize_response(self, response) -> LLMResponse:
        """Convert OpenRouter response to normalized LLMResponse."""
        choice = response.choices[0]
        message = choice.message
        
        # Normalize finish_reason
        finish = choice.finish_reason
        if finish == "tool_calls":
            stop_reason = "tool_use"
        elif finish == "stop":
            stop_reason = "end_turn"
        elif finish == "length":
            stop_reason = "max_tokens"
        else:
            stop_reason = "end_turn"
        
        # Build content blocks
        blocks: list[ContentBlock] = []
        if message.content:
            blocks.append(TextBlock(text=message.content))
        if message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = _json.loads(args)
                blocks.append(ToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                ))
        
        return LLMResponse(stop_reason=stop_reason, content=blocks, raw=response)

    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Store assistant message in OpenRouter-native format."""
        msg = {"role": "assistant", "content": None}
        text_parts = []
        tool_calls = []
        for block in response.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": _json.dumps(block.input),
                    },
                })
        if text_parts:
            msg["content"] = " ".join(text_parts)
        if tool_calls:
            msg["tool_calls"] = tool_calls
        return msg

    def format_tool_results(self, results: list[dict]) -> list[dict]:
        """OpenRouter uses separate 'tool' role messages."""
        return [
            {"role": "tool", "tool_call_id": r["tool_use_id"], "content": r["content"]}
            for r in results
        ]
```

### 3.5 Factory Function

```python
def create_provider(provider_name: str = None) -> LLMProvider:
    """Create an LLM provider based on configuration.
    
    Args:
        provider_name: "anthropic" or "openrouter". 
                       Defaults to LLM_PROVIDER env var, then "anthropic".
    """
    name = (provider_name or os.getenv("LLM_PROVIDER", "anthropic")).lower()
    if name == "anthropic":
        return AnthropicProvider()
    elif name == "openrouter":
        return OpenRouterProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {name}. Use 'anthropic' or 'openrouter'.")
```

---

## 4. Stage-by-Stage Implementation Plan

### 4.1 Refactoring Pattern (Applied to Each Stage)

Each stage requires these minimal changes:

**Before (e.g., s01):**
```python
from anthropic import Anthropic
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# In agent_loop:
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
for block in response.content:
    if block.type == "tool_use":
        # ... use block.name, block.input, block.id
        results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
messages.append({"role": "user", "content": results})
```

**After:**
```python
from agents.llm_provider import create_provider
provider = create_provider()
MODEL = os.environ["MODEL_ID"]

# In agent_loop:
response = provider.create_message(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
messages.append(provider.format_assistant_message(response))
if response.stop_reason != "tool_use":
    return
for block in response.content:
    if block.type == "tool_use":
        # ... use block.name, block.input, block.id  (UNCHANGED)
        results.append({"tool_use_id": block.id, "content": output})
tool_msg = provider.format_tool_results(results)
if isinstance(tool_msg, list):
    messages.extend(tool_msg)
else:
    messages.append(tool_msg)
```

**Lines changed per stage: ~8–12 lines** (import, client init, create call, message formatting, tool result formatting).

### 4.2 Stage-Specific Notes

| Stage | Extra Considerations |
|-------|---------------------|
| **s01** | Simplest case. Direct substitution. |
| **s02** | Same as s01 but with 4 tools. No special handling needed. |
| **s03** | Nag reminder injects `{"type": "text"}` into user content alongside tool results. OpenRouterProvider must handle mixed content in `_convert_messages()`. |
| **s04** | Subagent creates its own `client.messages.create()` call. Both parent and child use the same `provider` instance. |
| **s05** | No special concern — skill loading is tool-based. |
| **s06** | `auto_compact()` makes a **separate** LLM call for summarization (no tools). Provider must handle tool-less calls gracefully. |
| **s07** | Standard task tools. No special handling. |
| **s08** | Background task notifications inject text into messages. Same mixed-content concern as s03. |
| **s09–s11** | Teammate threads each call `client.messages.create()`. All threads share the same `provider` instance. **Thread safety**: OpenRouter SDK uses HTTPX which is thread-safe. Anthropic SDK is also thread-safe. |
| **s12** | Standard — same pattern as s07. |
| **s_full** | Combines all mechanisms. Same provider instance shared. |

### 4.3 Handling `format_tool_results` Return Type Difference

A key design subtlety: Anthropic expects tool results as a **single user message** containing a list of `tool_result` items, while OpenRouter expects **multiple separate `tool` role messages**.

The `format_tool_results` method returns:
- **Anthropic**: `dict` (single message)
- **OpenRouter**: `list[dict]` (multiple messages)

Agent code handles this with:
```python
tool_msg = provider.format_tool_results(results)
if isinstance(tool_msg, list):
    messages.extend(tool_msg)
else:
    messages.append(tool_msg)
```

This pattern must be applied consistently across all stages.

### 4.4 Handling Mixed Content (s03, s08)

In s03, the nag reminder is injected as:
```python
results.insert(0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"})
messages.append({"role": "user", "content": results})
```

For OpenRouter, the provider's `_convert_messages()` already handles this by separating text items from tool_result items. No additional stage-specific code needed.

---

## 5. Configuration Changes

### 5.1 Updated `.env.example`

```bash
# === LLM Provider Selection ===
# Choose: "anthropic" (default) or "openrouter"
# LLM_PROVIDER=anthropic

# === Anthropic Configuration ===
ANTHROPIC_API_KEY=sk-ant-xxx
MODEL_ID=claude-sonnet-4-6

# Base URL (optional, for Anthropic-compatible providers)
# ANTHROPIC_BASE_URL=https://api.anthropic.com

# === OpenRouter Configuration ===
# OPENROUTER_API_KEY=sk-or-v1-xxx
# MODEL_ID=anthropic/claude-sonnet-4  # OpenRouter model format

# Supported Claude models on OpenRouter:
#   anthropic/claude-haiku           (Claude Haiku - fast, cheap)
#   anthropic/claude-sonnet-4        (Claude Sonnet 4 - balanced)
#   anthropic/claude-opus-4          (Claude Opus 4 - most capable)
#   anthropic/claude-sonnet-4.5      (Claude Sonnet 4.5)
#   anthropic/claude-4.5-sonnet      (alias)
#
# Non-Claude models available via OpenRouter (300+ models):
#   openai/gpt-4o
#   google/gemini-2.5-pro
#   meta-llama/llama-4-maverick
#   deepseek/deepseek-chat
#   ... and many more at https://openrouter.ai/models
```

### 5.2 Updated `requirements.txt`

```
anthropic>=0.25.0
python-dotenv>=1.0.0
openrouter>=0.1.0  # Optional: only needed when LLM_PROVIDER=openrouter
```

Note: `openrouter` is a soft dependency. If `LLM_PROVIDER=anthropic` (default), the openrouter package is not imported or needed. The import happens lazily inside `OpenRouterProvider.__init__()`.

---

## 6. Model ID Mapping

When using Claude models, the model ID format differs between providers:

| Model | Anthropic `MODEL_ID` | OpenRouter `MODEL_ID` |
|-------|----------------------|----------------------|
| Claude Haiku | `claude-haiku-4-5` | `anthropic/claude-haiku` |
| Claude Sonnet | `claude-sonnet-4-6` | `anthropic/claude-sonnet-4` |
| Claude Opus | `claude-opus-4` | `anthropic/claude-opus-4` |

The user sets `MODEL_ID` according to their chosen provider. No automatic mapping is needed — this keeps the configuration explicit and avoids magic that could surprise users.

---

## 7. Testing Plan

### 7.1 Test Structure

```
tests/
├── __init__.py
├── conftest.py                  # Shared fixtures, mock providers
├── test_llm_provider.py         # Unit tests for provider abstraction
├── test_anthropic_provider.py   # Unit tests for Anthropic adapter
├── test_openrouter_provider.py  # Unit tests for OpenRouter adapter
├── test_message_conversion.py   # Unit tests for format conversion
├── test_agent_stages.py         # Integration tests for all stages
```

### 7.2 Unit Tests: Provider Abstraction (`test_llm_provider.py`)

```python
class TestCreateProvider:
    """Test factory function."""

    def test_default_is_anthropic(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        provider = create_provider()
        assert isinstance(provider, AnthropicProvider)

    def test_explicit_anthropic(self):
        provider = create_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_explicit_openrouter(self):
        provider = create_provider("openrouter")
        assert isinstance(provider, OpenRouterProvider)

    def test_case_insensitive(self):
        provider = create_provider("OpenRouter")
        assert isinstance(provider, OpenRouterProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_provider("azure")

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        provider = create_provider()
        assert isinstance(provider, OpenRouterProvider)
```

### 7.3 Unit Tests: Anthropic Provider (`test_anthropic_provider.py`)

```python
class TestAnthropicProvider:
    """Test Anthropic provider with mocked SDK client."""

    def test_create_message_text_response(self, mock_anthropic_client):
        """Model returns text only → stop_reason='end_turn', one TextBlock."""
        provider = AnthropicProvider()
        provider._client = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value = MockResponse(
            stop_reason="end_turn",
            content=[MockTextBlock("Hello!")]
        )
        resp = provider.create_message("model", "system", [{"role": "user", "content": "hi"}])
        assert resp.stop_reason == "end_turn"
        assert len(resp.content) == 1
        assert resp.content[0].text == "Hello!"

    def test_create_message_tool_use(self, mock_anthropic_client):
        """Model calls a tool → stop_reason='tool_use', ToolUseBlock present."""
        provider = AnthropicProvider()
        provider._client = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value = MockResponse(
            stop_reason="tool_use",
            content=[MockToolUseBlock(id="tu_1", name="bash", input={"command": "ls"})]
        )
        resp = provider.create_message("model", "system", [], tools=[SAMPLE_TOOL])
        assert resp.stop_reason == "tool_use"
        assert resp.content[0].name == "bash"
        assert resp.content[0].input == {"command": "ls"}

    def test_format_assistant_message(self):
        """Assistant message wraps raw Anthropic content blocks."""
        # ...

    def test_format_tool_results(self):
        """Returns single user message with tool_result list."""
        provider = AnthropicProvider()
        result = provider.format_tool_results([
            {"tool_use_id": "tu_1", "content": "output"},
        ])
        assert result["role"] == "user"
        assert result["content"][0]["type"] == "tool_result"
        assert result["content"][0]["tool_use_id"] == "tu_1"

    def test_tools_passed_through(self, mock_anthropic_client):
        """Anthropic tool format is passed through without conversion."""
        # Verify that input_schema is not renamed to parameters
        # ...
```

### 7.4 Unit Tests: OpenRouter Provider (`test_openrouter_provider.py`)

```python
class TestOpenRouterProvider:
    """Test OpenRouter provider with mocked SDK client."""

    def test_create_message_text_response(self, mock_openrouter_client):
        """Model returns text → normalized to TextBlock."""
        provider = OpenRouterProvider()
        provider._client = mock_openrouter_client
        mock_openrouter_client.chat.send.return_value = MockChatResponse(
            finish_reason="stop",
            content="Hello!",
            tool_calls=None,
        )
        resp = provider.create_message("model", "sys", [{"role": "user", "content": "hi"}])
        assert resp.stop_reason == "end_turn"
        assert resp.content[0].text == "Hello!"

    def test_create_message_tool_calls(self, mock_openrouter_client):
        """Model calls tools → normalized to ToolUseBlock."""
        provider = OpenRouterProvider()
        provider._client = mock_openrouter_client
        mock_openrouter_client.chat.send.return_value = MockChatResponse(
            finish_reason="tool_calls",
            content=None,
            tool_calls=[MockToolCall(id="tc_1", name="bash", arguments='{"command":"ls"}')],
        )
        resp = provider.create_message("model", "sys", [], tools=[SAMPLE_TOOL])
        assert resp.stop_reason == "tool_use"
        assert resp.content[0].name == "bash"
        assert resp.content[0].input == {"command": "ls"}

    def test_format_tool_results_returns_list(self):
        """OpenRouter returns list of tool messages."""
        provider = OpenRouterProvider()
        results = provider.format_tool_results([
            {"tool_use_id": "tc_1", "content": "output"},
        ])
        assert isinstance(results, list)
        assert results[0]["role"] == "tool"
        assert results[0]["tool_call_id"] == "tc_1"

    def test_system_prompt_injected_as_message(self, mock_openrouter_client):
        """System prompt becomes first message with role='system'."""
        provider = OpenRouterProvider()
        provider._client = mock_openrouter_client
        mock_openrouter_client.chat.send.return_value = MockChatResponse(
            finish_reason="stop", content="ok", tool_calls=None
        )
        provider.create_message("m", "You are helpful.", [{"role": "user", "content": "hi"}])
        call_args = mock_openrouter_client.chat.send.call_args
        msgs = call_args.kwargs["messages"]
        assert msgs[0] == {"role": "system", "content": "You are helpful."}
        assert msgs[1] == {"role": "user", "content": "hi"}
```

### 7.5 Unit Tests: Message Format Conversion (`test_message_conversion.py`)

```python
class TestMessageConversion:
    """Test Anthropic→OpenAI message format conversion."""

    def test_convert_tool_results(self):
        """Anthropic tool results in user message → OpenAI tool messages."""
        provider = OpenRouterProvider()
        messages = [
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "file.txt"},
            ]},
        ]
        oai = provider._convert_messages("", messages)
        assert oai[0]["role"] == "tool"
        assert oai[0]["tool_call_id"] == "tu_1"

    def test_convert_mixed_content_with_reminder(self):
        """Nag reminder text + tool results in same user message."""
        provider = OpenRouterProvider()
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "<reminder>Update todos</reminder>"},
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "done"},
            ]},
        ]
        oai = provider._convert_messages("", messages)
        # Should produce both a tool message and a user message
        roles = [m["role"] for m in oai]
        assert "tool" in roles
        assert "user" in roles

    def test_convert_tool_definitions(self):
        """Anthropic flat tool defs → OpenAI nested function format."""
        provider = OpenRouterProvider()
        tools = [{"name": "bash", "description": "Run command",
                  "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}}}]
        oai_tools = provider._convert_tools(tools)
        assert oai_tools[0]["type"] == "function"
        assert oai_tools[0]["function"]["name"] == "bash"
        assert oai_tools[0]["function"]["parameters"]["type"] == "object"

    def test_empty_system_prompt(self):
        """Empty system prompt should not inject a system message."""
        provider = OpenRouterProvider()
        oai = provider._convert_messages("", [{"role": "user", "content": "hi"}])
        assert oai[0]["role"] == "user"

    def test_roundtrip_preservation(self):
        """Messages formatted by provider can be read back correctly."""
        # ...
```

### 7.6 Integration Tests: Agent Stages (`test_agent_stages.py`)

These tests verify each stage works end-to-end with a mocked provider.

```python
class MockProvider(LLMProvider):
    """Mock provider that returns scripted responses."""
    def __init__(self, responses: list[LLMResponse]):
        self._responses = iter(responses)
    
    def create_message(self, model, system, messages, tools=None, max_tokens=8000):
        return next(self._responses)
    
    def format_assistant_message(self, response):
        return {"role": "assistant", "content": [
            {"type": b.type, **({"text": b.text} if hasattr(b, "text") else {"id": b.id, "name": b.name, "input": b.input})}
            for b in response.content
        ]}
    
    def format_tool_results(self, results):
        return {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": r["tool_use_id"], "content": r["content"]}
            for r in results
        ]}


class TestS01AgentLoop:
    """Verify s01 agent loop works with mock provider."""

    def test_single_tool_call_then_text(self, tmp_path):
        """Agent calls bash once, then returns text."""
        provider = MockProvider([
            LLMResponse(stop_reason="tool_use", content=[
                ToolUseBlock(id="1", name="bash", input={"command": "echo hello"})
            ]),
            LLMResponse(stop_reason="end_turn", content=[
                TextBlock(text="Done!")
            ]),
        ])
        messages = [{"role": "user", "content": "say hello"}]
        # agent_loop(messages, provider)  # Pass provider
        # assert messages[-1] contains text "Done!"

    def test_no_tool_call(self):
        """Model responds with text only — loop exits immediately."""
        # ...


class TestS04Subagent:
    """Verify subagent uses same provider."""

    def test_subagent_gets_provider(self):
        """Child agent should use the same provider instance."""
        # ...


class TestS06ContextCompact:
    """Verify auto_compact works with provider."""

    def test_auto_compact_uses_provider_for_summary(self):
        """Summarization call goes through provider.create_message()."""
        # ...
```

### 7.7 Negative Test Cases

```python
class TestErrorHandling:
    """Test error scenarios."""

    def test_openrouter_invalid_api_key(self):
        """OpenRouter returns 401 → should propagate as readable error."""
        # ...

    def test_openrouter_rate_limit(self):
        """OpenRouter returns 429 → should propagate."""
        # ...

    def test_malformed_tool_call_arguments(self):
        """OpenRouter returns non-JSON arguments → handle gracefully."""
        provider = OpenRouterProvider()
        # Mock response with malformed arguments
        # Should not crash; should return error content

    def test_missing_api_key_anthropic(self):
        """No ANTHROPIC_API_KEY → clear error on init."""
        # ...

    def test_missing_api_key_openrouter(self):
        """No OPENROUTER_API_KEY → clear error on first call."""
        # ...

    def test_provider_timeout(self):
        """API call times out → should propagate."""
        # ...

    def test_empty_response_content(self):
        """Model returns empty content → should not crash."""
        # ...
```

### 7.8 Test Configuration

```ini
# pytest.ini or pyproject.toml [tool.pytest.ini_options]
[pytest]
testpaths = tests
markers =
    unit: Unit tests (no external API calls)
    integration: Integration tests (may use mock or real API)
    slow: Tests that take >5s
```

---

## 8. Performance Considerations

| Concern | Impact | Mitigation |
|---------|--------|------------|
| **Extra abstraction layer overhead** | Negligible. `create_message()` adds ~0.1ms of Python overhead vs. multi-second API latency. | No action needed. |
| **Message format conversion** | O(n) in message count. For typical conversations (<100 messages), this is <1ms. | No action needed for typical use. For s06 compacted conversations, messages are already short. |
| **OpenRouter SDK HTTP client** | Uses HTTPX connection pooling internally. | Reuse single `OpenRouter()` instance (already the design). |
| **Thread safety (s09-s11)** | Multiple teammate threads share one provider. Both Anthropic and OpenRouter SDKs are thread-safe. | No extra locking needed. |
| **Lazy import** | `from openrouter import OpenRouter` only happens when `LLM_PROVIDER=openrouter`. | No penalty for Anthropic-only users. |

---

## 9. Implementation Sequence

### Phase 1: Core Provider Layer (Priority: P0)
1. Create `agents/llm_provider.py` with all types, abstract class, both providers, and factory.
2. Write `tests/test_llm_provider.py`, `tests/test_anthropic_provider.py`, `tests/test_openrouter_provider.py`, `tests/test_message_conversion.py`.
3. Validate all unit tests pass.

### Phase 2: Refactor Agent Stages (Priority: P0)
4. Refactor `s01_agent_loop.py` — the simplest stage. Verify manually with both providers.
5. Refactor `s02_tool_use.py` through `s08_background_tasks.py` using the same pattern.
6. Refactor `s09_agent_teams.py` through `s12_worktree_task_isolation.py` — these have teammate threads that also need the provider.
7. Refactor `s_full.py`.

### Phase 3: Configuration & Documentation (Priority: P1)
8. Update `.env.example` with OpenRouter configuration section.
9. Update `requirements.txt` to add `openrouter` as optional dependency.
10. Update `README.md` Quick Start section to mention OpenRouter option.

### Phase 4: Integration Testing (Priority: P1)
11. Write integration tests in `tests/test_agent_stages.py` using MockProvider.
12. Manual end-to-end testing with real OpenRouter API key.

### Estimated Effort

| Task | Effort |
|------|--------|
| `llm_provider.py` | 2 hours |
| Unit tests for provider | 2 hours |
| Refactor s01–s08 (8 files) | 2 hours |
| Refactor s09–s12 + s_full (5 files) | 2 hours |
| Configuration + docs | 1 hour |
| Integration tests | 2 hours |
| Manual E2E testing | 1 hour |
| **Total** | **~12 hours** |

---

## 10. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenRouter SDK breaks backward compat | Medium | High | Pin `openrouter>=0.1.0,<1.0` in requirements |
| Model-specific tool calling quirks via OpenRouter | Medium | Medium | Document tested models; add model-specific tests |
| Teaching clarity reduced by abstraction | Low | Medium | Keep `llm_provider.py` well-commented; each stage's diff is small and obvious |
| Thread safety issue in providers | Low | High | Both SDKs document thread safety; add threading tests |
| OpenRouter free-tier rate limits in CI | Medium | Low | Mock all API calls in CI; use real API only in manual E2E |

---

## 11. Summary of Changes per File

| File | Change Type | Description |
|------|-------------|-------------|
| `agents/llm_provider.py` | **NEW** | Provider abstraction, types, Anthropic/OpenRouter adapters, factory |
| `agents/s01_agent_loop.py` | MODIFY | Replace `Anthropic()` + `client.messages.create()` with provider |
| `agents/s02_tool_use.py` | MODIFY | Same pattern |
| `agents/s03_todo_write.py` | MODIFY | Same pattern + handle mixed content in tool results |
| `agents/s04_subagent.py` | MODIFY | Same pattern for both parent and child loops |
| `agents/s05_skill_loading.py` | MODIFY | Same pattern |
| `agents/s06_context_compact.py` | MODIFY | Same pattern + use provider for summarization call |
| `agents/s07_task_system.py` | MODIFY | Same pattern |
| `agents/s08_background_tasks.py` | MODIFY | Same pattern |
| `agents/s09_agent_teams.py` | MODIFY | Same pattern + teammate loops use shared provider |
| `agents/s10_team_protocols.py` | MODIFY | Same pattern + teammate loops use shared provider |
| `agents/s11_autonomous_agents.py` | MODIFY | Same pattern + teammate loops use shared provider |
| `agents/s12_worktree_task_isolation.py` | MODIFY | Same pattern |
| `agents/s_full.py` | MODIFY | Same pattern (all mechanisms combined) |
| `.env.example` | MODIFY | Add OpenRouter config section |
| `requirements.txt` | MODIFY | Add `openrouter>=0.1.0` |
| `tests/` | **NEW** | All test files |

---

## Appendix A: Complete `llm_provider.py` Skeleton

See Section 3.1–3.5 for the complete module design. The module is ~250 lines of Python with no external dependencies beyond the provider SDKs (imported lazily).

## Appendix B: OpenRouter Model Routing

OpenRouter supports provider routing preferences. The `OpenRouterProvider` can be extended later to support:
```python
provider_config = {
    "sort": "price",        # Route by cheapest provider
    "zdr": True,            # Zero data retention
    "allow_fallbacks": True # Fall back to alternative providers
}
```

This is not in scope for the initial implementation but the architecture supports it via kwargs pass-through in `create_message()`.
