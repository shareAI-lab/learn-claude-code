# API Reference: sdk.py

**Language**: Python

**Source**: `src/openrouter/sdk.py`

---

## Classes

### OpenRouter

OpenRouter API: OpenAI-compatible API with additional OpenRouter features
https://openrouter.ai/docs - OpenRouter Documentation

**Inherits from**: BaseSDK

#### Methods

##### __init__(self, api_key: Optional[Union[Optional[str], Callable[[], Optional[str]]]] = None, http_referer: Optional[str] = None, x_title: Optional[str] = None, server: Optional[str] = None, server_url: Optional[str] = None, url_params: Optional[Dict[str, str]] = None, client: Optional[HttpClient] = None, async_client: Optional[AsyncHttpClient] = None, retry_config: OptionalNullable[RetryConfig] = UNSET, timeout_ms: Optional[int] = None, debug_logger: Optional[Logger] = None) → None

Instantiates the SDK configuring it with the provided parameters.

:param api_key: The api_key required for authentication
:param http_referer: Configures the http_referer parameter for all supported operations
:param x_title: Configures the x_title parameter for all supported operations
:param server: The server by name to use for all methods
:param server_url: The server URL to use for all methods
:param url_params: Parameters to optionally template the server URL with
:param client: The HTTP client to use for all synchronous methods
:param async_client: The Async HTTP client to use for all asynchronous methods
:param retry_config: The retry configuration to use for all supported methods
:param timeout_ms: Optional request timeout applied to each operation in milliseconds

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| api_key | Optional[Union[Optional[str], Callable[[], Optional[str]]]] | None | - |
| http_referer | Optional[str] | None | - |
| x_title | Optional[str] | None | - |
| server | Optional[str] | None | - |
| server_url | Optional[str] | None | - |
| url_params | Optional[Dict[str, str]] | None | - |
| client | Optional[HttpClient] | None | - |
| async_client | Optional[AsyncHttpClient] | None | - |
| retry_config | OptionalNullable[RetryConfig] | UNSET | - |
| timeout_ms | Optional[int] | None | - |
| debug_logger | Optional[Logger] | None | - |

**Returns**: `None`


##### dynamic_import(self, modname, retries = 3)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| modname | None | - | - |
| retries | None | 3 | - |


##### __getattr__(self, name: str)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| name | str | - | - |


##### __dir__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __enter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __aenter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __exit__(self, exc_type, exc_val, exc_tb)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| exc_type | None | - | - |
| exc_val | None | - | - |
| exc_tb | None | - | - |


##### __aexit__(self, exc_type, exc_val, exc_tb)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| exc_type | None | - | - |
| exc_val | None | - | - |
| exc_tb | None | - | - |



