# API Reference: forms.py

**Language**: Python

**Source**: `src/openrouter/utils/forms.py`

---

## Functions

### _populate_form(field_name: str, explode: bool, obj: Any, delimiter: str, form: Dict[str, List[str]])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field_name | str | - | - |
| explode | bool | - | - |
| obj | Any | - | - |
| delimiter | str | - | - |
| form | Dict[str, List[str]] | - | - |

**Returns**: (none)



### _extract_file_properties(file_obj: Any) → Tuple[str, Any, Any]

Extract file name, content, and content type from a file object.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| file_obj | Any | - | - |

**Returns**: `Tuple[str, Any, Any]`



### serialize_multipart_form(media_type: str, request: Any) → Tuple[str, Dict[str, Any], List[Tuple[str, Any]]]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| media_type | str | - | - |
| request | Any | - | - |

**Returns**: `Tuple[str, Dict[str, Any], List[Tuple[str, Any]]]`



### serialize_form_data(data: Any) → Dict[str, Any]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| data | Any | - | - |

**Returns**: `Dict[str, Any]`


