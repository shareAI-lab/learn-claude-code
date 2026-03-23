# API Reference: oauth_create_sha256_code_challenge.py

**Language**: Python

**Source**: `src/openrouter/utils/oauth_create_sha256_code_challenge.py`

---

## Classes

### CreateSHA256CodeChallengeRequest

Request parameters for creating a SHA-256 code challenge.

If not provided, a random code verifier will be generated.
If provided, must be 43-128 characters and contain only unreserved
characters [A-Za-z0-9-._~] per RFC 7636.

**Inherits from**: (none)



### CreateSHA256CodeChallengeResponse

Response containing the code challenge and verifier

**Inherits from**: (none)



## Functions

### _array_buffer_to_base64_url(data: bytes) → str

Convert bytes to base64url encoding (RFC 4648)

Args:
    data: Bytes to encode

Returns:
    Base64url encoded string

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| data | bytes | - | - |

**Returns**: `str`



### _generate_code_verifier() → str

Generate a cryptographically random code verifier per RFC 7636

RFC 7636 recommends 32 octets of random data, base64url encoded = 43 chars

Returns:
    A random code verifier string

**Returns**: `str`



### _validate_code_verifier(code_verifier: str) → None

Validate code verifier according to RFC 7636

Args:
    code_verifier: The code verifier to validate

Raises:
    ValueError: If the code verifier is invalid

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| code_verifier | str | - | - |

**Returns**: `None`



### oauth_create_sha256_code_challenge(params: Optional[CreateSHA256CodeChallengeRequest] = None) → CreateSHA256CodeChallengeResponse

Generate a SHA-256 code challenge for PKCE

Generates a SHA-256 code challenge and corresponding code verifier for use
in the PKCE extension to OAuth2. If no code verifier is provided, a random
one will be generated according to RFC 7636 (32 random bytes, base64url
encoded). If a code verifier is provided, it must be 43-128 characters and
contain only unreserved characters [A-Za-z0-9-._~].

Args:
    params: Optional request parameters. If None, a random code verifier will be generated.

Returns:
    CreateSHA256CodeChallengeResponse containing the code challenge and verifier

Raises:
    ValueError: If the provided code verifier is invalid

See Also:
    - https://openrouter.ai/docs/use-cases/oauth-pkce
    - https://datatracker.ietf.org/doc/html/rfc7636

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| params | Optional[CreateSHA256CodeChallengeRequest] | None | - |

**Returns**: `CreateSHA256CodeChallengeResponse`


