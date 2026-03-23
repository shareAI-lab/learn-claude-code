# API Reference: retries.py

**Language**: Python

**Source**: `src/openrouter/utils/retries.py`

---

## Classes

### BackoffStrategy

**Inherits from**: (none)

#### Methods

##### __init__(self, initial_interval: int, max_interval: int, exponent: float, max_elapsed_time: int)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| initial_interval | int | - | - |
| max_interval | int | - | - |
| exponent | float | - | - |
| max_elapsed_time | int | - | - |




### RetryConfig

**Inherits from**: (none)

#### Methods

##### __init__(self, strategy: str, backoff: BackoffStrategy, retry_connection_errors: bool)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| strategy | str | - | - |
| backoff | BackoffStrategy | - | - |
| retry_connection_errors | bool | - | - |




### Retries

**Inherits from**: (none)

#### Methods

##### __init__(self, config: RetryConfig, status_codes: List[str])

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| config | RetryConfig | - | - |
| status_codes | List[str] | - | - |




### TemporaryError

**Inherits from**: Exception

#### Methods

##### __init__(self, response: httpx.Response)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| response | httpx.Response | - | - |




### PermanentError

**Inherits from**: Exception

#### Methods

##### __init__(self, inner: Exception)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| inner | Exception | - | - |




## Functions

### _parse_retry_after_header(response: httpx.Response) → Optional[int]

Parse Retry-After header from response.

Returns:
    Retry interval in milliseconds, or None if header is missing or invalid.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| response | httpx.Response | - | - |

**Returns**: `Optional[int]`



### _get_sleep_interval(exception: Exception, initial_interval: int, max_interval: int, exponent: float, retries: int) → float

Get sleep interval for retry with exponential backoff.

Args:
    exception: The exception that triggered the retry.
    initial_interval: Initial retry interval in milliseconds.
    max_interval: Maximum retry interval in milliseconds.
    exponent: Base for exponential backoff calculation.
    retries: Current retry attempt count.

Returns:
    Sleep interval in seconds.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| exception | Exception | - | - |
| initial_interval | int | - | - |
| max_interval | int | - | - |
| exponent | float | - | - |
| retries | int | - | - |

**Returns**: `float`



### retry(func, retries: Retries)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| func | None | - | - |
| retries | Retries | - | - |

**Returns**: (none)



### retry_async(func, retries: Retries)

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| func | None | - | - |
| retries | Retries | - | - |

**Returns**: (none)



### retry_with_backoff(func, initial_interval = 500, max_interval = 60000, exponent = 1.5, max_elapsed_time = 3600000)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| func | None | - | - |
| initial_interval | None | 500 | - |
| max_interval | None | 60000 | - |
| exponent | None | 1.5 | - |
| max_elapsed_time | None | 3600000 | - |

**Returns**: (none)



### retry_with_backoff_async(func, initial_interval = 500, max_interval = 60000, exponent = 1.5, max_elapsed_time = 3600000)

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| func | None | - | - |
| initial_interval | None | 500 | - |
| max_interval | None | 60000 | - |
| exponent | None | 1.5 | - |
| max_elapsed_time | None | 3600000 | - |

**Returns**: (none)



### do_request() → httpx.Response

**Returns**: `httpx.Response`



### do_request() → httpx.Response

**Async function**

**Returns**: `httpx.Response`


