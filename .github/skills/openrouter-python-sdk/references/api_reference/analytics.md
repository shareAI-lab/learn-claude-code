# API Reference: analytics.py

**Language**: Python

**Source**: `src/openrouter/analytics.py`

---

## Classes

### Analytics

Analytics and usage endpoints

**Inherits from**: BaseSDK

#### Methods

##### get_user_activity(self) → operations.GetUserActivityResponse

Get user activity grouped by endpoint

Returns user activity data grouped by endpoint for the last 30 (completed) UTC days. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param date_: Filter by a single UTC date in the last 30 days (YYYY-MM-DD format).
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.GetUserActivityResponse`


##### get_user_activity_async(self) → operations.GetUserActivityResponse

Get user activity grouped by endpoint

Returns user activity data grouped by endpoint for the last 30 (completed) UTC days. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param date_: Filter by a single UTC date in the last 30 days (YYYY-MM-DD format).
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.GetUserActivityResponse`



