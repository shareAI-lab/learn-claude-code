# API Reference: metadata.py

**Language**: Python

**Source**: `src/openrouter/utils/metadata.py`

---

## Classes

### SecurityMetadata

**Inherits from**: (none)

#### Methods

##### get_field_name(self, default: str) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| default | str | - | - |

**Returns**: `str`




### ParamMetadata

**Inherits from**: (none)



### PathParamMetadata

**Inherits from**: ParamMetadata



### QueryParamMetadata

**Inherits from**: ParamMetadata



### HeaderMetadata

**Inherits from**: ParamMetadata



### RequestMetadata

**Inherits from**: (none)



### MultipartFormMetadata

**Inherits from**: (none)



### FormMetadata

**Inherits from**: (none)



### FieldMetadata

**Inherits from**: (none)

#### Methods

##### __init__(self, security: Optional[SecurityMetadata] = None, path: Optional[Union[PathParamMetadata, bool]] = None, query: Optional[Union[QueryParamMetadata, bool]] = None, header: Optional[Union[HeaderMetadata, bool]] = None, request: Optional[Union[RequestMetadata, bool]] = None, form: Optional[Union[FormMetadata, bool]] = None, multipart: Optional[Union[MultipartFormMetadata, bool]] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| security | Optional[SecurityMetadata] | None | - |
| path | Optional[Union[PathParamMetadata, bool]] | None | - |
| query | Optional[Union[QueryParamMetadata, bool]] | None | - |
| header | Optional[Union[HeaderMetadata, bool]] | None | - |
| request | Optional[Union[RequestMetadata, bool]] | None | - |
| form | Optional[Union[FormMetadata, bool]] | None | - |
| multipart | Optional[Union[MultipartFormMetadata, bool]] | None | - |




## Functions

### find_field_metadata(field_info: FieldInfo, metadata_type: Type[T]) → Optional[T]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field_info | FieldInfo | - | - |
| metadata_type | Type[T] | - | - |

**Returns**: `Optional[T]`



### find_metadata(field_info: FieldInfo, metadata_type: Type[T]) → Optional[T]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| field_info | FieldInfo | - | - |
| metadata_type | Type[T] | - | - |

**Returns**: `Optional[T]`


