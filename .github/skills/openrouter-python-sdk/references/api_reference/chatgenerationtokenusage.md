# API Reference: chatgenerationtokenusage.py

**Language**: Python

**Source**: `src/openrouter/components/chatgenerationtokenusage.py`

---

## Classes

### CompletionTokensDetailsTypedDict

Detailed completion token usage

**Inherits from**: TypedDict



### CompletionTokensDetails

Detailed completion token usage

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### PromptTokensDetailsTypedDict

Detailed prompt token usage

**Inherits from**: TypedDict



### PromptTokensDetails

Detailed prompt token usage

**Inherits from**: BaseModel



### ChatGenerationTokenUsageTypedDict

Token usage statistics

**Inherits from**: TypedDict



### ChatGenerationTokenUsage

Token usage statistics

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |



