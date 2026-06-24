# Switching LLM Provider

The teaching code in this repository uses the Anthropic API by default. Via the `agents/_llm_client.py` abstraction layer, you can switch to any OpenAI-compatible endpoint (DeepSeek, Qwen, Kimi, Zhipu, etc.).

## Configuration

Set the following environment variables in `.env`:

### Anthropic (default)
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
MODEL_ID=claude-3-5-sonnet-20241022
```

### DeepSeek
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_ID=deepseek-chat
```

### Qwen
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_ID=qwen-plus
```

### Kimi
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.moonshot.cn/v1
MODEL_ID=moonshot-v1-8k
```

## Usage

```python
from agents._llm_client import LLMClient

client = LLMClient()  # auto-detect provider from environment variables
response = client.chat(
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)

# Unified response format (Anthropic style)
for block in response.content:
    if block.type == "text":
        print(block.text)
    elif block.type == "tool_use":
        print(block.name, block.input)

if response.stop_reason == "tool_use":
    # handle tool call
    pass
```

## Protocol Difference Reference

| Anthropic | OpenAI-compatible |
|-----------|-------------|
| `client.messages.create()` | `client.chat.completions.create()` |
| `system=SYSTEM` | prepend `{"role": "system", ...}` to `messages` |
| `tools[].input_schema` | `tools[].function.parameters` |
| `stop_reason == "tool_use"` | `finish_reason == "tool_calls"` |
| `content[].type == "tool_use"` | `message.tool_calls` |
| `block.id` / `block.name` / `block.input` | `tool_call.id` / `tool_call.function.name` / `json.loads(arguments)` |
| `tool_result` message block | `{"role": "tool", "tool_call_id": ...}` |

## Known Limitations

- The semantics of the `tool_choice` parameter on OpenAI-compatible endpoints differ slightly from Anthropic
- Some domestic models do not support parallel tool calls
- Context window size varies by model; adjust `max_tokens` accordingly
