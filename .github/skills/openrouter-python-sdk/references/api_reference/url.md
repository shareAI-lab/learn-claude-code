# API Reference: url.py

**Language**: Python

**Source**: `src/openrouter/utils/url.py`

---

## Functions

### generate_url(server_url: str, path: str, path_params: Any, gbls: Optional[Any] = None) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| server_url | str | - | - |
| path | str | - | - |
| path_params | Any | - | - |
| gbls | Optional[Any] | None | - |

**Returns**: `str`



### _populate_path_params(path_params: Any, gbls: Any, path_param_values: Dict[str, str], skip_fields: List[str]) → List[str]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| path_params | Any | - | - |
| gbls | Any | - | - |
| path_param_values | Dict[str, str] | - | - |
| skip_fields | List[str] | - | - |

**Returns**: `List[str]`



### is_optional(field)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field | None | - | - |

**Returns**: (none)



### template_url(url_with_params: str, params: Dict[str, str]) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| url_with_params | str | - | - |
| params | Dict[str, str] | - | - |

**Returns**: `str`



### remove_suffix(input_string, suffix)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| input_string | None | - | - |
| suffix | None | - | - |

**Returns**: (none)


