# API Reference: check_types.py

**Language**: Python

**Source**: `scripts/check_types.py`

---

## Functions

### compute_hash(model_ids: list[str]) → str

Compute SHA-256 hash of sorted model IDs (first 16 chars).

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| model_ids | list[str] | - | - |

**Returns**: `str`



### extract_hash(content: str) → str | None

Extract MODEL_HASH from types file content.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| content | str | - | - |

**Returns**: `str | None`



### fetch_models() → list[str]

Fetch model IDs from OpenRouter API.

**Returns**: `list[str]`



### main() → None

**Returns**: `None`


