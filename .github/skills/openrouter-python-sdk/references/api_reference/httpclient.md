# API Reference: httpclient.py

**Language**: Python

**Source**: `src/openrouter/httpclient.py`

---

## Classes

### HttpClient

**Inherits from**: Protocol

#### Methods

##### send(self, request: httpx.Request) → httpx.Response

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| request | httpx.Request | - | - |

**Returns**: `httpx.Response`


##### build_request(self, method: str, url: httpx._types.URLTypes) → httpx.Request

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| method | str | - | - |
| url | httpx._types.URLTypes | - | - |

**Returns**: `httpx.Request`


##### close(self) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `None`




### AsyncHttpClient

**Inherits from**: Protocol

#### Methods

##### send(self, request: httpx.Request) → httpx.Response

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| request | httpx.Request | - | - |

**Returns**: `httpx.Response`


##### build_request(self, method: str, url: httpx._types.URLTypes) → httpx.Request

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |
| method | str | - | - |
| url | httpx._types.URLTypes | - | - |

**Returns**: `httpx.Request`


##### aclose(self) → None

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `None`




### ClientOwner

**Inherits from**: Protocol



## Functions

### close_clients(owner: ClientOwner, sync_client: Union[HttpClient, None], sync_client_supplied: bool, async_client: Union[AsyncHttpClient, None], async_client_supplied: bool) → None

A finalizer function that is meant to be used with weakref.finalize to close
httpx clients used by an SDK so that underlying resources can be garbage
collected.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| owner | ClientOwner | - | - |
| sync_client | Union[HttpClient, None] | - | - |
| sync_client_supplied | bool | - | - |
| async_client | Union[AsyncHttpClient, None] | - | - |
| async_client_supplied | bool | - | - |

**Returns**: `None`


