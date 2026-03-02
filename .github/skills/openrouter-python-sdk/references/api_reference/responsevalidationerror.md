# API Reference: responsevalidationerror.py

**Language**: Python

**Source**: `src/openrouter/errors/responsevalidationerror.py`

---

## Classes

### ResponseValidationError

Error raised when there is a type mismatch between the response data and the expected Pydantic model.

**Inherits from**: OpenRouterError

#### Methods

##### __init__(self, message: str, raw_response: httpx.Response, cause: Exception, body: Optional[str] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| message | str | - | - |
| raw_response | httpx.Response | - | - |
| cause | Exception | - | - |
| body | Optional[str] | None | - |


##### cause(self)

Normally the Pydantic ValidationError

**Decorators**: `@property`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |



