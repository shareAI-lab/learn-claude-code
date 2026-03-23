# API Reference: chatgenerationparams.py

**Language**: Python

**Source**: `src/openrouter/components/chatgenerationparams.py`

---

## Classes

### ChatGenerationParamsProviderSortConfigTypedDict

**Inherits from**: TypedDict



### ChatGenerationParamsProviderSortConfig

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### ChatGenerationParamsMaxPriceTypedDict

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.

**Inherits from**: TypedDict



### ChatGenerationParamsMaxPrice

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.

**Inherits from**: BaseModel



### ChatGenerationParamsProviderTypedDict

When multiple model providers are available, optionally indicate your routing preference.

**Inherits from**: TypedDict



### ChatGenerationParamsProvider

When multiple model providers are available, optionally indicate your routing preference.

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### ChatGenerationParamsPluginResponseHealingTypedDict

**Inherits from**: TypedDict



### ChatGenerationParamsPluginResponseHealing

**Inherits from**: BaseModel



### ChatGenerationParamsPluginFileParserTypedDict

**Inherits from**: TypedDict



### ChatGenerationParamsPluginFileParser

**Inherits from**: BaseModel



### ChatGenerationParamsPluginWebTypedDict

**Inherits from**: TypedDict



### ChatGenerationParamsPluginWeb

**Inherits from**: BaseModel



### ChatGenerationParamsPluginModerationTypedDict

**Inherits from**: TypedDict



### ChatGenerationParamsPluginModeration

**Inherits from**: BaseModel



### ChatGenerationParamsPluginAutoRouterTypedDict

**Inherits from**: TypedDict



### ChatGenerationParamsPluginAutoRouter

**Inherits from**: BaseModel



### ChatGenerationParamsTraceTypedDict

Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.

**Inherits from**: TypedDict



### ChatGenerationParamsTrace

Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.

**Inherits from**: BaseModel

#### Methods

##### additional_properties(self)

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### additional_properties(self, value)

**Decorators**: `@additional_properties.setter`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| value | None | - | - |




### ReasoningTypedDict

Configuration options for reasoning models

**Inherits from**: TypedDict



### Reasoning

Configuration options for reasoning models

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### ChatGenerationParamsTypedDict

Chat completion request parameters

**Inherits from**: TypedDict



### ChatGenerationParams

Chat completion request parameters

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |



