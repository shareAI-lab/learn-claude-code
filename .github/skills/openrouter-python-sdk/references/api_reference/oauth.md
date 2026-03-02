# API Reference: oauth.py

**Language**: Python

**Source**: `src/openrouter/oauth.py`

---

## Classes

### OAuth

OAuth authentication endpoints

**Inherits from**: BaseSDK

#### Methods

##### exchange_auth_code_for_api_key(self) → operations.ExchangeAuthCodeForAPIKeyResponse

Exchange authorization code for API key

Exchange an authorization code from the PKCE flow for a user-controlled API key

:param code: The authorization code received from the OAuth redirect
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param code_verifier: The code verifier if code_challenge was used in the authorization request
:param code_challenge_method: The method used to generate the code challenge
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ExchangeAuthCodeForAPIKeyResponse`


##### exchange_auth_code_for_api_key_async(self) → operations.ExchangeAuthCodeForAPIKeyResponse

Exchange authorization code for API key

Exchange an authorization code from the PKCE flow for a user-controlled API key

:param code: The authorization code received from the OAuth redirect
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param code_verifier: The code verifier if code_challenge was used in the authorization request
:param code_challenge_method: The method used to generate the code challenge
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ExchangeAuthCodeForAPIKeyResponse`


##### create_auth_code(self) → operations.CreateAuthKeysCodeResponse

Create authorization code

Create an authorization code for the PKCE flow to generate a user-controlled API key

:param callback_url: The callback URL to redirect to after authorization. Note, only https URLs on ports 443 and 3000 are allowed.
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param code_challenge: PKCE code challenge for enhanced security
:param code_challenge_method: The method used to generate the code challenge
:param limit: Credit limit for the API key to be created
:param expires_at: Optional expiration time for the API key to be created
:param key_label: Optional custom label for the API key. Defaults to the app name if not provided.
:param usage_limit_type: Optional credit limit reset interval. When set, the credit limit resets on this interval.
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateAuthKeysCodeResponse`


##### create_auth_code_async(self) → operations.CreateAuthKeysCodeResponse

Create authorization code

Create an authorization code for the PKCE flow to generate a user-controlled API key

:param callback_url: The callback URL to redirect to after authorization. Note, only https URLs on ports 443 and 3000 are allowed.
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param code_challenge: PKCE code challenge for enhanced security
:param code_challenge_method: The method used to generate the code challenge
:param limit: Credit limit for the API key to be created
:param expires_at: Optional expiration time for the API key to be created
:param key_label: Optional custom label for the API key. Defaults to the app name if not provided.
:param usage_limit_type: Optional credit limit reset interval. When set, the credit limit resets on this interval.
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateAuthKeysCodeResponse`



