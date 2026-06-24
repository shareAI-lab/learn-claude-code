# LLM プロバイダーの切り替え

本リポジトリの教学コードはデフォルトで Anthropic API を使用します。`agents/_llm_client.py` 抽象化レイヤーを通じて、任意の OpenAI 互換エンドポイント（DeepSeek、Qwen、Kimi、Zhipu など）に切り替えることができます。

## 設定方法

`.env` に以下の環境変数を設定します：

### Anthropic（デフォルト）
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

## 使用方法

```python
from agents._llm_client import LLMClient

client = LLMClient()  # 環境変数からプロバイダーを自動検出
response = client.chat(
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)

# 統一されたレスポンス形式（Anthropic スタイル）
for block in response.content:
    if block.type == "text":
        print(block.text)
    elif block.type == "tool_use":
        print(block.name, block.input)

if response.stop_reason == "tool_use":
    # ツール呼び出しを処理
    pass
```

## プロトコル差異対照表

| Anthropic | OpenAI 互換 |
|-----------|-------------|
| `client.messages.create()` | `client.chat.completions.create()` |
| `system=SYSTEM` | `messages` の先頭に `{"role": "system", ...}` を追加 |
| `tools[].input_schema` | `tools[].function.parameters` |
| `stop_reason == "tool_use"` | `finish_reason == "tool_calls"` |
| `content[].type == "tool_use"` | `message.tool_calls` |
| `block.id` / `block.name` / `block.input` | `tool_call.id` / `tool_call.function.name` / `json.loads(arguments)` |
| `tool_result` メッセージブロック | `{"role": "tool", "tool_call_id": ...}` |

## 既知の制限事項

- OpenAI 互換エンドポイントの `tool_choice` パラメータのセマンティクスは Anthropic とわずかに異なります
- 一部の国産モデルは並列ツール呼び出し（parallel tool calls）をサポートしていません
- コンテキストウィンドウサイズはモデルにより異なるため、それに応じて `max_tokens` を調整してください
