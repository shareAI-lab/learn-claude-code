# API Reference: serializers.py

**Language**: Python

**Source**: `src/openrouter/utils/serializers.py`

---

## Functions

### serialize_decimal(as_str: bool)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| as_str | bool | - | - |

**Returns**: (none)



### validate_decimal(d)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| d | None | - | - |

**Returns**: (none)



### serialize_float(as_str: bool)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| as_str | bool | - | - |

**Returns**: (none)



### validate_float(f)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| f | None | - | - |

**Returns**: (none)



### serialize_int(as_str: bool)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| as_str | bool | - | - |

**Returns**: (none)



### validate_int(b)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| b | None | - | - |

**Returns**: (none)



### validate_open_enum(is_int: bool)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| is_int | bool | - | - |

**Returns**: (none)



### validate_const(v)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| v | None | - | - |

**Returns**: (none)



### unmarshal_json(raw, typ: Any) → Any

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| raw | None | - | - |
| typ | Any | - | - |

**Returns**: `Any`



### unmarshal(val, typ: Any) → Any

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| val | None | - | - |
| typ | Any | - | - |

**Returns**: `Any`



### marshal_json(val, typ)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| val | None | - | - |
| typ | None | - | - |

**Returns**: (none)



### is_nullable(field)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field | None | - | - |

**Returns**: (none)



### is_union(obj: object) → bool

Returns True if the given object is a typing.Union or typing_extensions.Union.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| obj | object | - | - |

**Returns**: `bool`



### stream_to_text(stream: httpx.Response) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| stream | httpx.Response | - | - |

**Returns**: `str`



### stream_to_text_async(stream: httpx.Response) → str

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| stream | httpx.Response | - | - |

**Returns**: `str`



### stream_to_bytes(stream: httpx.Response) → bytes

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| stream | httpx.Response | - | - |

**Returns**: `bytes`



### stream_to_bytes_async(stream: httpx.Response) → bytes

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| stream | httpx.Response | - | - |

**Returns**: `bytes`



### get_pydantic_model(data: Any, typ: Any) → Any

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| data | Any | - | - |
| typ | Any | - | - |

**Returns**: `Any`



### _contains_pydantic_model(data: Any) → bool

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| data | Any | - | - |

**Returns**: `bool`



### _get_typing_objects_by_name_of(name: str) → Tuple[Any, ...]

Get typing objects by name from typing and typing_extensions.
Reference: https://typing-extensions.readthedocs.io/en/latest/#runtime-use-of-types

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| name | str | - | - |

**Returns**: `Tuple[Any, ...]`



### serialize(d)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| d | None | - | - |

**Returns**: (none)



### serialize(f)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| f | None | - | - |

**Returns**: (none)



### serialize(i)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| i | None | - | - |

**Returns**: (none)



### validate(e)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| e | None | - | - |

**Returns**: (none)



### validate(c)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| c | None | - | - |

**Returns**: (none)


