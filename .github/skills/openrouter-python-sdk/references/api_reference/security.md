# API Reference: security.py

**Language**: Python

**Source**: `src/openrouter/utils/security.py`

---

## Functions

### get_security(security: Any) → Tuple[Dict[str, str], Dict[str, List[str]]]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| security | Any | - | - |

**Returns**: `Tuple[Dict[str, str], Dict[str, List[str]]]`



### get_security_from_env(security: Any, security_class: Any) → Optional[BaseModel]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| security | Any | - | - |
| security_class | Any | - | - |

**Returns**: `Optional[BaseModel]`



### _parse_security_option(headers: Dict[str, str], query_params: Dict[str, List[str]], option: Any)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers | Dict[str, str] | - | - |
| query_params | Dict[str, List[str]] | - | - |
| option | Any | - | - |

**Returns**: (none)



### _parse_security_scheme(headers: Dict[str, str], query_params: Dict[str, List[str]], scheme_metadata: SecurityMetadata, field_name: str, scheme: Any)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers | Dict[str, str] | - | - |
| query_params | Dict[str, List[str]] | - | - |
| scheme_metadata | SecurityMetadata | - | - |
| field_name | str | - | - |
| scheme | Any | - | - |

**Returns**: (none)



### _parse_security_scheme_value(headers: Dict[str, str], query_params: Dict[str, List[str]], scheme_metadata: SecurityMetadata, security_metadata: SecurityMetadata, field_name: str, value: Any)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers | Dict[str, str] | - | - |
| query_params | Dict[str, List[str]] | - | - |
| scheme_metadata | SecurityMetadata | - | - |
| security_metadata | SecurityMetadata | - | - |
| field_name | str | - | - |
| value | Any | - | - |

**Returns**: (none)



### _apply_bearer(token: str) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| token | str | - | - |

**Returns**: `str`



### _parse_basic_auth_scheme(headers: Dict[str, str], scheme: Any)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| headers | Dict[str, str] | - | - |
| scheme | Any | - | - |

**Returns**: (none)


