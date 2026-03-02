# API Reference: internalserverresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/internalserverresponse_error.py`

---

## Classes

### InternalServerResponseErrorData

**Inherits from**: BaseModel



### InternalServerResponseError

Internal Server Error - Unexpected server error

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: InternalServerResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | InternalServerResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



