# API Reference: types.py

**Language**: Python

**Source**: `src/openrouter/_hooks/types.py`

---

## Classes

### HookContext

**Inherits from**: (none)

#### Methods

##### __init__(self, config: SDKConfiguration, base_url: str, operation_id: str, oauth2_scopes: Optional[List[str]], security_source: Optional[Union[Any, Callable[[], Any]]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| config | SDKConfiguration | - | - |
| base_url | str | - | - |
| operation_id | str | - | - |
| oauth2_scopes | Optional[List[str]] | - | - |
| security_source | Optional[Union[Any, Callable[[], Any]]] | - | - |




### BeforeRequestContext

**Inherits from**: HookContext

#### Methods

##### __init__(self, hook_ctx: HookContext)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | HookContext | - | - |




### AfterSuccessContext

**Inherits from**: HookContext

#### Methods

##### __init__(self, hook_ctx: HookContext)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | HookContext | - | - |




### AfterErrorContext

**Inherits from**: HookContext

#### Methods

##### __init__(self, hook_ctx: HookContext)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | HookContext | - | - |




### SDKInitHook

**Inherits from**: ABC

#### Methods

##### sdk_init(self, config: SDKConfiguration) → SDKConfiguration

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| config | SDKConfiguration | - | - |

**Returns**: `SDKConfiguration`




### BeforeRequestHook

**Inherits from**: ABC

#### Methods

##### before_request(self, hook_ctx: BeforeRequestContext, request: httpx.Request) → Union[httpx.Request, Exception]

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | BeforeRequestContext | - | - |
| request | httpx.Request | - | - |

**Returns**: `Union[httpx.Request, Exception]`




### AfterSuccessHook

**Inherits from**: ABC

#### Methods

##### after_success(self, hook_ctx: AfterSuccessContext, response: httpx.Response) → Union[httpx.Response, Exception]

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | AfterSuccessContext | - | - |
| response | httpx.Response | - | - |

**Returns**: `Union[httpx.Response, Exception]`




### AfterErrorHook

**Inherits from**: ABC

#### Methods

##### after_error(self, hook_ctx: AfterErrorContext, response: Optional[httpx.Response], error: Optional[Exception]) → Union[Tuple[Optional[httpx.Response], Optional[Exception]], Exception]

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | AfterErrorContext | - | - |
| response | Optional[httpx.Response] | - | - |
| error | Optional[Exception] | - | - |

**Returns**: `Union[Tuple[Optional[httpx.Response], Optional[Exception]], Exception]`




### Hooks

**Inherits from**: ABC

#### Methods

##### register_sdk_init_hook(self, hook: SDKInitHook)

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | SDKInitHook | - | - |


##### register_before_request_hook(self, hook: BeforeRequestHook)

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | BeforeRequestHook | - | - |


##### register_after_success_hook(self, hook: AfterSuccessHook)

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | AfterSuccessHook | - | - |


##### register_after_error_hook(self, hook: AfterErrorHook)

**Decorators**: `@abstractmethod`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook | AfterErrorHook | - | - |



