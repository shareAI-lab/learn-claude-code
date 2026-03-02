# API Reference: endpoints.py

**Language**: Python

**Source**: `src/openrouter/endpoints.py`

---

## Classes

### Endpoints

Endpoint information

**Inherits from**: BaseSDK

#### Methods

##### list(self) → operations.ListEndpointsResponse

List all endpoints for a model

:param author:
:param slug:
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

**Returns**: `operations.ListEndpointsResponse`


##### list_async(self) → operations.ListEndpointsResponse

List all endpoints for a model

:param author:
:param slug:
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

**Returns**: `operations.ListEndpointsResponse`


##### list_zdr_endpoints(self) → operations.ListEndpointsZdrResponse

Preview the impact of ZDR on the available endpoints

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

**Returns**: `operations.ListEndpointsZdrResponse`


##### list_zdr_endpoints_async(self) → operations.ListEndpointsZdrResponse

Preview the impact of ZDR on the available endpoints

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

**Returns**: `operations.ListEndpointsZdrResponse`



