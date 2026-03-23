# API Reference: queryparams.py

**Language**: Python

**Source**: `src/openrouter/utils/queryparams.py`

---

## Functions

### get_query_params(query_params: Any, gbls: Optional[Any] = None, allow_empty_value: Optional[List[str]] = None) → Dict[str, List[str]]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| query_params | Any | - | - |
| gbls | Optional[Any] | None | - |
| allow_empty_value | Optional[List[str]] | None | - |

**Returns**: `Dict[str, List[str]]`



### _populate_query_params(query_params: Any, gbls: Any, query_param_values: Dict[str, List[str]], skip_fields: List[str], allow_empty_value: Optional[List[str]] = None) → List[str]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| query_params | Any | - | - |
| gbls | Any | - | - |
| query_param_values | Dict[str, List[str]] | - | - |
| skip_fields | List[str] | - | - |
| allow_empty_value | Optional[List[str]] | None | - |

**Returns**: `List[str]`



### _populate_deep_object_query_params(field_name: str, obj: Any, params: Dict[str, List[str]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field_name | str | - | - |
| obj | Any | - | - |
| params | Dict[str, List[str]] | - | - |

**Returns**: (none)



### _populate_deep_object_query_params_basemodel(prior_params_key: str, obj: Any, params: Dict[str, List[str]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| prior_params_key | str | - | - |
| obj | Any | - | - |
| params | Dict[str, List[str]] | - | - |

**Returns**: (none)



### _populate_deep_object_query_params_dict(prior_params_key: str, value: Dict, params: Dict[str, List[str]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| prior_params_key | str | - | - |
| value | Dict | - | - |
| params | Dict[str, List[str]] | - | - |

**Returns**: (none)



### _populate_deep_object_query_params_list(params_key: str, value: List, params: Dict[str, List[str]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| params_key | str | - | - |
| value | List | - | - |
| params | Dict[str, List[str]] | - | - |

**Returns**: (none)



### _populate_delimited_query_params(metadata: QueryParamMetadata, field_name: str, obj: Any, delimiter: str, query_param_values: Dict[str, List[str]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| metadata | QueryParamMetadata | - | - |
| field_name | str | - | - |
| obj | Any | - | - |
| delimiter | str | - | - |
| query_param_values | Dict[str, List[str]] | - | - |

**Returns**: (none)


