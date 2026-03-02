# API Reference: providerpreferences.py

**Language**: Python

**Source**: `src/openrouter/components/providerpreferences.py`

---

## Classes

### ProviderPreferencesProviderSortConfigTypedDict

**Inherits from**: TypedDict



### ProviderPreferencesProviderSortConfig

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |




### ProviderPreferencesMaxPriceTypedDict

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.

**Inherits from**: TypedDict



### ProviderPreferencesMaxPrice

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.

**Inherits from**: BaseModel



### ProviderPreferencesTypedDict

Provider routing preferences for the request.

**Inherits from**: TypedDict



### ProviderPreferences

Provider routing preferences for the request.

**Inherits from**: BaseModel

#### Methods

##### serialize_model(self, handler)

**Decorators**: `@model_serializer(mode='wrap')`

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| handler | None | - | - |



