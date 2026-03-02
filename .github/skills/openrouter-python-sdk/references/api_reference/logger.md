# API Reference: logger.py

**Language**: Python

**Source**: `src/openrouter/utils/logger.py`

---

## Classes

### Logger

**Inherits from**: Protocol

#### Methods

##### debug(self, msg: str) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| msg | str | - | - |

**Returns**: `None`




### NoOpLogger

**Inherits from**: (none)

#### Methods

##### debug(self, msg: str) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| msg | str | - | - |

**Returns**: `None`




## Functions

### get_body_content(req: httpx.Request) → str

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| req | httpx.Request | - | - |

**Returns**: `str`



### get_default_logger() → Logger

**Returns**: `Logger`


