# API Reference: badrequestresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/badrequestresponse_error.py`

---

## Classes

### BadRequestResponseErrorData

**Inherits from**: BaseModel



### BadRequestResponseError

Bad Request - Invalid request parameters or malformed input

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: BadRequestResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | BadRequestResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



