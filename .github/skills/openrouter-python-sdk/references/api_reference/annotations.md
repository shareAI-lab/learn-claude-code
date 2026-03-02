# API Reference: annotations.py

**Language**: Python

**Source**: `src/openrouter/utils/annotations.py`

---

## Functions

### get_discriminator(model: Any, fieldname: str, key: str) → str

Recursively search for the discriminator attribute in a model.

Args:
    model (Any): The model to search within.
    fieldname (str): The name of the field to search for.
    key (str): The key to search for in dictionaries.

Returns:
    str: The name of the discriminator attribute.

Raises:
    ValueError: If the discriminator attribute is not found.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| model | Any | - | - |
| fieldname | str | - | - |
| key | str | - | - |

**Returns**: `str`



### get_field_discriminator(field: Any) → Optional[str]

Search for the discriminator attribute in a given field.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field | Any | - | - |

**Returns**: `Optional[str]`



### search_nested_discriminator(obj: Any) → Optional[str]

Recursively search for discriminator in nested structures.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| obj | Any | - | - |

**Returns**: `Optional[str]`


