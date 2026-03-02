# API Reference: values.py

**Language**: Python

**Source**: `src/openrouter/utils/values.py`

---

## Functions

### match_content_type(content_type: str, pattern: str) → bool

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| content_type | str | - | - |
| pattern | str | - | - |

**Returns**: `bool`



### match_status_codes(status_codes: List[str], status_code: int) → bool

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| status_codes | List[str] | - | - |
| status_code | int | - | - |

**Returns**: `bool`



### cast_partial(typ)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| typ | None | - | - |

**Returns**: (none)



### get_global_from_env(value: Optional[T], env_key: str, type_cast: Callable[[str], T]) → Optional[T]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| value | Optional[T] | - | - |
| env_key | str | - | - |
| type_cast | Callable[[str], T] | - | - |

**Returns**: `Optional[T]`



### match_response(response: Response, code: Union[str, List[str]], content_type: str) → bool

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| response | Response | - | - |
| code | Union[str, List[str]] | - | - |
| content_type | str | - | - |

**Returns**: `bool`



### _populate_from_globals(param_name: str, value: Any, param_metadata_type: type, gbls: Any) → Tuple[Any, bool]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| param_name | str | - | - |
| value | Any | - | - |
| param_metadata_type | type | - | - |
| gbls | Any | - | - |

**Returns**: `Tuple[Any, bool]`



### _val_to_string(val) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| val | None | - | - |

**Returns**: `str`



### _get_serialized_params(metadata: ParamMetadata, field_name: str, obj: Any, typ: type) → Dict[str, str]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| metadata | ParamMetadata | - | - |
| field_name | str | - | - |
| obj | Any | - | - |
| typ | type | - | - |

**Returns**: `Dict[str, str]`



### _is_set(value: Any) → bool

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| value | Any | - | - |

**Returns**: `bool`


