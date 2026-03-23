# API Reference: datetimes.py

**Language**: Python

**Source**: `src/openrouter/utils/datetimes.py`

---

## Functions

### parse_datetime(datetime_string: str) → datetime

Convert a RFC 3339 / ISO 8601 formatted string into a datetime object.
Python versions 3.11 and later support parsing RFC 3339 directly with
datetime.fromisoformat(), but for earlier versions, this function
encapsulates the necessary extra logic.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| datetime_string | str | - | - |

**Returns**: `datetime`


