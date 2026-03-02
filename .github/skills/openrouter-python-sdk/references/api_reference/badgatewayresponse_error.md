# API Reference: badgatewayresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/badgatewayresponse_error.py`

---

## Classes

### BadGatewayResponseErrorData

**Inherits from**: BaseModel



### BadGatewayResponseError

Bad Gateway - Provider/upstream API failure

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: BadGatewayResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | BadGatewayResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



