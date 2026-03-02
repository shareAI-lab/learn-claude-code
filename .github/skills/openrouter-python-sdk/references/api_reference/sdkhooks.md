# API Reference: sdkhooks.py

**Language**: Python

**Source**: `src/openrouter/_hooks/sdkhooks.py`

---

## Classes

### SDKHooks

**Inherits from**: Hooks

#### Methods

##### __init__(self) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `None`


##### register_sdk_init_hook(self, hook: SDKInitHook) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | SDKInitHook | - | - |

**Returns**: `None`


##### register_before_request_hook(self, hook: BeforeRequestHook) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | BeforeRequestHook | - | - |

**Returns**: `None`


##### register_after_success_hook(self, hook: AfterSuccessHook) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | AfterSuccessHook | - | - |

**Returns**: `None`


##### register_after_error_hook(self, hook: AfterErrorHook) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | AfterErrorHook | - | - |

**Returns**: `None`


##### sdk_init(self, config: SDKConfiguration) → SDKConfiguration

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| config | SDKConfiguration | - | - |

**Returns**: `SDKConfiguration`


##### before_request(self, hook_ctx: BeforeRequestContext, request: httpx.Request) → httpx.Request

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | BeforeRequestContext | - | - |
| request | httpx.Request | - | - |

**Returns**: `httpx.Request`


##### after_success(self, hook_ctx: AfterSuccessContext, response: httpx.Response) → httpx.Response

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | AfterSuccessContext | - | - |
| response | httpx.Response | - | - |

**Returns**: `httpx.Response`


##### after_error(self, hook_ctx: AfterErrorContext, response: Optional[httpx.Response], error: Optional[Exception]) → Tuple[Optional[httpx.Response], Optional[Exception]]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | AfterErrorContext | - | - |
| response | Optional[httpx.Response] | - | - |
| error | Optional[Exception] | - | - |

**Returns**: `Tuple[Optional[httpx.Response], Optional[Exception]]`



