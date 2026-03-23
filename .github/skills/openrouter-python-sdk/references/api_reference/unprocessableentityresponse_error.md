# API Reference: unprocessableentityresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/unprocessableentityresponse_error.py`

---

## Classes

### UnprocessableEntityResponseErrorData

**Inherits from**: BaseModel



### UnprocessableEntityResponseError

Unprocessable Entity - Semantic validation failure

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: UnprocessableEntityResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | UnprocessableEntityResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



