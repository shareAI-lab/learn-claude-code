# API Reference: credits.py

**Language**: Python

**Source**: `src/openrouter/credits.py`

---

## Classes

### Credits

Credit management endpoints

**Inherits from**: BaseSDK

#### Methods

##### get_credits(self) → operations.GetCreditsResponse

Get remaining credits

Get total credits purchased and used for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

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

**Returns**: `operations.GetCreditsResponse`


##### get_credits_async(self) → operations.GetCreditsResponse

Get remaining credits

Get total credits purchased and used for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

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

**Returns**: `operations.GetCreditsResponse`


##### create_coinbase_charge(self) → operations.CreateCoinbaseChargeResponse

Create a Coinbase charge for crypto payment

Create a Coinbase charge for crypto payment

:param security:
:param amount:
:param sender:
:param chain_id:
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

**Returns**: `operations.CreateCoinbaseChargeResponse`


##### create_coinbase_charge_async(self) → operations.CreateCoinbaseChargeResponse

Create a Coinbase charge for crypto payment

Create a Coinbase charge for crypto payment

:param security:
:param amount:
:param sender:
:param chain_id:
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

**Returns**: `operations.CreateCoinbaseChargeResponse`



