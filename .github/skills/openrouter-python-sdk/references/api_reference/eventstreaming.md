# API Reference: eventstreaming.py

**Language**: Python

**Source**: `src/openrouter/utils/eventstreaming.py`

---

## Classes

### EventStream

**Inherits from**: (none)

#### Methods

##### __init__(self, response: httpx.Response, decoder: Callable[[str], T], sentinel: Optional[str] = None, client_ref: Optional[object] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| response | httpx.Response | - | - |
| decoder | Callable[[str], T] | - | - |
| sentinel | Optional[str] | None | - |
| client_ref | Optional[object] | None | - |


##### __iter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __next__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __enter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __exit__(self, exc_type, exc_val, exc_tb)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| exc_type | None | - | - |
| exc_val | None | - | - |
| exc_tb | None | - | - |




### EventStreamAsync

**Inherits from**: (none)

#### Methods

##### __init__(self, response: httpx.Response, decoder: Callable[[str], T], sentinel: Optional[str] = None, client_ref: Optional[object] = None)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| response | httpx.Response | - | - |
| decoder | Callable[[str], T] | - | - |
| sentinel | Optional[str] | None | - |
| client_ref | Optional[object] | None | - |


##### __aiter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __anext__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __aenter__(self)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |


##### __aexit__(self, exc_type, exc_val, exc_tb)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| exc_type | None | - | - |
| exc_val | None | - | - |
| exc_tb | None | - | - |




### ServerEvent

**Inherits from**: (none)



## Functions

### stream_events_async(response: httpx.Response, decoder: Callable[[str], T], sentinel: Optional[str] = None) → AsyncGenerator[T, None]

**Async function**

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| response | httpx.Response | - | - |
| decoder | Callable[[str], T] | - | - |
| sentinel | Optional[str] | None | - |

**Returns**: `AsyncGenerator[T, None]`



### stream_events(response: httpx.Response, decoder: Callable[[str], T], sentinel: Optional[str] = None) → Generator[T, None, None]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| response | httpx.Response | - | - |
| decoder | Callable[[str], T] | - | - |
| sentinel | Optional[str] | None | - |

**Returns**: `Generator[T, None, None]`



### _parse_event(raw: bytearray, decoder: Callable[[str], T], sentinel: Optional[str] = None) → Tuple[Optional[T], bool]

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| raw | bytearray | - | - |
| decoder | Callable[[str], T] | - | - |
| sentinel | Optional[str] | None | - |

**Returns**: `Tuple[Optional[T], bool]`



### _peek_sequence(position: int, buffer: bytearray, sequence: bytes)

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| position | int | - | - |
| buffer | bytearray | - | - |
| sequence | bytes | - | - |

**Returns**: (none)


