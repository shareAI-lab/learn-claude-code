# API Reference: embeddings.py

**Language**: Python

**Source**: `src/openrouter/embeddings.py`

---

## Classes

### GenerateAcceptEnum

**Inherits from**: str, Enum



### Embeddings

Text embedding endpoints

**Inherits from**: BaseSDK

#### Methods

##### generate(self) → operations.CreateEmbeddingsResponse

Submit an embedding request

Submits an embedding request to the embeddings router

:param input:
:param model:
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param encoding_format:
:param dimensions:
:param user:
:param provider: Provider routing preferences for the request.
:param input_type:
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateEmbeddingsResponse`


##### generate_async(self) → operations.CreateEmbeddingsResponse

Submit an embedding request

Submits an embedding request to the embeddings router

:param input:
:param model:
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param encoding_format:
:param dimensions:
:param user:
:param provider: Provider routing preferences for the request.
:param input_type:
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param accept_header_override: Override the default accept header for this method
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateEmbeddingsResponse`


##### list_models(self) → components.ModelsListResponse

List all embeddings models

Returns a list of all available embeddings models and their properties

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `components.ModelsListResponse`


##### list_models_async(self) → components.ModelsListResponse

List all embeddings models

Returns a list of all available embeddings models and their properties

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `components.ModelsListResponse`



