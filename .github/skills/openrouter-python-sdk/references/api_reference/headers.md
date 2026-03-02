# API Reference: headers.py

**Language**: Python

**Source**: `src/openrouter/utils/headers.py`

---

## Functions

### get_headers(headers_params: Any, gbls: Optional[Any] = None) → Dict[str, str]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers_params | Any | - | - |
| gbls | Optional[Any] | None | - |

**Returns**: `Dict[str, str]`



### _populate_headers(headers_params: Any, gbls: Any, header_values: Dict[str, str], skip_fields: List[str]) → List[str]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers_params | Any | - | - |
| gbls | Any | - | - |
| header_values | Dict[str, str] | - | - |
| skip_fields | List[str] | - | - |

**Returns**: `List[str]`



### _serialize_header(explode: bool, obj: Any) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| explode | bool | - | - |
| obj | Any | - | - |

**Returns**: `str`



### get_response_headers(headers: Headers) → Dict[str, List[str]]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers | Headers | - | - |

**Returns**: `Dict[str, List[str]]`


