# OpenRouter Integration Implementation Plan
## for `learn-claude-code` Agent Framework

**Document Version:** 1.0  
**Author:** Open Router Plan Agent  
**Target Repository:** `learn-claude-code` (s01–s12 + s_full agent stages)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Analysis](#architecture-analysis)
3. [Critical Design Decisions](#critical-design-decisions)
4. [Integration Architecture](#integration-architecture)
5. [Phase 1: Provider Abstraction Layer](#phase-1-provider-abstraction-layer)
6. [Phase 2: Configuration System](#phase-2-configuration-system)
7. [Phase 3: Refactor Agent Stages](#phase-3-refactor-agent-stages)
8. [Phase 4: Testing Framework](#phase-4-testing-framework)
9. [Phase 5: Documentation & CI Updates](#phase-5-documentation--ci-updates)
10. [Trade-offs & Justifications](#trade-offs--justifications)
11. [Missing Information & Clarifying Questions](#missing-information--clarifying-questions)

---

## Executive Summary

The `learn-claude-code` project currently uses the Anthropic Python SDK (`anthropic>=0.25.0`) exclusively across all 12 progressive agent stages. Each stage hardcodes `Anthropic(base_url=...)` client instantiation and relies on Anthropic-specific response types (`response.stop_reason`, `response.content`, `block.type`, `block.id`, etc.).

This plan introduces **OpenRouter** as a second LLM provider by:
1. Creating a **common provider interface** (Protocol class) with normalized response types
2. Implementing **ClaudeProvider** (wraps existing Anthropic SDK) and **OpenRouterProvider** (wraps `openrouter` Python SDK)
3. Refactoring each of the 12 agent stages to use the provider interface with **zero change to agent logic**
4. Providing a **configuration switch** via environment variables (`LLM_PROVIDER=claude|openrouter`)
5. Adding **comprehensive unit tests** using mock providers

**Key Insight:** The `.env.example` already documents Anthropic-compatible base URL switching (for MiniMax, GLM, Kimi, DeepSeek). OpenRouter's primary API is OpenAI-compatible (not Anthropic-compatible), making it fundamentally different — it requires a proper translation layer, not just a URL swap.

---

## Architecture Analysis

### Current Architecture (Uniform Pattern Across All Stages)

```
.env (ANTHROPIC_API_KEY, MODEL_ID, ANTHROPIC_BASE_URL)
       |
       v
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
       |
       v
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,      ← Anthropic-specific: separate system param
    messages=messages,  ← Anthropic message format
    tools=TOOLS,        ← Anthropic tool schema format
    max_tokens=8000,
)
       |
       v
response.stop_reason  → "tool_use" | "end_turn" | "max_tokens"
response.content      → List[TextBlock | ToolUseBlock]
  block.type          → "tool_use" | "text"
  block.id            → tool call ID
  block.name          → tool name
  block.input         → dict of tool arguments
  block.text          → text content
```

### API Differences: Anthropic vs OpenRouter

| Aspect | Anthropic SDK | OpenRouter SDK |
|--------|--------------|----------------|
| Client class | `Anthropic(api_key, base_url)` | `OpenRouter(api_key, http_referer, x_title)` |
| API call | `client.messages.create(model, system, messages, tools, max_tokens)` | `client.chat.send(model, messages, tools, max_tokens)` |
| System prompt | Separate `system` parameter | `{"role": "system", "content": ...}` prepended to messages |
| Stop condition | `response.stop_reason == "tool_use"` | `response.choices[0].finish_reason == "tool_calls"` |
| Response content | `response.content` = list of typed blocks | `response.choices[0].message` |
| Tool calls | `block.type == "tool_use"` with `block.id/name/input` | `message.tool_calls[i].id/function.name/function.arguments` |
| Text content | `block.text` | `message.content` |
| Tool definition | `{"name":…, "description":…, "input_schema":{…}}` | `{"type":"function","function":{"name":…,"description":…,"parameters":{…}}}` |
| Tool result message | `{"role":"user","content":[{"type":"tool_result","tool_use_id":…,"content":…}]}` | `{"role":"tool","tool_call_id":…,"content":…}` |
| Assistant message with tools | `{"role":"assistant","content":[ToolUseBlock(…)]}` | `{"role":"assistant","content":null,"tool_calls":[…]}` |

### Stage-by-Stage LLM Usage Summary

| Stage | LLM Calls | Complexity | Special Notes |
|-------|-----------|-----------|---------------|
| s01 | 1 client, 1 call site in `agent_loop()` | Low | Baseline |
| s02 | 1 client, 1 call site in `agent_loop()` | Low | Identical to s01 |
| s03 | 1 client, 1 call site in `agent_loop()` | Low | Same pattern |
| s04 | 1 client, **2 call sites**: `agent_loop()` + `run_subagent()` | Medium | Subagent uses same client |
| s05 | 1 client, 1 call site in `agent_loop()` | Low | Same as s02 |
| s06 | 1 client, **2 call sites**: `agent_loop()` + `auto_compact()` | Medium | `auto_compact()` calls LLM for summarization |
| s07 | 1 client, 1 call site in `agent_loop()` | Low | Same as s02 |
| s08 | 1 client, 1 call site in `agent_loop()` | Low | Same as s02 |
| s09 | 1 client, **2 call sites**: `agent_loop()` + `_teammate_loop()` in thread | High | Each teammate thread calls LLM |
| s10 | 1 client, **2 call sites**: `agent_loop()` + `_teammate_loop()` in thread | High | Protocol FSM over teammate LLM calls |
| s11 | 1 client, **2 call sites**: `agent_loop()` + `_loop()` in thread | High | Autonomous idle-work cycle |
| s12 | 1 client, 1 call site in `agent_loop()` | Low | Worktree isolation |
| s_full | 1 client, **3+ call sites**: lead loop + subagent + teammate threads | Very High | All mechanisms combined |

---

## Critical Design Decisions

### Decision 1: Provider Abstraction via Protocol + Dataclasses ✅ CHOSEN

**Approach:** Define a `LLMProvider` Protocol class and normalized response dataclasses that mimic the Anthropic SDK's interface. Each agent stage uses the provider via the common interface.

**Justification:**
- **Zero agent logic change**: The normalized response objects have the same `.type`, `.id`, `.name`, `.input`, `.text` attributes as Anthropic typed blocks. Only the initialization code changes.
- **Testability**: Mock providers can be injected without network calls.
- **Extensibility**: Adding a third provider (e.g., Gemini) requires only a new provider implementation.

**Rejected Alternatives:**
- *Anthropic-compatible base URL*: Simple but limited. OpenRouter doesn't fully implement the Anthropic `/v1/messages` endpoint for all non-Anthropic models. Only works for `anthropic/claude-*` models.
- *OpenAI SDK + base URL*: Still requires message format translation; no real advantage over using the proper OpenRouter SDK.
- *Full message format migration to dicts*: Would require extensive changes across all 12 stages and break the teaching clarity.

### Decision 2: OpenRouter Python SDK (`openrouter` package) ✅ CHOSEN

**Justification:**
- Official SDK with type safety (Pydantic-validated), auto-generated from OpenRouter's OpenAPI spec.
- Provides access to ALL OpenRouter features (provider routing, `zdr`, model fallbacks) — not just compatibility.
- `client.chat.send(messages, model, tools, max_tokens)` is clean and explicit.

**Rejected Alternative:** Using `openai` library with `base_url="https://openrouter.ai/api/v1"`:
- Works but requires managing the OpenAI SDK version compatibility.
- Loses OpenRouter-specific features (provider hints, routing preferences).
- Less educational value for learners.

### Decision 3: Messages Stored in Internal Normalized Format ✅ CHOSEN

**Key Challenge:** After each LLM call, `messages.append({"role":"assistant","content":response.content})` stores Anthropic-typed objects. When messages are sent back on the next loop iteration, the provider must serialize them correctly.

**Solution:** Store messages with **normalized dataclass objects** (`NormalizedToolUseBlock`, `NormalizedTextBlock`). Each provider's `create_message()` converts these internally to its own wire format before the API call.

This means:
- `ClaudeProvider.create_message()` converts `NormalizedToolUseBlock → {"type":"tool_use", ...}` dict (Anthropic SDK accepts dicts)
- `OpenRouterProvider.create_message()` converts `NormalizedToolUseBlock → {"id":..., "type":"function", "function":{...}}` for OpenAI format
- The agent loop code is completely unchanged after initial refactoring

---

## Integration Architecture

### File Structure

```
agents/
├── providers/                    ← NEW: provider abstraction layer
│   ├── __init__.py               ← exports: create_provider, load_config, NormalizedResponse...
│   ├── base.py                   ← LLMProvider Protocol, NormalizedResponse, NormalizedTextBlock,
│   │                               NormalizedToolUseBlock
│   ├── claude.py                 ← ClaudeProvider (wraps anthropic.Anthropic)
│   ├── openrouter.py             ← OpenRouterProvider (wraps openrouter.OpenRouter)
│   └── config.py                 ← ProviderConfig, load_config(), create_provider()
├── s01_agent_loop.py             ← REFACTORED: replace client → provider
├── s02_tool_use.py               ← REFACTORED
├── s03_todo_write.py             ← REFACTORED
├── s04_subagent.py               ← REFACTORED
├── s05_skill_loading.py          ← REFACTORED
├── s06_context_compact.py        ← REFACTORED (2 LLM call sites)
├── s07_task_system.py            ← REFACTORED
├── s08_background_tasks.py       ← REFACTORED
├── s09_agent_teams.py            ← REFACTORED (2 LLM call sites, threads)
├── s10_team_protocols.py         ← REFACTORED (2 LLM call sites, threads)
├── s11_autonomous_agents.py      ← REFACTORED (2 LLM call sites, threads)
├── s12_worktree_task_isolation.py ← REFACTORED
└── s_full.py                     ← REFACTORED (3+ LLM call sites)

tests/
├── providers/
│   ├── test_base.py
│   ├── test_claude_provider.py
│   ├── test_openrouter_provider.py
│   └── test_config.py
└── agents/
    ├── test_s01_agent_loop.py
    ├── test_s02_tool_use.py
    ├── test_s04_subagent.py
    ├── test_s06_context_compact.py
    └── test_s09_agent_teams.py

.env.example                      ← UPDATED: add OpenRouter config section
requirements.txt                  ← UPDATED: add openrouter>=0.x.x
```

---

## Phase 1: Provider Abstraction Layer

### Step 1.1: Create `agents/providers/base.py`

**Purpose:** Define normalized response types and the `LLMProvider` Protocol.

**Expected Outcome:** Normalized response objects that mimic Anthropic SDK's interface so existing agent code works with zero changes after provider injection.

```python
# agents/providers/base.py
"""
LLM Provider abstraction layer.

Defines the common interface and normalized response types used across
all agent stages (s01-s12). Both ClaudeProvider and OpenRouterProvider
implement this interface.

Normalized response objects mimic the Anthropic SDK's attribute interface
(.type, .id, .name, .input, .text) so agent loop code requires no changes
when switching providers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Union


@dataclass
class NormalizedTextBlock:
    """Normalized text block — mirrors anthropic.types.TextBlock."""
    type: str = "text"
    text: str = ""


@dataclass
class NormalizedToolUseBlock:
    """
    Normalized tool use block — mirrors anthropic.types.ToolUseBlock.
    
    Attributes match the Anthropic SDK so agent loop code can use
    block.type, block.id, block.name, block.input unchanged.
    """
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)


ContentBlock = Union[NormalizedTextBlock, NormalizedToolUseBlock]


@dataclass
class NormalizedResponse:
    """
    Normalized LLM response — provider-independent.
    
    stop_reason: "tool_use" (model wants to call a tool) or "end_turn" (done).
    content: list of NormalizedTextBlock and/or NormalizedToolUseBlock.
    """
    stop_reason: str  # "tool_use" | "end_turn"
    content: List[ContentBlock]


class LLMProvider(Protocol):
    """
    Common interface for LLM providers.
    
    All agent stages use this interface exclusively. Provider-specific
    initialization, message format conversion, and response normalization
    are encapsulated inside each implementation.
    """

    def create_message(
        self,
        model: str,
        system: str,
        messages: List[Dict],
        tools: List[Dict],
        max_tokens: int = 8000,
    ) -> NormalizedResponse:
        """
        Send messages to the LLM and return a normalized response.
        
        Handles all format conversions (tools, messages, system prompt)
        internally. Returns NormalizedResponse with stop_reason and content
        using the standard normalized block types.
        """
        ...

    def response_to_assistant_message(
        self, response: NormalizedResponse
    ) -> Dict:
        """
        Convert a NormalizedResponse to an assistant message dict suitable
        for appending to the messages list for the next LLM call.
        
        Returns: {"role": "assistant", "content": List[ContentBlock]}
        The content list contains NormalizedToolUseBlock/NormalizedTextBlock
        objects that both providers can serialize on the next call.
        """
        ...
```

**Testing Plan:**
- Verify `NormalizedTextBlock` has correct default values
- Verify `NormalizedToolUseBlock` attribute access mirrors Anthropic types
- Verify `NormalizedResponse` stores stop_reason and content correctly
- Type checking with `mypy` or `pyright`

---

### Step 1.2: Create `agents/providers/claude.py`

**Purpose:** Wrap the existing Anthropic SDK with the `LLMProvider` interface.

**Expected Outcome:** `ClaudeProvider` passes all existing test scenarios unchanged; the Anthropic SDK is still used under the hood.

```python
# agents/providers/claude.py
"""
Claude provider: wraps anthropic.Anthropic to implement LLMProvider.

Message format translation (NormalizedToolUseBlock → Anthropic dict)
happens inside create_message() so the agent loop code is unchanged.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic

from .base import (
    ContentBlock,
    NormalizedResponse,
    NormalizedTextBlock,
    NormalizedToolUseBlock,
)


class ClaudeProvider:
    """
    LLM provider backed by Anthropic's claude models.
    
    Supports all ANTHROPIC_BASE_URL-compatible providers (MiniMax, GLM,
    Kimi, DeepSeek) by passing through the base_url parameter.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.client = Anthropic(api_key=api_key, base_url=base_url)

    def create_message(
        self,
        model: str,
        system: str,
        messages: List[Dict],
        tools: List[Dict],
        max_tokens: int = 8000,
    ) -> NormalizedResponse:
        """
        Call Anthropic API and return a NormalizedResponse.
        
        Converts messages containing NormalizedToolUseBlock objects to
        Anthropic dict format before the API call.
        """
        # Convert normalized message blocks to Anthropic-compatible dicts
        converted = self._convert_messages(messages)
        
        response = self.client.messages.create(
            model=model,
            system=system,
            messages=converted,
            tools=tools,
            max_tokens=max_tokens,
        )
        return self._normalize_response(response)

    def response_to_assistant_message(
        self, response: NormalizedResponse
    ) -> Dict:
        """Return assistant message dict with normalized content blocks."""
        return {"role": "assistant", "content": response.content}

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Convert messages list for the Anthropic SDK.
        
        NormalizedToolUseBlock → {"type":"tool_use", "id":..., ...}
        NormalizedTextBlock    → {"type":"text", "text":...}
        
        Raw Anthropic SDK objects are passed through unchanged.
        """
        result = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                converted_content = []
                for block in content:
                    if isinstance(block, NormalizedToolUseBlock):
                        converted_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                    elif isinstance(block, NormalizedTextBlock):
                        converted_content.append({
                            "type": "text",
                            "text": block.text,
                        })
                    else:
                        # Raw Anthropic SDK objects or existing dicts
                        converted_content.append(block)
                result.append({**msg, "content": converted_content})
            else:
                result.append(msg)
        return result

    def _normalize_response(self, response: Any) -> NormalizedResponse:
        """Convert Anthropic SDK response to NormalizedResponse."""
        content: List[ContentBlock] = []
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                content.append(NormalizedToolUseBlock(
                    type="tool_use",
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))
            else:
                text = getattr(block, "text", "")
                content.append(NormalizedTextBlock(type="text", text=text))
        
        stop_reason = (
            "tool_use"
            if response.stop_reason == "tool_use"
            else "end_turn"
        )
        return NormalizedResponse(stop_reason=stop_reason, content=content)
```

**Testing Plan (Positive):**
- Mock `Anthropic.messages.create` → return a response with `stop_reason="tool_use"` and ToolUseBlock content
- Assert `NormalizedResponse.stop_reason == "tool_use"`
- Assert `NormalizedResponse.content[0]` is `NormalizedToolUseBlock` with correct id/name/input
- Test with `stop_reason="end_turn"` → `NormalizedResponse.stop_reason == "end_turn"`
- Test `_convert_messages` with NormalizedToolUseBlock objects in messages → correct dict format

**Testing Plan (Negative):**
- Mock `Anthropic.messages.create` → raise `anthropic.APIError` → assert propagates
- Test `_convert_messages` with None content → no crash
- Test `_convert_messages` with string content → no crash

---

### Step 1.3: Create `agents/providers/openrouter.py`

**Purpose:** Wrap the `openrouter` Python SDK with the `LLMProvider` interface, translating between Anthropic message format and OpenAI/OpenRouter format.

**Expected Outcome:** `OpenRouterProvider.create_message()` accepts the same inputs as `ClaudeProvider` and returns an identical `NormalizedResponse`.

```python
# agents/providers/openrouter.py
"""
OpenRouter provider: wraps openrouter.OpenRouter SDK to implement LLMProvider.

Translation layers:
  1. Tools: Anthropic {name, description, input_schema} 
             → OpenAI {type:"function", function:{name, description, parameters}}
  2. Messages: Anthropic list-of-blocks format 
               → OpenAI role/content/tool_calls format
  3. Response: OpenAI choices[0].message 
               → NormalizedResponse with NormalizedToolUseBlock

System prompt: Anthropic separate 'system' param 
               → OpenAI {"role":"system","content":...} prepended to messages
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from openrouter import OpenRouter

from .base import (
    ContentBlock,
    NormalizedResponse,
    NormalizedTextBlock,
    NormalizedToolUseBlock,
)


class OpenRouterProvider:
    """
    LLM provider backed by OpenRouter, supporting 300+ models.
    
    Uses the official openrouter Python SDK for type-safe API access.
    Translates between Anthropic-style message format (used internally
    in all agent stages) and OpenAI-style format required by OpenRouter.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
    ):
        self.client = OpenRouter(
            api_key=api_key,
            http_referer=http_referer or "https://github.com/shareAI-lab/learn-claude-code",
            x_title=x_title or "learn-claude-code",
        )

    def create_message(
        self,
        model: str,
        system: str,
        messages: List[Dict],
        tools: List[Dict],
        max_tokens: int = 8000,
    ) -> NormalizedResponse:
        """
        Call OpenRouter API and return a NormalizedResponse.
        
        Full translation pipeline:
        1. Convert tools to OpenAI function-calling format
        2. Prepend system prompt as {"role":"system"} message
        3. Convert messages (Anthropic format → OpenAI format)
        4. Call client.chat.send()
        5. Normalize response to NormalizedResponse
        """
        oai_tools = self._convert_tools(tools)
        oai_messages = self._convert_messages(system, messages)
        
        response = self.client.chat.send(
            model=model,
            messages=oai_messages,
            tools=oai_tools if oai_tools else None,
            max_tokens=max_tokens,
        )
        return self._normalize_response(response)

    def response_to_assistant_message(
        self, response: NormalizedResponse
    ) -> Dict:
        """Return assistant message dict with normalized content blocks."""
        return {"role": "assistant", "content": response.content}

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert Anthropic tool definitions to OpenAI function format.
        
        Anthropic: {"name":…, "description":…, "input_schema":{…}}
        OpenAI:    {"type":"function","function":{"name":…,"description":…,"parameters":{…}}}
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {
                        "type": "object",
                        "properties": {}
                    }),
                },
            }
            for tool in tools
        ]

    def _convert_messages(
        self, system: str, messages: List[Dict]
    ) -> List[Dict]:
        """
        Convert Anthropic-format messages to OpenAI-format messages.
        
        Prepends system prompt. Translates:
        - assistant messages with NormalizedToolUseBlock → tool_calls format
        - user messages with tool_result dicts → {"role":"tool"} messages
        - Plain string content passes through unchanged
        """
        result = []
        
        # System prompt as first message
        if system:
            result.append({"role": "system", "content": system})
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content")
            
            if role == "assistant":
                if isinstance(content, list):
                    text_parts = []
                    tool_calls = []
                    for block in content:
                        if isinstance(block, NormalizedToolUseBlock):
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input),
                                },
                            })
                        elif isinstance(block, NormalizedTextBlock):
                            if block.text:
                                text_parts.append(block.text)
                        elif isinstance(block, dict):
                            # Handle raw dict blocks (tool_use or text dicts)
                            if block.get("type") == "tool_use":
                                tool_calls.append({
                                    "id": block["id"],
                                    "type": "function",
                                    "function": {
                                        "name": block["name"],
                                        "arguments": json.dumps(block.get("input", {})),
                                    },
                                })
                            elif block.get("type") == "text":
                                if block.get("text"):
                                    text_parts.append(block["text"])
                        elif hasattr(block, "type"):
                            # Handle Anthropic SDK typed objects
                            if block.type == "tool_use":
                                tool_calls.append({
                                    "id": block.id,
                                    "type": "function",
                                    "function": {
                                        "name": block.name,
                                        "arguments": json.dumps(block.input),
                                    },
                                })
                            elif block.type == "text":
                                if hasattr(block, "text") and block.text:
                                    text_parts.append(block.text)
                    
                    oai_msg = {
                        "role": "assistant",
                        "content": " ".join(text_parts) or None,
                    }
                    if tool_calls:
                        oai_msg["tool_calls"] = tool_calls
                    result.append(oai_msg)
                else:
                    result.append({"role": "assistant", "content": str(content or "")})

            elif role == "user":
                if isinstance(content, list):
                    # Check if this is a tool_result batch or mixed content
                    tool_results = []
                    text_parts = []
                    reminder_parts = []
                    
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "tool_result":
                                # Convert Anthropic tool_result → OpenAI tool role
                                tool_results.append({
                                    "role": "tool",
                                    "tool_call_id": item["tool_use_id"],
                                    "content": str(item.get("content", "")),
                                })
                            elif item.get("type") == "text":
                                reminder_parts.append(item["text"])
                            else:
                                text_parts.append(str(item))
                        else:
                            text_parts.append(str(item))
                    
                    # Add reminder text first (e.g. todo nag from s03)
                    if reminder_parts:
                        result.append({"role": "user", "content": "\n".join(reminder_parts)})
                    # Add tool results as individual tool messages
                    result.extend(tool_results)
                    # Add any remaining text
                    if text_parts:
                        result.append({"role": "user", "content": "\n".join(text_parts)})
                else:
                    result.append({"role": "user", "content": str(content or "")})
            
            else:
                # Pass through any other roles (e.g. "system" injected by agent)
                result.append(msg)
        
        return result

    def _normalize_response(self, response: Any) -> NormalizedResponse:
        """Convert OpenRouter/OpenAI response to NormalizedResponse."""
        choice = response.choices[0]
        finish_reason = choice.finish_reason or ""
        message = choice.message
        
        content: List[ContentBlock] = []
        
        # Text content
        if message.content:
            content.append(NormalizedTextBlock(
                type="text",
                text=message.content,
            ))
        
        # Tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                try:
                    tool_input = json.loads(tc.function.arguments or "{}")
                except (json.JSONDecodeError, AttributeError):
                    tool_input = {}
                content.append(NormalizedToolUseBlock(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=tool_input,
                ))
        
        stop_reason = (
            "tool_use"
            if finish_reason in ("tool_calls", "function_call")
            else "end_turn"
        )
        return NormalizedResponse(stop_reason=stop_reason, content=content)
```

**Testing Plan (Positive):**
- Mock `OpenRouter.chat.send` → return response with `finish_reason="tool_calls"` and tool_calls
- Assert `NormalizedResponse.stop_reason == "tool_use"`
- Assert `NormalizedResponse.content[0]` is `NormalizedToolUseBlock` with correct id/name/input (JSON deserialized)
- Test `_convert_tools` with Anthropic tool defs → correct OpenAI format
- Test `_convert_messages` with NormalizedToolUseBlock in assistant message → tool_calls format
- Test `_convert_messages` with tool_result dicts in user message → `{"role":"tool"}` messages
- Test system prompt prepend
- Test `finish_reason="stop"` → `NormalizedResponse.stop_reason == "end_turn"`

**Testing Plan (Negative):**
- Mock `OpenRouter.chat.send` → raise connection error → assert propagates
- Test `_normalize_response` with `message.tool_calls = None` → no crash, empty content
- Test `_normalize_response` with malformed JSON in `tc.function.arguments` → empty dict fallback
- Test `_convert_messages` with empty messages list → only system message

---

### Step 1.4: Create `agents/providers/config.py`

**Purpose:** Environment-based configuration loading and provider factory.

```python
# agents/providers/config.py
"""
Provider configuration: load from environment, create provider instance.

Environment variables:
  LLM_PROVIDER          = "claude" (default) | "openrouter"
  MODEL_ID              = model identifier (format depends on provider)
  
For Claude:
  ANTHROPIC_API_KEY     = sk-ant-xxx
  ANTHROPIC_BASE_URL    = optional, for compatible providers (MiniMax, GLM...)

For OpenRouter:
  OPENROUTER_API_KEY    = sk-or-xxx
  OPENROUTER_HTTP_REFERER = optional, your app URL
  OPENROUTER_X_TITLE    = optional, your app display name
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .base import LLMProvider


class ProviderType(str, Enum):
    CLAUDE = "claude"
    OPENROUTER = "openrouter"


@dataclass
class ProviderConfig:
    provider: ProviderType
    model: str
    
    # Claude-specific
    anthropic_api_key: Optional[str] = None
    anthropic_base_url: Optional[str] = None
    
    # OpenRouter-specific
    openrouter_api_key: Optional[str] = None
    openrouter_http_referer: Optional[str] = None
    openrouter_x_title: Optional[str] = None


def load_config() -> ProviderConfig:
    """
    Load provider configuration from environment variables.
    
    Defaults to Claude if LLM_PROVIDER is not set.
    """
    provider_str = os.getenv("LLM_PROVIDER", "claude").lower().strip()
    
    try:
        provider = ProviderType(provider_str)
    except ValueError:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_str}'. "
            f"Valid values: {[p.value for p in ProviderType]}"
        )
    
    model = os.getenv("MODEL_ID", "")
    if not model:
        # Provide sensible defaults per provider
        defaults = {
            ProviderType.CLAUDE: "claude-sonnet-4-6",
            ProviderType.OPENROUTER: "anthropic/claude-sonnet-4-6",
        }
        model = defaults[provider]
    
    if provider == ProviderType.OPENROUTER:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is required "
                "when LLM_PROVIDER=openrouter"
            )
        return ProviderConfig(
            provider=provider,
            model=model,
            openrouter_api_key=api_key,
            openrouter_http_referer=os.getenv("OPENROUTER_HTTP_REFERER"),
            openrouter_x_title=os.getenv("OPENROUTER_X_TITLE"),
        )
    else:
        return ProviderConfig(
            provider=provider,
            model=model,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
        )


def create_provider(config: Optional[ProviderConfig] = None) -> LLMProvider:
    """
    Create an LLM provider instance from config.
    
    If config is not provided, loads from environment automatically.
    This is the primary factory function used by all agent stages.
    
    Usage in agent stages:
        from providers import create_provider, load_config
        config = load_config()
        provider = create_provider(config)
        MODEL = config.model
    """
    if config is None:
        config = load_config()
    
    if config.provider == ProviderType.OPENROUTER:
        from .openrouter import OpenRouterProvider
        return OpenRouterProvider(
            api_key=config.openrouter_api_key,
            http_referer=config.openrouter_http_referer,
            x_title=config.openrouter_x_title,
        )
    else:
        from .claude import ClaudeProvider
        return ClaudeProvider(
            api_key=config.anthropic_api_key,
            base_url=config.anthropic_base_url,
        )
```

### Step 1.5: Create `agents/providers/__init__.py`

```python
# agents/providers/__init__.py
from .base import (
    ContentBlock,
    LLMProvider,
    NormalizedResponse,
    NormalizedTextBlock,
    NormalizedToolUseBlock,
)
from .config import ProviderConfig, ProviderType, create_provider, load_config

__all__ = [
    "ContentBlock",
    "LLMProvider",
    "NormalizedResponse",
    "NormalizedTextBlock",
    "NormalizedToolUseBlock",
    "ProviderConfig",
    "ProviderType",
    "create_provider",
    "load_config",
]
```

---

## Phase 2: Configuration System

### Step 2.1: Update `.env.example`

Add OpenRouter configuration section alongside the existing Claude config:

```bash
# =============================================================================
# LLM Provider Selection
# =============================================================================
# Options: "claude" (default) | "openrouter"
LLM_PROVIDER=claude

# Model ID — format depends on the selected provider (see below)
MODEL_ID=claude-sonnet-4-6

# =============================================================================
# PROVIDER: Claude (Anthropic) — default
# =============================================================================
ANTHROPIC_API_KEY=sk-ant-xxx

# Optional: Anthropic-compatible base URL for other providers
# ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
# MODEL_ID=MiniMax-M2.5

# =============================================================================
# PROVIDER: OpenRouter — access 300+ models from one API
# =============================================================================
# Uncomment and set to use OpenRouter:
# LLM_PROVIDER=openrouter
# OPENROUTER_API_KEY=sk-or-xxx              # from openrouter.ai/settings/keys
# OPENROUTER_HTTP_REFERER=https://your-app  # optional, for tracking
# OPENROUTER_X_TITLE=My Agent              # optional, display name

# OpenRouter Model IDs (prefix with provider/):
# MODEL_ID=anthropic/claude-sonnet-4-6      # Claude via OpenRouter
# MODEL_ID=openai/gpt-4o                    # GPT-4o via OpenRouter
# MODEL_ID=google/gemini-2.0-flash          # Gemini via OpenRouter
# MODEL_ID=deepseek/deepseek-chat           # DeepSeek via OpenRouter
# MODEL_ID=minimax/minimax-m2               # MiniMax via OpenRouter
# MODEL_ID=meta-llama/llama-3.3-70b-instruct # LLaMA via OpenRouter
```

### Step 2.2: Update `requirements.txt`

```
anthropic>=0.25.0
python-dotenv>=1.0.0
openrouter>=0.1.0      # OpenRouter Python SDK
```

> **Note:** Pin to a specific version once validated, since the OpenRouter SDK is in beta.
> The README notes the beta status: "there may be breaking changes between versions without a major version update."

---

## Phase 3: Refactor Agent Stages

### The Standard Refactoring Pattern

Every agent stage follows the same 3-step refactoring:

**BEFORE (all stages):**
```python
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# In agent_loop():
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

**AFTER (all stages):**
```python
import os
from dotenv import load_dotenv
from providers import create_provider, load_config

load_dotenv(override=True)

_config = load_config()
provider = create_provider(_config)
MODEL = _config.model

# In agent_loop():
response = provider.create_message(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
messages.append(provider.response_to_assistant_message(response))
if response.stop_reason != "tool_use":
    return
```

The tool dispatch code is **completely unchanged**:
```python
# This works identically for both providers — response.content contains
# NormalizedToolUseBlock objects with .type, .id, .name, .input attributes
for block in response.content:
    if block.type == "tool_use":
        output = TOOL_HANDLERS[block.name](**block.input)
        results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
```

---

### Step 3.1: Refactor s01_agent_loop.py

**Complexity:** Low — 1 call site.  
**Change diff:** Replace 5 lines of init code + 2 lines in `agent_loop()`.

```python
# Before: from anthropic import Anthropic
# After:
from providers import create_provider, load_config

_config = load_config()
provider = create_provider(_config)
MODEL = _config.model

# In agent_loop(), change:
# response = client.messages.create(...)
# messages.append({"role": "assistant", "content": response.content})
# To:
# response = provider.create_message(...)
# messages.append(provider.response_to_assistant_message(response))
```

**Testing:**
- Unit test with `MockProvider` that returns a single `NormalizedResponse(stop_reason="end_turn", content=[NormalizedTextBlock(...)])`
- Verify loop exits when `stop_reason != "tool_use"`
- Unit test with `MockProvider` that returns `stop_reason="tool_use"` followed by `stop_reason="end_turn"`
- Verify tool call extracted, executed, result appended, loop continues

---

### Step 3.2: Refactor s02_tool_use.py

**Complexity:** Low — 1 call site. Identical pattern to s01.  
**Additional test:** Verify the dispatch map handles tool calls correctly with normalized blocks.

---

### Step 3.3: Refactor s03_todo_write.py

**Complexity:** Low — 1 call site. Verify the nag reminder injection still works:
```python
# The reminder injected as {"type": "text", "text": "<reminder>..."} in results[]
# OpenRouter provider must handle this in _convert_messages()
# → included in the reminder_parts handling in user message conversion
```

**Testing:**
- Verify reminder text `{"type": "text", "text": "..."}` in user content is correctly converted to a user message by OpenRouterProvider

---

### Step 3.4: Refactor s04_subagent.py

**Complexity:** Medium — 2 call sites: `agent_loop()` and `run_subagent()`.

**Key change in `run_subagent()`:**
```python
# Before:
response = client.messages.create(
    model=MODEL, system=SUBAGENT_SYSTEM, messages=sub_messages,
    tools=CHILD_TOOLS, max_tokens=8000,
)
sub_messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    break
# After:
response = provider.create_message(
    model=MODEL, system=SUBAGENT_SYSTEM, messages=sub_messages,
    tools=CHILD_TOOLS, max_tokens=8000,
)
sub_messages.append(provider.response_to_assistant_message(response))
if response.stop_reason != "tool_use":
    break
```

**Testing:**
- Test parent agent spawning a subagent → verify subagent uses the same provider
- Test subagent returning summary to parent
- Verify child context discarded (only summary returned)

---

### Step 3.5: Refactor s05_skill_loading.py

**Complexity:** Low — 1 call site. Identical to s02 pattern.  
**Note:** Skill loading is pure Python (file I/O), no LLM changes needed.

---

### Step 3.6: Refactor s06_context_compact.py

**Complexity:** Medium — 2 call sites: `agent_loop()` AND `auto_compact()`.

**Key change in `auto_compact()`:**
```python
# Before (uses client directly for summarization):
response = client.messages.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Summarize..."}],
    max_tokens=2000,
)
summary = response.content[0].text

# After (uses provider, with empty tools list and empty system):
response = provider.create_message(
    model=MODEL,
    system="",
    messages=[{"role": "user", "content": "Summarize..."}],
    tools=[],
    max_tokens=2000,
)
summary_blocks = [b for b in response.content if b.type == "text"]
summary = summary_blocks[0].text if summary_blocks else "(no summary)"
```

**Testing:**
- Test `auto_compact` uses the provider's `create_message()` for summarization
- Test that summary is extracted from `NormalizedTextBlock.text`
- Test threshold check triggers auto_compact
- Test manual compact tool triggers `auto_compact`

---

### Step 3.7: Refactor s07_task_system.py

**Complexity:** Low — 1 call site. `TaskManager` is pure file I/O.

---

### Step 3.8: Refactor s08_background_tasks.py

**Complexity:** Low — 1 call site. `BackgroundManager` uses threads but no LLM.

---

### Step 3.9: Refactor s09_agent_teams.py

**Complexity:** High — 2 call sites: `agent_loop()` (main thread) AND `_teammate_loop()` (daemon threads).

**Critical thread-safety consideration:** The `provider` object is created once and shared across the lead and all teammate threads. The OpenRouter SDK client uses HTTPX internally — verify thread safety.

**Recommendation:** Create a `threading.local()` provider per thread or verify that `OpenRouter` client is thread-safe (HTTPX is generally thread-safe for synchronous calls).

```python
# Teammate thread now uses the shared provider:
response = provider.create_message(
    model=MODEL,
    system=sys_prompt,
    messages=messages,
    tools=tools,
    max_tokens=8000,
)
messages.append(provider.response_to_assistant_message(response))
if response.stop_reason != "tool_use":
    break
```

**Testing:**
- Test teammate spawn with mock provider
- Test inter-teammate messaging flow
- Test thread safety: spawn 3 teammates simultaneously, verify no race conditions on mock provider

---

### Step 3.10: Refactor s10_team_protocols.py

**Complexity:** High — Same as s09 plus protocol FSM.  
**Change:** Same 2-site refactoring pattern as s09.

---

### Step 3.11: Refactor s11_autonomous_agents.py

**Complexity:** High — Idle-cycle + task board + 2 LLM call sites.  
**Change:** Same 2-site refactoring as s09/s10. The idle polling loop (time.sleep) has no LLM calls.

---

### Step 3.12: Refactor s12_worktree_task_isolation.py

**Complexity:** Low — 1 call site. `TaskManager` and `WorktreeManager` are pure file/git operations.

---

### Step 3.13: Refactor s_full.py

**Complexity:** Very High — 3+ call sites (lead loop, subagent, teammate threads).

**Changes required:**
1. Replace initialization (same pattern as all stages)
2. Refactor `agent_loop()` (lead)
3. Refactor `run_subagent()` 
4. Refactor teammate `_loop()` in `TeammateManager`
5. Refactor `auto_compact()` (if included — s_full combines s06)

**Testing:**
- Integration test with mock provider simulating full multi-agent flow
- Test that all mechanisms (skills, compact, tasks, teams) work together

---

## Phase 4: Testing Framework

### Step 4.1: Create `tests/providers/test_base.py`

```python
"""Tests for normalized response types."""
import pytest
from agents.providers.base import (
    NormalizedTextBlock,
    NormalizedToolUseBlock,
    NormalizedResponse,
)


class TestNormalizedTextBlock:
    def test_default_type(self):
        block = NormalizedTextBlock(text="hello")
        assert block.type == "text"

    def test_text_attribute(self):
        block = NormalizedTextBlock(text="hello")
        assert block.text == "hello"

    def test_hasattr_text(self):
        """Agent code uses hasattr(block, 'text') — must work."""
        block = NormalizedTextBlock(text="hello")
        assert hasattr(block, "text")


class TestNormalizedToolUseBlock:
    def test_default_type(self):
        block = NormalizedToolUseBlock(id="abc", name="bash", input={"command": "ls"})
        assert block.type == "tool_use"

    def test_attributes(self):
        block = NormalizedToolUseBlock(id="abc", name="bash", input={"command": "ls"})
        assert block.id == "abc"
        assert block.name == "bash"
        assert block.input == {"command": "ls"}

    def test_no_text_attribute(self):
        """Tool blocks don't have text — hasattr(block, 'text') == False."""
        block = NormalizedToolUseBlock(id="1", name="bash", input={})
        assert not hasattr(block, "text")


class TestNormalizedResponse:
    def test_stop_reason_tool_use(self):
        response = NormalizedResponse(stop_reason="tool_use", content=[])
        assert response.stop_reason == "tool_use"
        assert response.stop_reason != "end_turn"

    def test_stop_reason_end_turn(self):
        response = NormalizedResponse(stop_reason="end_turn", content=[])
        assert response.stop_reason != "tool_use"

    def test_content_access(self):
        blocks = [NormalizedTextBlock(text="hi"), NormalizedToolUseBlock(id="1", name="bash", input={})]
        response = NormalizedResponse(stop_reason="tool_use", content=blocks)
        assert len(response.content) == 2
        assert response.content[0].type == "text"
        assert response.content[1].type == "tool_use"
```

---

### Step 4.2: Create `tests/providers/test_claude_provider.py`

```python
"""Tests for ClaudeProvider."""
import pytest
from unittest.mock import MagicMock, patch

from agents.providers.claude import ClaudeProvider
from agents.providers.base import NormalizedTextBlock, NormalizedToolUseBlock


class MockAnthropicTextBlock:
    type = "text"
    text = "Hello, world!"

class MockAnthropicToolUseBlock:
    type = "tool_use"
    id = "tool_abc"
    name = "bash"
    input = {"command": "ls"}

class MockAnthropicResponse:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


@pytest.fixture
def mock_anthropic():
    with patch("agents.providers.claude.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        yield instance


class TestClaudeProviderPositive:
    def test_text_response(self, mock_anthropic):
        """Returns NormalizedTextBlock for text responses."""
        mock_anthropic.messages.create.return_value = MockAnthropicResponse(
            stop_reason="end_turn",
            content=[MockAnthropicTextBlock()],
        )
        provider = ClaudeProvider(api_key="test")
        response = provider.create_message(
            model="claude-3-sonnet",
            system="You are a coder.",
            messages=[{"role": "user", "content": "Hi"}],
            tools=[],
        )
        assert response.stop_reason == "end_turn"
        assert len(response.content) == 1
        assert isinstance(response.content[0], NormalizedTextBlock)
        assert response.content[0].text == "Hello, world!"

    def test_tool_use_response(self, mock_anthropic):
        """Returns NormalizedToolUseBlock for tool_use responses."""
        mock_anthropic.messages.create.return_value = MockAnthropicResponse(
            stop_reason="tool_use",
            content=[MockAnthropicToolUseBlock()],
        )
        provider = ClaudeProvider(api_key="test")
        response = provider.create_message(
            model="claude-3-sonnet",
            system="You are a coder.",
            messages=[{"role": "user", "content": "List files"}],
            tools=[{"name": "bash", "description": "...", "input_schema": {}}],
        )
        assert response.stop_reason == "tool_use"
        assert len(response.content) == 1
        block = response.content[0]
        assert isinstance(block, NormalizedToolUseBlock)
        assert block.id == "tool_abc"
        assert block.name == "bash"
        assert block.input == {"command": "ls"}

    def test_convert_messages_with_normalized_blocks(self, mock_anthropic):
        """NormalizedToolUseBlock in messages → Anthropic dict format."""
        mock_anthropic.messages.create.return_value = MockAnthropicResponse(
            stop_reason="end_turn", content=[MockAnthropicTextBlock()])
        
        provider = ClaudeProvider(api_key="test")
        normalized_block = NormalizedToolUseBlock(id="t1", name="bash", input={"command": "ls"})
        messages = [
            {"role": "assistant", "content": [normalized_block]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "output"}]},
        ]
        provider.create_message("model", "sys", messages, [])
        
        # Verify the Anthropic SDK received dict format (not NormalizedToolUseBlock)
        call_args = mock_anthropic.messages.create.call_args
        sent_messages = call_args.kwargs["messages"]
        assert sent_messages[0]["content"][0] == {
            "type": "tool_use", "id": "t1", "name": "bash", "input": {"command": "ls"}
        }


class TestClaudeProviderNegative:
    def test_api_error_propagates(self, mock_anthropic):
        """API errors should propagate to caller."""
        from anthropic import APIConnectionError
        mock_anthropic.messages.create.side_effect = APIConnectionError(request=MagicMock())
        
        provider = ClaudeProvider(api_key="test")
        with pytest.raises(APIConnectionError):
            provider.create_message("model", "sys", [{"role": "user", "content": "hi"}], [])

    def test_empty_content_list(self, mock_anthropic):
        """Empty content list is handled gracefully."""
        mock_anthropic.messages.create.return_value = MockAnthropicResponse(
            stop_reason="end_turn", content=[])
        provider = ClaudeProvider(api_key="test")
        response = provider.create_message("model", "sys", [{"role": "user", "content": "hi"}], [])
        assert response.content == []
        assert response.stop_reason == "end_turn"
```

---

### Step 4.3: Create `tests/providers/test_openrouter_provider.py`

```python
"""Tests for OpenRouterProvider — message format translation + normalization."""
import json
import pytest
from unittest.mock import MagicMock, patch

from agents.providers.openrouter import OpenRouterProvider
from agents.providers.base import NormalizedTextBlock, NormalizedToolUseBlock


def make_mock_or_response(finish_reason, content_text=None, tool_calls=None):
    """Build a mock OpenRouter chat response."""
    message = MagicMock()
    message.content = content_text
    message.tool_calls = tool_calls
    
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message = message
    
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def mock_openrouter():
    with patch("agents.providers.openrouter.OpenRouter") as MockOR:
        instance = MockOR.return_value
        yield instance


class TestOpenRouterToolConversion:
    def test_anthropic_tools_to_openai_format(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        anthropic_tools = [{
            "name": "bash",
            "description": "Run shell command",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            }
        }]
        result = provider._convert_tools(anthropic_tools)
        assert result == [{
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Run shell command",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                }
            }
        }]

    def test_empty_tools_list(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        assert provider._convert_tools([]) == []


class TestOpenRouterMessageConversion:
    def test_system_prompt_prepended(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        result = provider._convert_messages("You are a coder.", [
            {"role": "user", "content": "Hi"}
        ])
        assert result[0] == {"role": "system", "content": "You are a coder."}
        assert result[1] == {"role": "user", "content": "Hi"}

    def test_normalized_tool_use_block_in_assistant_message(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        block = NormalizedToolUseBlock(id="t1", name="bash", input={"command": "ls"})
        result = provider._convert_messages("", [
            {"role": "assistant", "content": [block]}
        ])
        assistant_msg = next(m for m in result if m["role"] == "assistant")
        assert assistant_msg["tool_calls"] == [{
            "id": "t1",
            "type": "function",
            "function": {"name": "bash", "arguments": '{"command": "ls"}'}
        }]

    def test_tool_result_to_tool_role(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        result = provider._convert_messages("", [
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "file.txt"}
            ]}
        ])
        tool_msg = next(m for m in result if m.get("role") == "tool")
        assert tool_msg == {"role": "tool", "tool_call_id": "t1", "content": "file.txt"}

    def test_todo_reminder_in_user_message(self):
        """s03 injects {"type":"text","text":"<reminder>..."} — must become user message."""
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        result = provider._convert_messages("", [
            {"role": "user", "content": [
                {"type": "text", "text": "<reminder>Update your todos.</reminder>"},
                {"type": "tool_result", "tool_use_id": "t1", "content": "done"},
            ]}
        ])
        # Should produce a user message with reminder AND a tool message
        user_msgs = [m for m in result if m["role"] == "user"]
        tool_msgs = [m for m in result if m["role"] == "tool"]
        assert any("<reminder>" in m.get("content", "") for m in user_msgs)
        assert len(tool_msgs) == 1


class TestOpenRouterResponseNormalization:
    def test_tool_calls_response(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        mock_tc = MagicMock()
        mock_tc.id = "call_123"
        mock_tc.function.name = "bash"
        mock_tc.function.arguments = '{"command": "ls -la"}'
        
        response = make_mock_or_response("tool_calls", tool_calls=[mock_tc])
        result = provider._normalize_response(response)
        
        assert result.stop_reason == "tool_use"
        assert len(result.content) == 1
        block = result.content[0]
        assert isinstance(block, NormalizedToolUseBlock)
        assert block.id == "call_123"
        assert block.name == "bash"
        assert block.input == {"command": "ls -la"}

    def test_text_response(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        response = make_mock_or_response("stop", content_text="Hello!")
        result = provider._normalize_response(response)
        
        assert result.stop_reason == "end_turn"
        assert len(result.content) == 1
        assert isinstance(result.content[0], NormalizedTextBlock)
        assert result.content[0].text == "Hello!"

    def test_malformed_tool_arguments_fallback(self):
        """Malformed JSON in tool arguments → empty dict, no crash."""
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        mock_tc = MagicMock()
        mock_tc.id = "t1"
        mock_tc.function.name = "bash"
        mock_tc.function.arguments = "NOT_VALID_JSON"
        
        response = make_mock_or_response("tool_calls", tool_calls=[mock_tc])
        result = provider._normalize_response(response)
        
        assert result.content[0].input == {}

    def test_no_tool_calls(self):
        """Response with no tool_calls → no NormalizedToolUseBlock."""
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        mock_message = MagicMock()
        mock_message.content = "Done"
        mock_message.tool_calls = None
        
        choice = MagicMock()
        choice.finish_reason = "stop"
        choice.message = mock_message
        
        response = MagicMock()
        response.choices = [choice]
        
        result = provider._normalize_response(response)
        assert result.stop_reason == "end_turn"
        tool_blocks = [b for b in result.content if b.type == "tool_use"]
        assert len(tool_blocks) == 0


class TestOpenRouterProviderIntegration:
    def test_full_tool_use_cycle(self, mock_openrouter):
        """End-to-end: provider call → tool use → tool result round-trip."""
        mock_tc = MagicMock()
        mock_tc.id = "call_abc"
        mock_tc.function.name = "bash"
        mock_tc.function.arguments = '{"command": "ls"}'
        
        mock_openrouter.chat.send.return_value = make_mock_or_response(
            "tool_calls", tool_calls=[mock_tc])
        
        provider = OpenRouterProvider(api_key="test-key")
        response = provider.create_message(
            model="anthropic/claude-sonnet-4-6",
            system="You are a coder.",
            messages=[{"role": "user", "content": "List files"}],
            tools=[{"name": "bash", "description": "Run command",
                    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}],
        )
        assert response.stop_reason == "tool_use"
        assert response.content[0].name == "bash"
        
        # Verify tools were converted to OpenAI format
        call_args = mock_openrouter.chat.send.call_args
        tools_sent = call_args.kwargs.get("tools") or call_args.args[0] if call_args.args else None
        # (exact assertion depends on how the SDK accepts kwargs)
```

---

### Step 4.4: Create `tests/providers/test_config.py`

```python
"""Tests for provider configuration loading."""
import os
import pytest
from unittest.mock import patch

from agents.providers.config import load_config, create_provider, ProviderType


class TestLoadConfig:
    def test_default_is_claude(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": ""}, clear=False):
            os.environ.pop("LLM_PROVIDER", None)
            config = load_config()
            assert config.provider == ProviderType.CLAUDE

    def test_claude_provider(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "claude",
            "MODEL_ID": "claude-sonnet-4-6",
            "ANTHROPIC_API_KEY": "sk-ant-test"
        }):
            config = load_config()
            assert config.provider == ProviderType.CLAUDE
            assert config.model == "claude-sonnet-4-6"
            assert config.anthropic_api_key == "sk-ant-test"

    def test_openrouter_provider(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openrouter",
            "MODEL_ID": "anthropic/claude-sonnet-4-6",
            "OPENROUTER_API_KEY": "sk-or-test",
        }):
            config = load_config()
            assert config.provider == ProviderType.OPENROUTER
            assert config.model == "anthropic/claude-sonnet-4-6"
            assert config.openrouter_api_key == "sk-or-test"

    def test_unknown_provider_raises(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown_provider"}):
            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                load_config()

    def test_openrouter_missing_api_key_raises(self):
        env = {"LLM_PROVIDER": "openrouter", "MODEL_ID": "anthropic/claude"}
        env.pop("OPENROUTER_API_KEY", None)
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                load_config()

    def test_model_default_for_claude(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "claude", "ANTHROPIC_API_KEY": "key"}, clear=True):
            os.environ.pop("MODEL_ID", None)
            config = load_config()
            assert config.model == "claude-sonnet-4-6"

    def test_model_default_for_openrouter(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "key"}, clear=True):
            os.environ.pop("MODEL_ID", None)
            config = load_config()
            assert config.model == "anthropic/claude-sonnet-4-6"
```

---

### Step 4.5: Create `tests/agents/test_s01_agent_loop.py`

**Pattern for all agent stage tests: mock the provider, verify agent loop behavior**

```python
"""
Tests for s01_agent_loop.py using mock provider.

Key insight: by mocking the provider, we test the agent's loop logic
independently of any network calls or LLM behavior.
"""
import pytest
from unittest.mock import MagicMock, patch
from agents.providers.base import (
    NormalizedResponse, NormalizedTextBlock, NormalizedToolUseBlock
)


class MockProvider:
    """Configurable mock LLM provider for agent loop testing."""
    
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    
    def create_message(self, model, system, messages, tools, max_tokens=8000):
        self.calls.append({"model": model, "messages": list(messages), "tools": tools})
        return next(self.responses)
    
    def response_to_assistant_message(self, response):
        return {"role": "assistant", "content": response.content}


@pytest.fixture
def tool_response():
    return NormalizedResponse(
        stop_reason="tool_use",
        content=[NormalizedToolUseBlock(id="t1", name="bash", input={"command": "echo hello"})],
    )

@pytest.fixture
def text_response():
    return NormalizedResponse(
        stop_reason="end_turn",
        content=[NormalizedTextBlock(text="Task complete.")],
    )


class TestAgentLoopPositive:
    def test_single_turn_no_tools(self, text_response):
        """Agent loop exits when stop_reason is not tool_use."""
        from agents.s01_agent_loop import agent_loop
        
        provider = MockProvider([text_response])
        messages = [{"role": "user", "content": "Hi"}]
        
        with patch("agents.s01_agent_loop.provider", provider):
            agent_loop(messages)
        
        assert len(provider.calls) == 1
        # Messages: [user, assistant]
        assert len(messages) == 2
        assert messages[-1]["role"] == "assistant"

    def test_tool_use_then_complete(self, tool_response, text_response):
        """Agent loop calls tool and continues until stop_reason != tool_use."""
        from agents.s01_agent_loop import agent_loop
        
        executed_commands = []
        
        def mock_run_bash(command):
            executed_commands.append(command)
            return "hello"
        
        provider = MockProvider([tool_response, text_response])
        messages = [{"role": "user", "content": "Run echo hello"}]
        
        with patch("agents.s01_agent_loop.provider", provider), \
             patch("agents.s01_agent_loop.run_bash", mock_run_bash):
            agent_loop(messages)
        
        assert len(provider.calls) == 2
        assert executed_commands == ["echo hello"]
        # Messages: [user, assistant (tool_use), user (tool_result), assistant (final)]
        assert len(messages) == 4

    def test_provider_called_with_correct_model(self, text_response):
        """Provider is called with MODEL from config."""
        from agents.s01_agent_loop import agent_loop
        
        provider = MockProvider([text_response])
        messages = [{"role": "user", "content": "Hi"}]
        
        with patch("agents.s01_agent_loop.provider", provider), \
             patch("agents.s01_agent_loop.MODEL", "test-model-123"):
            agent_loop(messages)
        
        assert provider.calls[0]["model"] == "test-model-123"


class TestAgentLoopNegative:
    def test_provider_error_propagates(self):
        """If provider raises, the error propagates out of agent_loop."""
        from agents.s01_agent_loop import agent_loop
        
        provider = MagicMock()
        provider.create_message.side_effect = RuntimeError("API down")
        
        messages = [{"role": "user", "content": "Hi"}]
        
        with patch("agents.s01_agent_loop.provider", provider):
            with pytest.raises(RuntimeError, match="API down"):
                agent_loop(messages)
```

---

### Step 4.6: Key Agent Stage Test — s04_subagent.py

```python
"""Tests for s04_subagent.py — verifies subagent uses provider, parent context stays clean."""

class TestSubagentIsolation:
    def test_subagent_fresh_context(self):
        """Subagent starts with fresh messages, parent not modified during subagent run."""
        from agents.s04_subagent import run_subagent
        
        text_response = NormalizedResponse(
            stop_reason="end_turn",
            content=[NormalizedTextBlock(text="Subtask complete.")],
        )
        provider = MockProvider([text_response])
        
        with patch("agents.s04_subagent.provider", provider):
            result = run_subagent("Do subtask X")
        
        assert "Subtask complete." in result
        # Subagent called provider with fresh 1-message context
        assert len(provider.calls[0]["messages"]) == 1

    def test_subagent_tool_loop(self):
        """Subagent runs tool loop internally before returning summary."""
        tool_response = NormalizedResponse(
            stop_reason="tool_use",
            content=[NormalizedToolUseBlock(id="t1", name="bash", input={"command": "ls"})],
        )
        summary_response = NormalizedResponse(
            stop_reason="end_turn",
            content=[NormalizedTextBlock(text="Found 3 files.")],
        )
        provider = MockProvider([tool_response, summary_response])
        
        with patch("agents.s04_subagent.provider", provider), \
             patch("agents.s04_subagent.TOOL_HANDLERS", {"bash": lambda **kw: "file1.txt\nfile2.txt"}):
            result = run_subagent("List files")
        
        assert "Found 3 files." in result
        assert len(provider.calls) == 2
```

---

### Step 4.7: Key Agent Stage Test — s06_context_compact.py

```python
"""Tests for s06_context_compact — auto_compact uses provider for summarization."""

class TestAutoCompact:
    def test_auto_compact_calls_provider(self, tmp_path):
        """auto_compact() uses provider.create_message() for summarization."""
        from agents.s06_context_compact import auto_compact
        
        summary_response = NormalizedResponse(
            stop_reason="end_turn",
            content=[NormalizedTextBlock(text="Conversation summary: did X, Y, Z.")],
        )
        provider = MockProvider([summary_response])
        
        messages = [
            {"role": "user", "content": "Start"},
            {"role": "assistant", "content": [NormalizedTextBlock(text="Working...")]},
        ]
        
        with patch("agents.s06_context_compact.provider", provider), \
             patch("agents.s06_context_compact.TRANSCRIPT_DIR", tmp_path):
            new_messages = auto_compact(messages)
        
        assert len(provider.calls) == 1
        # Result is compressed: 2 messages (summary + acknowledgment)
        assert len(new_messages) == 2
        assert "summary" in new_messages[0]["content"].lower() or "did X" in new_messages[0]["content"]
```

---

## Phase 5: Documentation & CI Updates

### Step 5.1: Update README.md

Add an "LLM Provider Configuration" section between Quick Start and Learning Path:

```markdown
## LLM Provider Configuration

By default, the agent uses **Claude** (Anthropic). You can switch to **OpenRouter** 
to access 300+ models from a single API key.

### Use Claude (default)
```sh
# .env
ANTHROPIC_API_KEY=sk-ant-xxx
MODEL_ID=claude-sonnet-4-6
LLM_PROVIDER=claude  # or omit — default is claude
```

### Use OpenRouter
```sh
# .env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxx       # from openrouter.ai/settings/keys
MODEL_ID=anthropic/claude-sonnet-4-6  # or any of 300+ models
```

OpenRouter model IDs (examples):
| Model | ID |
|-------|-----|
| Claude Sonnet 4.6 | `anthropic/claude-sonnet-4-6` |
| GPT-4o | `openai/gpt-4o` |
| Gemini 2.0 Flash | `google/gemini-2.0-flash` |
| DeepSeek Chat | `deepseek/deepseek-chat` |
| LLaMA 3.3 70B | `meta-llama/llama-3.3-70b-instruct` |
```

### Step 5.2: Update CI/CD

The `.github/workflows/ci.yml` currently runs typecheck + build for the Next.js web app.  
Add a Python testing step:

```yaml
# In .github/workflows/ci.yml, add:
- name: Install Python dependencies
  run: pip install -r requirements.txt pytest pytest-mock

- name: Run Python provider tests
  run: pytest tests/ -v --tb=short
  env:
    LLM_PROVIDER: claude  # tests use mocks, no real API key needed
    ANTHROPIC_API_KEY: test-key-for-ci
```

---

## Trade-offs & Justifications

### Trade-off 1: OpenRouter SDK vs OpenAI SDK as Backend

| | OpenRouter SDK (`openrouter` package) | OpenAI SDK (`openai`) with base_url |
|--|--|--|
| **Type safety** | ✅ Pydantic-validated, auto-generated | ❌ No OpenRouter-specific types |
| **Feature access** | ✅ Full (provider routing, ZDR, fallbacks) | ❌ Only standard OpenAI params |
| **Stability** | ⚠️ Beta, may break | ✅ Stable |
| **Code learning** | ✅ Shows OpenRouter SDK usage | ❌ Hides OpenRouter-specific API |
| **Dependency** | ➕ New `openrouter` package | ➕ `openai` package (often already installed) |

**Decision: OpenRouter SDK** — provides the fullest OpenRouter feature access and is the official supported path. The beta caveat is mitigated by pinning the version in `requirements.txt`.

### Trade-off 2: Shared Provider Instance vs Per-Thread Instance (s09-s11)

| | Shared single provider | Per-thread provider instance |
|--|--|--|
| **Resource usage** | ✅ Lower (one HTTPX client) | ❌ Higher (N HTTPX clients) |
| **Thread safety** | ⚠️ Depends on SDK implementation | ✅ Guaranteed safe |
| **Simplicity** | ✅ Simpler code | ❌ Requires thread-local storage |

**Decision: Shared provider with verification.** HTTPX (used by both Anthropic SDK and OpenRouter SDK internally) is designed to be thread-safe for synchronous calls. The shared `provider` object should be safe. However, add a comment in s09-s11 noting this assumption and the thread-local alternative.

**Thread-local alternative if needed:**
```python
import threading
_thread_local = threading.local()

def get_provider():
    if not hasattr(_thread_local, 'provider'):
        _thread_local.provider = create_provider(load_config())
    return _thread_local.provider
```

### Trade-off 3: Normalized Response Objects vs Pure Dict Messages

| | Normalized dataclass objects (chosen) | Convert everything to dicts |
|--|--|--|
| **Agent code change** | ✅ Minimal (`.type`, `.id`, `.name`, `.input` same) | ❌ Extensive (all 12 stages change `block.type` → `block["type"]`) |
| **Clarity** | ✅ Clear types, IDE autocomplete | ⚠️ Dict access, runtime KeyError risk |
| **Testability** | ✅ Easy to construct in tests | ✅ Easy to construct in tests |
| **Anthropic SDK compat** | ✅ Can convert back to dicts | ✅ Direct dict passing |

**Decision: Normalized dataclass objects** — preserves the existing agent code attribute access patterns with minimal change.

### Trade-off 4: Provider Injection vs Global Provider

| | Module-level global `provider` (chosen for minimum change) | Dependency injection via function param |
|--|--|--|
| **Existing code change** | ✅ Minimal | ❌ All function signatures change |
| **Testability** | ✅ Easy to patch with `unittest.mock.patch` | ✅ Pass mock directly |
| **Production code quality** | ⚠️ Global state | ✅ Explicit dependencies |
| **Teaching clarity** | ✅ Simple, clear | ⚠️ More complex patterns |

**Decision: Module-level global** for initial implementation (matches existing code style). Future improvement: add `agent_loop(messages, provider=None)` optional parameter for explicit injection.

---

## Missing Information & Clarifying Questions

### Missing Information

1. **OpenRouter SDK version stability:** The SKILL.md notes the SDK is in beta. Need to determine the current stable version tag for pinning in `requirements.txt`. Run `pip install openrouter && pip show openrouter` to get current version.

2. **OpenRouter tool calling support for all models:** Not all models on OpenRouter support function/tool calling. Need to confirm: Does the `openrouter` SDK raise an error or silently ignore tools for models that don't support it? This affects error handling in `create_message()`.

3. **OpenRouter's system message handling across models:** Some models (e.g., older LLaMA variants) handle system messages differently. Need to verify `_convert_messages()` system prepend works correctly across target models.

4. **Message format when no tool_calls present in OpenRouter response:** In the OpenAI spec, `message.tool_calls` is `null` when no tools are called. Verify `hasattr(message, "tool_calls")` vs `message.tool_calls is None` guard in `_normalize_response()`.

### Clarifying Questions for Users

1. **Target models via OpenRouter:** Which specific OpenRouter models should be prioritized for testing? Claude via OpenRouter? DeepSeek? Gemini? This affects what edge cases to handle in tool format conversion.

2. **Backward compatibility requirement:** Should the refactored agent stages maintain backward compatibility with the existing `.env` format (where only `ANTHROPIC_API_KEY` and `MODEL_ID` are set, without `LLM_PROVIDER`)? **Current plan:** Yes, `LLM_PROVIDER` defaults to `"claude"` so existing `.env` files work unchanged.

3. **s_full.py scope:** The `s_full.py` combines all mechanisms. Should it be refactored as part of this plan, or kept as a reference-only file? **Recommendation:** Yes, refactor it last as validation of the complete implementation.

4. **Testing scope:** Should integration tests with real API calls be included (requiring actual API keys in CI)? **Recommendation:** Keep unit tests (mocked) in CI; provide optional integration tests that require `OPENROUTER_API_KEY` env var, skipped in CI unless set.

5. **Python version constraint:** The OpenRouter SDK requires Python 3.9+. The existing `requirements.txt` has no Python version constraint. Add `python_requires >= 3.9` note in documentation.

---

## Implementation Checklist

```
Phase 1: Provider Abstraction Layer
  [ ] Create agents/providers/ directory
  [ ] Create agents/providers/__init__.py
  [ ] Create agents/providers/base.py (NormalizedResponse, LLMProvider Protocol)
  [ ] Create agents/providers/claude.py (ClaudeProvider)
  [ ] Create agents/providers/openrouter.py (OpenRouterProvider)
  [ ] Create agents/providers/config.py (load_config, create_provider)

Phase 2: Configuration
  [ ] Update .env.example with OpenRouter section
  [ ] Update requirements.txt with openrouter>=0.x.x

Phase 3: Refactor Agent Stages (in order)
  [ ] s01_agent_loop.py
  [ ] s02_tool_use.py
  [ ] s03_todo_write.py  (verify todo reminder injection)
  [ ] s04_subagent.py    (2 call sites)
  [ ] s05_skill_loading.py
  [ ] s06_context_compact.py (2 call sites, auto_compact)
  [ ] s07_task_system.py
  [ ] s08_background_tasks.py
  [ ] s09_agent_teams.py  (thread safety verification)
  [ ] s10_team_protocols.py
  [ ] s11_autonomous_agents.py
  [ ] s12_worktree_task_isolation.py
  [ ] s_full.py  (all mechanisms combined)

Phase 4: Testing
  [ ] Create tests/ directory structure
  [ ] tests/providers/test_base.py
  [ ] tests/providers/test_claude_provider.py
  [ ] tests/providers/test_openrouter_provider.py
  [ ] tests/providers/test_config.py
  [ ] tests/agents/test_s01_agent_loop.py
  [ ] tests/agents/test_s04_subagent.py
  [ ] tests/agents/test_s06_context_compact.py
  [ ] tests/agents/test_s09_agent_teams.py (thread tests)
  [ ] Manual integration test: s01 with real OpenRouter API key

Phase 5: Documentation
  [ ] Update README.md with provider configuration section
  [ ] Update .github/workflows/ci.yml with Python test step
  [ ] Add CONTRIBUTING.md note about adding new providers
```

---

## Quick Start for Implementors

```bash
# 1. Install dependencies
pip install -r requirements.txt  # after adding openrouter>=0.x.x

# 2. Test with Claude (no change from current behavior)
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and MODEL_ID
python agents/s01_agent_loop.py

# 3. Test with OpenRouter
# Edit .env:
#   LLM_PROVIDER=openrouter
#   OPENROUTER_API_KEY=sk-or-xxx
#   MODEL_ID=anthropic/claude-sonnet-4-6
python agents/s01_agent_loop.py

# 4. Run tests (no API key needed — uses mocks)
pytest tests/ -v
```

---

*"The model is the agent. Our job is to give it tools — and now, to give the tools a provider."*
