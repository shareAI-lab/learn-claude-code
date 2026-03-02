# API Reference: getcurrentkey.py

**Language**: Python

**Source**: `src/openrouter/operations/getcurrentkey.py`

---

## Classes

### GetCurrentKeyGlobalsTypedDict

**Inherits from**: TypedDict



### GetCurrentKeyGlobals

**Inherits from**: BaseModel



### GetCurrentKeyRequestTypedDict

**Inherits from**: TypedDict



### GetCurrentKeyRequest

**Inherits from**: BaseModel



### RateLimitTypedDict

Legacy rate limit information about a key. Will always return -1.

**Inherits from**: TypedDict



### RateLimit

Legacy rate limit information about a key. Will always return -1.

**Inherits from**: BaseModel



### GetCurrentKeyDataTypedDict

Current API key information

**Inherits from**: TypedDict



### GetCurrentKeyData

Current API key information

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### GetCurrentKeyResponseTypedDict

API key details

**Inherits from**: TypedDict



### GetCurrentKeyResponse

API key details

**Inherits from**: BaseModel


