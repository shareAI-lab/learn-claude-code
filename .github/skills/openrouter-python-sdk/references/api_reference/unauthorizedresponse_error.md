# API Reference: unauthorizedresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/unauthorizedresponse_error.py`

---

## Classes

### UnauthorizedResponseErrorData

**Inherits from**: BaseModel



### UnauthorizedResponseError

Unauthorized - Authentication required or invalid credentials

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: UnauthorizedResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | UnauthorizedResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



