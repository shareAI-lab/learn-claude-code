# API Reference: api_keys.py

**Language**: Python

**Source**: `src/openrouter/api_keys.py`

---

## Classes

### APIKeys

API key management endpoints

**Inherits from**: BaseSDK

#### Methods

##### list(self) → operations.ListResponse

List API keys

List all API keys for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param include_disabled: Whether to include disabled API keys in the response
:param offset: Number of API keys to skip for pagination
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListResponse`


##### list_async(self) → operations.ListResponse

List API keys

List all API keys for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param include_disabled: Whether to include disabled API keys in the response
:param offset: Number of API keys to skip for pagination
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListResponse`


##### create(self) → operations.CreateKeysResponse

Create a new API key

Create a new API key for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param name: Name for the new API key
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param limit: Optional spending limit for the API key in USD
:param limit_reset: Type of limit reset for the API key (daily, weekly, monthly, or null for no reset). Resets happen automatically at midnight UTC, and weeks are Monday through Sunday.
:param include_byok_in_limit: Whether to include BYOK usage in the limit
:param expires_at: Optional ISO 8601 UTC timestamp when the API key should expire. Must be UTC, other timezones will be rejected
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateKeysResponse`


##### create_async(self) → operations.CreateKeysResponse

Create a new API key

Create a new API key for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param name: Name for the new API key
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param limit: Optional spending limit for the API key in USD
:param limit_reset: Type of limit reset for the API key (daily, weekly, monthly, or null for no reset). Resets happen automatically at midnight UTC, and weeks are Monday through Sunday.
:param include_byok_in_limit: Whether to include BYOK usage in the limit
:param expires_at: Optional ISO 8601 UTC timestamp when the API key should expire. Must be UTC, other timezones will be rejected
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateKeysResponse`


##### update(self) → operations.UpdateKeysResponse

Update an API key

Update an existing API key. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param hash: The hash identifier of the API key to update
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param name: New name for the API key
:param disabled: Whether to disable the API key
:param limit: New spending limit for the API key in USD
:param limit_reset: New limit reset type for the API key (daily, weekly, monthly, or null for no reset). Resets happen automatically at midnight UTC, and weeks are Monday through Sunday.
:param include_byok_in_limit: Whether to include BYOK usage in the limit
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.UpdateKeysResponse`


##### update_async(self) → operations.UpdateKeysResponse

Update an API key

Update an existing API key. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param hash: The hash identifier of the API key to update
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param name: New name for the API key
:param disabled: Whether to disable the API key
:param limit: New spending limit for the API key in USD
:param limit_reset: New limit reset type for the API key (daily, weekly, monthly, or null for no reset). Resets happen automatically at midnight UTC, and weeks are Monday through Sunday.
:param include_byok_in_limit: Whether to include BYOK usage in the limit
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.UpdateKeysResponse`


##### delete(self) → operations.DeleteKeysResponse

Delete an API key

Delete an existing API key. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param hash: The hash identifier of the API key to delete
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

**Returns**: `operations.DeleteKeysResponse`


##### delete_async(self) → operations.DeleteKeysResponse

Delete an API key

Delete an existing API key. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param hash: The hash identifier of the API key to delete
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

**Returns**: `operations.DeleteKeysResponse`


##### get(self) → operations.GetKeyResponse

Get a single API key

Get a single API key by hash. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param hash: The hash identifier of the API key to retrieve
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

**Returns**: `operations.GetKeyResponse`


##### get_async(self) → operations.GetKeyResponse

Get a single API key

Get a single API key by hash. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param hash: The hash identifier of the API key to retrieve
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

**Returns**: `operations.GetKeyResponse`


##### get_current_key_metadata(self) → operations.GetCurrentKeyResponse

Get current API key

Get information on the API key associated with the current authentication session

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

**Returns**: `operations.GetCurrentKeyResponse`


##### get_current_key_metadata_async(self) → operations.GetCurrentKeyResponse

Get current API key

Get information on the API key associated with the current authentication session

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

**Returns**: `operations.GetCurrentKeyResponse`



