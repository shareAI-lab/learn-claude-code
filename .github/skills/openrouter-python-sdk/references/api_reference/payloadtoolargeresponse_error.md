# API Reference: payloadtoolargeresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/payloadtoolargeresponse_error.py`

---

## Classes

### PayloadTooLargeResponseErrorData

**Inherits from**: BaseModel



### PayloadTooLargeResponseError

Payload Too Large - Request payload exceeds size limits

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: PayloadTooLargeResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | PayloadTooLargeResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



