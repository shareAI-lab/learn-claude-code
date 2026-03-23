# API Reference: basesdk.py

**Language**: Python

**Source**: `src/openrouter/basesdk.py`

---

## Classes

### BaseSDK

**Inherits from**: (none)

#### Methods

##### __init__(self, sdk_config: SDKConfiguration, parent_ref: Optional[object] = None) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| sdk_config | SDKConfiguration | - | - |
| parent_ref | Optional[object] | None | - |

**Returns**: `None`


##### _get_url(self, base_url, url_variables)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| base_url | None | - | - |
| url_variables | None | - | - |


##### _build_request_async(self, method, path, base_url, url_variables, request, request_body_required, request_has_path_params, request_has_query_params, user_agent_header, accept_header_value, _globals = None, security = None, timeout_ms: Optional[int] = None, get_serialized_body: Optional[Callable[[], Optional[SerializedRequestBody]]] = None, url_override: Optional[str] = None, http_headers: Optional[Mapping[str, str]] = None, allow_empty_value: Optional[List[str]] = None) → httpx.Request

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| method | None | - | - |
| path | None | - | - |
| base_url | None | - | - |
| url_variables | None | - | - |
| request | None | - | - |
| request_body_required | None | - | - |
| request_has_path_params | None | - | - |
| request_has_query_params | None | - | - |
| user_agent_header | None | - | - |
| accept_header_value | None | - | - |
| _globals | None | None | - |
| security | None | None | - |
| timeout_ms | Optional[int] | None | - |
| get_serialized_body | Optional[Callable[[], Optional[SerializedRequestBody]]] | None | - |
| url_override | Optional[str] | None | - |
| http_headers | Optional[Mapping[str, str]] | None | - |
| allow_empty_value | Optional[List[str]] | None | - |

**Returns**: `httpx.Request`


##### _build_request(self, method, path, base_url, url_variables, request, request_body_required, request_has_path_params, request_has_query_params, user_agent_header, accept_header_value, _globals = None, security = None, timeout_ms: Optional[int] = None, get_serialized_body: Optional[Callable[[], Optional[SerializedRequestBody]]] = None, url_override: Optional[str] = None, http_headers: Optional[Mapping[str, str]] = None, allow_empty_value: Optional[List[str]] = None) → httpx.Request

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| method | None | - | - |
| path | None | - | - |
| base_url | None | - | - |
| url_variables | None | - | - |
| request | None | - | - |
| request_body_required | None | - | - |
| request_has_path_params | None | - | - |
| request_has_query_params | None | - | - |
| user_agent_header | None | - | - |
| accept_header_value | None | - | - |
| _globals | None | None | - |
| security | None | None | - |
| timeout_ms | Optional[int] | None | - |
| get_serialized_body | Optional[Callable[[], Optional[SerializedRequestBody]]] | None | - |
| url_override | Optional[str] | None | - |
| http_headers | Optional[Mapping[str, str]] | None | - |
| allow_empty_value | Optional[List[str]] | None | - |

**Returns**: `httpx.Request`


##### _build_request_with_client(self, client, method, path, base_url, url_variables, request, request_body_required, request_has_path_params, request_has_query_params, user_agent_header, accept_header_value, _globals = None, security = None, timeout_ms: Optional[int] = None, get_serialized_body: Optional[Callable[[], Optional[SerializedRequestBody]]] = None, url_override: Optional[str] = None, http_headers: Optional[Mapping[str, str]] = None, allow_empty_value: Optional[List[str]] = None) → httpx.Request

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| client | None | - | - |
| method | None | - | - |
| path | None | - | - |
| base_url | None | - | - |
| url_variables | None | - | - |
| request | None | - | - |
| request_body_required | None | - | - |
| request_has_path_params | None | - | - |
| request_has_query_params | None | - | - |
| user_agent_header | None | - | - |
| accept_header_value | None | - | - |
| _globals | None | None | - |
| security | None | None | - |
| timeout_ms | Optional[int] | None | - |
| get_serialized_body | Optional[Callable[[], Optional[SerializedRequestBody]]] | None | - |
| url_override | Optional[str] | None | - |
| http_headers | Optional[Mapping[str, str]] | None | - |
| allow_empty_value | Optional[List[str]] | None | - |

**Returns**: `httpx.Request`


##### do_request(self, hook_ctx, request, error_status_codes, stream = False, retry_config: Optional[Tuple[RetryConfig, List[str]]] = None) → httpx.Response

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | None | - | - |
| request | None | - | - |
| error_status_codes | None | - | - |
| stream | None | False | - |
| retry_config | Optional[Tuple[RetryConfig, List[str]]] | None | - |

**Returns**: `httpx.Response`


##### do_request_async(self, hook_ctx, request, error_status_codes, stream = False, retry_config: Optional[Tuple[RetryConfig, List[str]]] = None) → httpx.Response

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| hook_ctx | None | - | - |
| request | None | - | - |
| error_status_codes | None | - | - |
| stream | None | False | - |
| retry_config | Optional[Tuple[RetryConfig, List[str]]] | None | - |

**Returns**: `httpx.Response`




## Functions

### do()

**Returns**: (none)



### do()

**Async function**

**Returns**: (none)


