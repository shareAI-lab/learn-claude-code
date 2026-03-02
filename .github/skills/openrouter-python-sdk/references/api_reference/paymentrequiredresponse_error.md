# API Reference: paymentrequiredresponse_error.py

**Language**: Python

**Source**: `src/openrouter/errors/paymentrequiredresponse_error.py`

---

## Classes

### PaymentRequiredResponseErrorData

**Inherits from**: BaseModel



### PaymentRequiredResponseError

Payment Required - Insufficient credits or quota to complete request

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, data: PaymentRequiredResponseErrorData, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| data | PaymentRequiredResponseErrorData | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |



