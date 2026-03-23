# API Reference: forbiddenresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/forbiddenresponse_error.py`

---

## Classes

### ForbiddenResponseErrorData

**Inherits from**: BaseModel



### ForbiddenResponseError

Forbidden - Authentication successful but insufficient permissions

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: ForbiddenResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | ForbiddenResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



