# API Reference: openroutererror.py

**Language**: Python

**Source**: `src/openrouter/errors/openroutererror.py`

---

## Classes

### OpenRouterError

The base class for all HTTP error responses.

**Inherits from**: Exception

#### Methods

##### __init__(self, message: str, raw_response: httpx.Response, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| message | str | - | - |
| raw_response | httpx.Response | - | - |
| body | Optional[str] | None | - |


##### __str__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |



