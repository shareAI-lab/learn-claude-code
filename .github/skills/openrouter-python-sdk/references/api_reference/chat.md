# API Reference: chat.py

**Language**: Python

**Source**: `src/openrouter/chat.py`

---

## Classes

### SendAcceptEnum

**Inherits from**: str, Enum



### Chat

**Inherits from**: BaseSDK

#### Methods

##### send(self) → components.ChatResponse

Create a chat completion

Sends a request for a model response for the given chat conversation. Supports both streaming and non-streaming modes.

:param messages: List of messages for the conversation
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: Unique user identifier
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param model: Model to use for completion
:param models: Models to use for completion
:param frequency_penalty: Frequency penalty (-2.0 to 2.0)
:param logit_bias: Token logit bias adjustments
:param logprobs: Return log probabilities
:param top_logprobs: Number of top log probabilities to return (0-20)
:param max_completion_tokens: Maximum tokens in completion
:param max_tokens: Maximum tokens (deprecated, use max_completion_tokens)
:param metadata: Key-value pairs for additional object information (max 16 pairs, 64 char keys, 512 char values)
:param presence_penalty: Presence penalty (-2.0 to 2.0)
:param reasoning: Configuration options for reasoning models
:param response_format: Response format configuration
:param seed: Random seed for deterministic outputs
:param stop: Stop sequences (up to 4)
:param stream: Enable streaming response
:param stream_options: Streaming configuration options
:param temperature: Sampling temperature (0-2)
:param parallel_tool_calls:
:param tool_choice: Tool choice configuration
:param tools: Available tools for function calling
:param top_p: Nucleus sampling parameter (0-1)
:param debug: Debug options for inspecting request transformations (streaming only)
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/guides/overview/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Decorators**: `@overload`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `components.ChatResponse`


##### send(self) → eventstreaming.EventStream[components.ChatStreamingResponseChunk]

Create a chat completion

Sends a request for a model response for the given chat conversation. Supports both streaming and non-streaming modes.

:param messages: List of messages for the conversation
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: Unique user identifier
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param model: Model to use for completion
:param models: Models to use for completion
:param frequency_penalty: Frequency penalty (-2.0 to 2.0)
:param logit_bias: Token logit bias adjustments
:param logprobs: Return log probabilities
:param top_logprobs: Number of top log probabilities to return (0-20)
:param max_completion_tokens: Maximum tokens in completion
:param max_tokens: Maximum tokens (deprecated, use max_completion_tokens)
:param metadata: Key-value pairs for additional object information (max 16 pairs, 64 char keys, 512 char values)
:param presence_penalty: Presence penalty (-2.0 to 2.0)
:param reasoning: Configuration options for reasoning models
:param response_format: Response format configuration
:param seed: Random seed for deterministic outputs
:param stop: Stop sequences (up to 4)
:param stream: Enable streaming response
:param stream_options: Streaming configuration options
:param temperature: Sampling temperature (0-2)
:param parallel_tool_calls:
:param tool_choice: Tool choice configuration
:param tools: Available tools for function calling
:param top_p: Nucleus sampling parameter (0-1)
:param debug: Debug options for inspecting request transformations (streaming only)
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/guides/overview/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Decorators**: `@overload`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `eventstreaming.EventStream[components.ChatStreamingResponseChunk]`


##### send(self) → operations.SendChatCompletionRequestResponse

Create a chat completion

Sends a request for a model response for the given chat conversation. Supports both streaming and non-streaming modes.

:param messages: List of messages for the conversation
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: Unique user identifier
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param model: Model to use for completion
:param models: Models to use for completion
:param frequency_penalty: Frequency penalty (-2.0 to 2.0)
:param logit_bias: Token logit bias adjustments
:param logprobs: Return log probabilities
:param top_logprobs: Number of top log probabilities to return (0-20)
:param max_completion_tokens: Maximum tokens in completion
:param max_tokens: Maximum tokens (deprecated, use max_completion_tokens)
:param metadata: Key-value pairs for additional object information (max 16 pairs, 64 char keys, 512 char values)
:param presence_penalty: Presence penalty (-2.0 to 2.0)
:param reasoning: Configuration options for reasoning models
:param response_format: Response format configuration
:param seed: Random seed for deterministic outputs
:param stop: Stop sequences (up to 4)
:param stream: Enable streaming response
:param stream_options: Streaming configuration options
:param temperature: Sampling temperature (0-2)
:param parallel_tool_calls:
:param tool_choice: Tool choice configuration
:param tools: Available tools for function calling
:param top_p: Nucleus sampling parameter (0-1)
:param debug: Debug options for inspecting request transformations (streaming only)
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/guides/overview/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.SendChatCompletionRequestResponse`


##### send_async(self) → components.ChatResponse

Create a chat completion

Sends a request for a model response for the given chat conversation. Supports both streaming and non-streaming modes.

:param messages: List of messages for the conversation
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: Unique user identifier
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param model: Model to use for completion
:param models: Models to use for completion
:param frequency_penalty: Frequency penalty (-2.0 to 2.0)
:param logit_bias: Token logit bias adjustments
:param logprobs: Return log probabilities
:param top_logprobs: Number of top log probabilities to return (0-20)
:param max_completion_tokens: Maximum tokens in completion
:param max_tokens: Maximum tokens (deprecated, use max_completion_tokens)
:param metadata: Key-value pairs for additional object information (max 16 pairs, 64 char keys, 512 char values)
:param presence_penalty: Presence penalty (-2.0 to 2.0)
:param reasoning: Configuration options for reasoning models
:param response_format: Response format configuration
:param seed: Random seed for deterministic outputs
:param stop: Stop sequences (up to 4)
:param stream: Enable streaming response
:param stream_options: Streaming configuration options
:param temperature: Sampling temperature (0-2)
:param parallel_tool_calls:
:param tool_choice: Tool choice configuration
:param tools: Available tools for function calling
:param top_p: Nucleus sampling parameter (0-1)
:param debug: Debug options for inspecting request transformations (streaming only)
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/guides/overview/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Decorators**: `@overload`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `components.ChatResponse`


##### send_async(self) → eventstreaming.EventStreamAsync[components.ChatStreamingResponseChunk]

Create a chat completion

Sends a request for a model response for the given chat conversation. Supports both streaming and non-streaming modes.

:param messages: List of messages for the conversation
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: Unique user identifier
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param model: Model to use for completion
:param models: Models to use for completion
:param frequency_penalty: Frequency penalty (-2.0 to 2.0)
:param logit_bias: Token logit bias adjustments
:param logprobs: Return log probabilities
:param top_logprobs: Number of top log probabilities to return (0-20)
:param max_completion_tokens: Maximum tokens in completion
:param max_tokens: Maximum tokens (deprecated, use max_completion_tokens)
:param metadata: Key-value pairs for additional object information (max 16 pairs, 64 char keys, 512 char values)
:param presence_penalty: Presence penalty (-2.0 to 2.0)
:param reasoning: Configuration options for reasoning models
:param response_format: Response format configuration
:param seed: Random seed for deterministic outputs
:param stop: Stop sequences (up to 4)
:param stream: Enable streaming response
:param stream_options: Streaming configuration options
:param temperature: Sampling temperature (0-2)
:param parallel_tool_calls:
:param tool_choice: Tool choice configuration
:param tools: Available tools for function calling
:param top_p: Nucleus sampling parameter (0-1)
:param debug: Debug options for inspecting request transformations (streaming only)
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/guides/overview/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Decorators**: `@overload`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `eventstreaming.EventStreamAsync[components.ChatStreamingResponseChunk]`


##### send_async(self) → operations.SendChatCompletionRequestResponse

Create a chat completion

Sends a request for a model response for the given chat conversation. Supports both streaming and non-streaming modes.

:param messages: List of messages for the conversation
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: Unique user identifier
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param model: Model to use for completion
:param models: Models to use for completion
:param frequency_penalty: Frequency penalty (-2.0 to 2.0)
:param logit_bias: Token logit bias adjustments
:param logprobs: Return log probabilities
:param top_logprobs: Number of top log probabilities to return (0-20)
:param max_completion_tokens: Maximum tokens in completion
:param max_tokens: Maximum tokens (deprecated, use max_completion_tokens)
:param metadata: Key-value pairs for additional object information (max 16 pairs, 64 char keys, 512 char values)
:param presence_penalty: Presence penalty (-2.0 to 2.0)
:param reasoning: Configuration options for reasoning models
:param response_format: Response format configuration
:param seed: Random seed for deterministic outputs
:param stop: Stop sequences (up to 4)
:param stream: Enable streaming response
:param stream_options: Streaming configuration options
:param temperature: Sampling temperature (0-2)
:param parallel_tool_calls:
:param tool_choice: Tool choice configuration
:param tools: Available tools for function calling
:param top_p: Nucleus sampling parameter (0-1)
:param debug: Debug options for inspecting request transformations (streaming only)
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/guides/overview/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.SendChatCompletionRequestResponse`



