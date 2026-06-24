# 切换 LLM Provider

本仓库教学代码默认使用 Anthropic API。通过 `agents/_llm_client.py` 适配层，可切换到任意 OpenAI 兼容端点（DeepSeek、通义千问、Kimi、智谱等）。

## 配置方法

在 `.env` 中设置以下环境变量：

### Anthropic（默认）
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

### 通义千问
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

## 使用方法

```python
from agents._llm_client import LLMClient

client = LLMClient()  # 自动从环境变量读取 provider
response = client.chat(
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)

# 统一的响应格式（Anthropic 风格）
for block in response.content:
    if block.type == "text":
        print(block.text)
    elif block.type == "tool_use":
        print(block.name, block.input)

if response.stop_reason == "tool_use":
    # 处理工具调用
    pass
```

## 协议差异对照

| Anthropic | OpenAI 兼容 |
|-----------|-------------|
| `client.messages.create()` | `client.chat.completions.create()` |
| `system=SYSTEM` | `messages` 前加 `{"role": "system", ...}` |
| `tools[].input_schema` | `tools[].function.parameters` |
| `stop_reason == "tool_use"` | `finish_reason == "tool_calls"` |
| `content[].type == "tool_use"` | `message.tool_calls` |
| `block.id` / `block.name` / `block.input` | `tool_call.id` / `tool_call.function.name` / `json.loads(arguments)` |
| `tool_result` 消息块 | `{"role": "tool", "tool_call_id": ...}` |

## 已知限制

- OpenAI 兼容端点的 `tool_choice` 参数语义与 Anthropic 略有差异
- 部分国产模型不支持并行工具调用（parallel tool calls）
- 上下文窗口大小因模型而异，需相应调整 `max_tokens`
