# API Reference: openresponsesrequest.py

**Language**: Python

**Source**: `src/openrouter/components/openresponsesrequest.py`

---

## Classes

### OpenResponsesRequestToolFunctionTypedDict

Function tool definition

**Inherits from**: TypedDict



### OpenResponsesRequestToolFunction

Function tool definition

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### OpenResponsesRequestMaxPriceTypedDict

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.

**Inherits from**: TypedDict



### OpenResponsesRequestMaxPrice

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.

**Inherits from**: BaseModel



### OpenResponsesRequestProviderTypedDict

When multiple model providers are available, optionally indicate your routing preference.

**Inherits from**: TypedDict



### OpenResponsesRequestProvider

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




### OpenResponsesRequestPluginResponseHealingTypedDict

**Inherits from**: TypedDict



### OpenResponsesRequestPluginResponseHealing

**Inherits from**: BaseModel



### OpenResponsesRequestPluginFileParserTypedDict

**Inherits from**: TypedDict



### OpenResponsesRequestPluginFileParser

**Inherits from**: BaseModel



### OpenResponsesRequestPluginWebTypedDict

**Inherits from**: TypedDict



### OpenResponsesRequestPluginWeb

**Inherits from**: BaseModel



### OpenResponsesRequestPluginModerationTypedDict

**Inherits from**: TypedDict



### OpenResponsesRequestPluginModeration

**Inherits from**: BaseModel



### OpenResponsesRequestPluginAutoRouterTypedDict

**Inherits from**: TypedDict



### OpenResponsesRequestPluginAutoRouter

**Inherits from**: BaseModel



### OpenResponsesRequestTraceTypedDict

Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.

**Inherits from**: TypedDict



### OpenResponsesRequestTrace

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




### OpenResponsesRequestTypedDict

Request schema for Responses endpoint

**Inherits from**: TypedDict



### OpenResponsesRequest

Request schema for Responses endpoint

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |



