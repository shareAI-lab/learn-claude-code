# API Reference: requesttimeoutresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/requesttimeoutresponse_error.py`

---

## Classes

### RequestTimeoutResponseErrorData

**Inherits from**: BaseModel



### RequestTimeoutResponseError

Request Timeout - Operation exceeded time limit

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: RequestTimeoutResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | RequestTimeoutResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



