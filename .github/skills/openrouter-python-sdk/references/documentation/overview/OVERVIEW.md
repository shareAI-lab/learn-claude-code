# OpenRouter Python SDK

The OpenRouter Python SDK is a type-safe toolkit for building AI applications with access to 300+ language models through a unified API.

## Why use the OpenRouter SDK?

Integrating AI models into applications involves handling different provider APIs, managing model-specific requirements, and avoiding common implementation mistakes. The OpenRouter SDK standardizes these integrations and protects you from footguns.

```python
from openrouter import OpenRouter
import os

with OpenRouter(
    api_key=os.getenv("OPENROUTER_API_KEY")
) as client:
    response = client.chat.send(
        model="minimax/minimax-m2",
        messages=[
            {"role": "user", "content": "Explain quantum computing"}
        ]
    )
```

The SDK provides three core benefits:

### Auto-generated from API specifications

The SDK is automatically generated from OpenRouter's OpenAPI specs and updated with every API change. New models, parameters, and features appear in your IDE autocomplete immediately. No manual updates. No version drift.

```python
# When new models launch, they're available instantly
response = client.chat.send(
    model="minimax/minimax-m2"
)
```

### Type-safe by default

Every parameter, response field, and configuration option is fully typed with Python type hints and validated with Pydantic. Invalid configurations are caught at runtime with clear error messages.

```python
response = client.chat.send(
    model="minimax/minimax-m2",
    messages=[
        {"role": "user", "content": "Hello"}
        # ← Pydantic validates message structure
    ],
    temperature=0.7,  # ← Type-checked and validated
    stream=True       # ← Response type changes based on this
)
```

**Actionable error messages:**

```python
# Instead of generic errors, get specific guidance:
# "Model 'openai/o1-preview' requires at least 2 messages.
#  You provided 1 message. Add a system or user message."
```

**Type-safe streaming:**

```python
stream = client.chat.send(
    model="minimax/minimax-m2",
    messages=[{"role": "user", "content": "Write a story"}],
    stream=True
)

for event in stream:
    # Full type information for streaming responses
    content = event.choices[0].delta.content if event.choices else None
```

**Async support:**

```python
import asyncio

async def main():
    async with OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY")
    ) as client:
        response = await client.chat.send_async(
            model="minimax/minimax-m2",
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(response.choices[0].message.content)

asyncio.run(main())
```

## Installation

```bash
# Using uv (recommended)
uv add openrouter

# Using pip
pip install openrouter

# Using poetry
poetry add openrouter
```

**Requirements:** Python 3.9 or higher

Get your API key from [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys).

## Quick start

```python
from openrouter import OpenRouter
import os

with OpenRouter(
    api_key=os.getenv("OPENROUTER_API_KEY")
) as client:
    response = client.chat.send(
        model="minimax/minimax-m2",
        messages=[
            {"role": "user", "content": "Hello!"}
        ]
    )

    print(response.choices[0].message.content)
```
