# API Reference: responses.py

**Language**: Python

**Source**: `src/openrouter/responses.py`

---

## Classes

### SendAcceptEnum

**Inherits from**: str, Enum



### Responses

beta.responses endpoints

**Inherits from**: BaseSDK

#### Methods

##### send(self) → components.OpenResponsesNonStreamingResponse

Create a response

Creates a streaming or non-streaming response using OpenResponses API format

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param input: Input for a response request - can be a string or array of items
:param instructions:
:param metadata: Metadata key-value pairs for the request. Keys must be ≤64 characters and cannot contain brackets. Values must be ≤512 characters. Maximum 16 pairs allowed.
:param tools:
:param tool_choice:
:param parallel_tool_calls:
:param model:
:param models:
:param text: Text output configuration including format and verbosity
:param reasoning: Configuration for reasoning mode in the response
:param max_output_tokens:
:param temperature:
:param top_p:
:param top_logprobs:
:param max_tool_calls:
:param presence_penalty:
:param frequency_penalty:
:param top_k:
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/features/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param prompt_cache_key:
:param previous_response_id:
:param prompt:
:param include:
:param background:
:param safety_identifier:
:param service_tier:
:param truncation:
:param stream:
:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: A unique identifier representing your end-user, which helps distinguish between different users of your app. This allows your app to identify specific users in case of abuse reports, preventing your entire app from being affected by the actions of individual users. Maximum of 128 characters.
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
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

**Returns**: `components.OpenResponsesNonStreamingResponse`


##### send(self) → eventstreaming.EventStream[components.OpenResponsesStreamEvent]

Create a response

Creates a streaming or non-streaming response using OpenResponses API format

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param input: Input for a response request - can be a string or array of items
:param instructions:
:param metadata: Metadata key-value pairs for the request. Keys must be ≤64 characters and cannot contain brackets. Values must be ≤512 characters. Maximum 16 pairs allowed.
:param tools:
:param tool_choice:
:param parallel_tool_calls:
:param model:
:param models:
:param text: Text output configuration including format and verbosity
:param reasoning: Configuration for reasoning mode in the response
:param max_output_tokens:
:param temperature:
:param top_p:
:param top_logprobs:
:param max_tool_calls:
:param presence_penalty:
:param frequency_penalty:
:param top_k:
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/features/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param prompt_cache_key:
:param previous_response_id:
:param prompt:
:param include:
:param background:
:param safety_identifier:
:param service_tier:
:param truncation:
:param stream:
:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: A unique identifier representing your end-user, which helps distinguish between different users of your app. This allows your app to identify specific users in case of abuse reports, preventing your entire app from being affected by the actions of individual users. Maximum of 128 characters.
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
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

**Returns**: `eventstreaming.EventStream[components.OpenResponsesStreamEvent]`


##### send(self) → operations.CreateResponsesResponse

Create a response

Creates a streaming or non-streaming response using OpenResponses API format

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param input: Input for a response request - can be a string or array of items
:param instructions:
:param metadata: Metadata key-value pairs for the request. Keys must be ≤64 characters and cannot contain brackets. Values must be ≤512 characters. Maximum 16 pairs allowed.
:param tools:
:param tool_choice:
:param parallel_tool_calls:
:param model:
:param models:
:param text: Text output configuration including format and verbosity
:param reasoning: Configuration for reasoning mode in the response
:param max_output_tokens:
:param temperature:
:param top_p:
:param top_logprobs:
:param max_tool_calls:
:param presence_penalty:
:param frequency_penalty:
:param top_k:
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/features/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param prompt_cache_key:
:param previous_response_id:
:param prompt:
:param include:
:param background:
:param safety_identifier:
:param service_tier:
:param truncation:
:param stream:
:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: A unique identifier representing your end-user, which helps distinguish between different users of your app. This allows your app to identify specific users in case of abuse reports, preventing your entire app from being affected by the actions of individual users. Maximum of 128 characters.
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateResponsesResponse`


##### send_async(self) → components.OpenResponsesNonStreamingResponse

Create a response

Creates a streaming or non-streaming response using OpenResponses API format

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param input: Input for a response request - can be a string or array of items
:param instructions:
:param metadata: Metadata key-value pairs for the request. Keys must be ≤64 characters and cannot contain brackets. Values must be ≤512 characters. Maximum 16 pairs allowed.
:param tools:
:param tool_choice:
:param parallel_tool_calls:
:param model:
:param models:
:param text: Text output configuration including format and verbosity
:param reasoning: Configuration for reasoning mode in the response
:param max_output_tokens:
:param temperature:
:param top_p:
:param top_logprobs:
:param max_tool_calls:
:param presence_penalty:
:param frequency_penalty:
:param top_k:
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/features/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param prompt_cache_key:
:param previous_response_id:
:param prompt:
:param include:
:param background:
:param safety_identifier:
:param service_tier:
:param truncation:
:param stream:
:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: A unique identifier representing your end-user, which helps distinguish between different users of your app. This allows your app to identify specific users in case of abuse reports, preventing your entire app from being affected by the actions of individual users. Maximum of 128 characters.
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
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

**Returns**: `components.OpenResponsesNonStreamingResponse`


##### send_async(self) → eventstreaming.EventStreamAsync[components.OpenResponsesStreamEvent]

Create a response

Creates a streaming or non-streaming response using OpenResponses API format

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param input: Input for a response request - can be a string or array of items
:param instructions:
:param metadata: Metadata key-value pairs for the request. Keys must be ≤64 characters and cannot contain brackets. Values must be ≤512 characters. Maximum 16 pairs allowed.
:param tools:
:param tool_choice:
:param parallel_tool_calls:
:param model:
:param models:
:param text: Text output configuration including format and verbosity
:param reasoning: Configuration for reasoning mode in the response
:param max_output_tokens:
:param temperature:
:param top_p:
:param top_logprobs:
:param max_tool_calls:
:param presence_penalty:
:param frequency_penalty:
:param top_k:
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/features/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param prompt_cache_key:
:param previous_response_id:
:param prompt:
:param include:
:param background:
:param safety_identifier:
:param service_tier:
:param truncation:
:param stream:
:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: A unique identifier representing your end-user, which helps distinguish between different users of your app. This allows your app to identify specific users in case of abuse reports, preventing your entire app from being affected by the actions of individual users. Maximum of 128 characters.
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
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

**Returns**: `eventstreaming.EventStreamAsync[components.OpenResponsesStreamEvent]`


##### send_async(self) → operations.CreateResponsesResponse

Create a response

Creates a streaming or non-streaming response using OpenResponses API format

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param input: Input for a response request - can be a string or array of items
:param instructions:
:param metadata: Metadata key-value pairs for the request. Keys must be ≤64 characters and cannot contain brackets. Values must be ≤512 characters. Maximum 16 pairs allowed.
:param tools:
:param tool_choice:
:param parallel_tool_calls:
:param model:
:param models:
:param text: Text output configuration including format and verbosity
:param reasoning: Configuration for reasoning mode in the response
:param max_output_tokens:
:param temperature:
:param top_p:
:param top_logprobs:
:param max_tool_calls:
:param presence_penalty:
:param frequency_penalty:
:param top_k:
:param image_config: Provider-specific image configuration options. Keys and values vary by model/provider. See https://openrouter.ai/docs/features/multimodal/image-generation for more details.
:param modalities: Output modalities for the response. Supported values are \"text\" and \"image\".
:param prompt_cache_key:
:param previous_response_id:
:param prompt:
:param include:
:param background:
:param safety_identifier:
:param service_tier:
:param truncation:
:param stream:
:param provider: When multiple model providers are available, optionally indicate your routing preference.
:param plugins: Plugins you want to enable for this request, including their settings.
:param user: A unique identifier representing your end-user, which helps distinguish between different users of your app. This allows your app to identify specific users in case of abuse reports, preventing your entire app from being affected by the actions of individual users. Maximum of 128 characters.
:param session_id: A unique identifier for grouping related requests (e.g., a conversation or agent workflow) for observability. If provided in both the request body and the x-session-id header, the body value takes precedence. Maximum of 128 characters.
:param trace: Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateResponsesResponse`



