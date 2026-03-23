# API Reference: oauth_create_authorization_url.py

**Language**: Python

**Source**: `src/openrouter/utils/oauth_create_authorization_url.py`

---

## Classes

### CreateAuthorizationUrlRequestBase

Base request parameters for creating an authorization URL

**Inherits from**: (none)



### CreateAuthorizationUrlRequestWithPKCE

Request parameters with PKCE for creating an authorization URL

**Inherits from**: (none)



## Functions

### _get_server_url(client: 'OpenRouter') → str

Get the server URL from the client configuration

Args:
    client: OpenRouter client instance

Returns:
    The server URL

Raises:
    ValueError: If no server URL is configured

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| client | 'OpenRouter' | - | - |

**Returns**: `str`



### oauth_create_authorization_url(client: 'OpenRouter', params: CreateAuthorizationUrlRequest) → str

Generate an OAuth2 authorization URL

Generates a URL to redirect users to for authorizing your application. The
URL includes the provided callback URL and, if applicable, the code
challenge parameters for PKCE.

Args:
    client: OpenRouter client instance
    params: Request parameters including callback URL and optional PKCE parameters

Returns:
    The authorization URL as a string

Raises:
    ValueError: If no server URL is configured or parameters are invalid

See Also:
    - https://openrouter.ai/docs/use-cases/oauth-pkce

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| client | 'OpenRouter' | - | - |
| params | CreateAuthorizationUrlRequest | - | - |

**Returns**: `str`


