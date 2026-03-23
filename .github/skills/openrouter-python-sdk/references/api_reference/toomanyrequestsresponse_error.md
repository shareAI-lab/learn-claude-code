# API Reference: toomanyrequestsresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/toomanyrequestsresponse_error.py`

---

## Classes

### TooManyRequestsResponseErrorData

**Inherits from**: BaseModel



### TooManyRequestsResponseError

Too Many Requests - Rate limit exceeded

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: TooManyRequestsResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | TooManyRequestsResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



