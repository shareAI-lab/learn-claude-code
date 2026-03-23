# APIKeys
(*api_keys*)

## Overview

API key management endpoints

### Available Operations

* [list](#list) - List API keys
* [create](#create) - Create a new API key
* [update](#update) - Update an API key
* [delete](#delete) - Delete an API key
* [get](#get) - Get a single API key
* [get_current_key_metadata](#get_current_key_metadata) - Get current API key

## list

List all API keys for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

### Example Usage

<!-- UsageSnippet language="python" operationID="list" method="get" path="/keys" -->
```python
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.api_keys.list(include_disabled="false", offset="0")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                         | Type                                                                                                                                              | Required                                                                                                                                          | Description                                                                                                                                       | Example                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `http_referer`                                                                                                                                    | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app identifier should be your app's URL and is used as the primary identifier for rankings.<br/>This is used to track API usage per application.<br/> |                                                                                                                                                   |
| `x_title`                                                                                                                                         | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app display name allows you to customize how your app appears in OpenRouter's dashboard.<br/>                                                 |                                                                                                                                                   |
| `include_disabled`                                                                                                                                | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | Whether to include disabled API keys in the response                                                                                              | false                                                                                                                                             |
| `offset`                                                                                                                                          | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | Number of API keys to skip for pagination                                                                                                         | 0                                                                                                                                                 |
| `retries`                                                                                                                                         | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                  | :heavy_minus_sign:                                                                                                                                | Configuration to override the default retry behavior of the client.                                                                               |                                                                                                                                                   |

### Response

**[operations.ListResponse](../../operations/listresponse.md)**

### Errors

| Error Type                          | Status Code                         | Content Type                        |
| ----------------------------------- | ----------------------------------- | ----------------------------------- |
| errors.UnauthorizedResponseError    | 401                                 | application/json                    |
| errors.TooManyRequestsResponseError | 429                                 | application/json                    |
| errors.InternalServerResponseError  | 500                                 | application/json                    |
| errors.OpenRouterDefaultError       | 4XX, 5XX                            | \*/\*                               |

## create

Create a new API key for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

### Example Usage

<!-- UsageSnippet language="python" operationID="createKeys" method="post" path="/keys" -->
```python
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.api_keys.create(name="My New API Key")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                             | Type                                                                                                                                                                  | Required                                                                                                                                                              | Description                                                                                                                                                           | Example                                                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                                                                                                                                                | *str*                                                                                                                                                                 | :heavy_check_mark:                                                                                                                                                    | Name for the new API key                                                                                                                                              | My New API Key                                                                                                                                                        |
| `http_referer`                                                                                                                                                        | *Optional[str]*                                                                                                                                                       | :heavy_minus_sign:                                                                                                                                                    | The app identifier should be your app's URL and is used as the primary identifier for rankings.<br/>This is used to track API usage per application.<br/>             |                                                                                                                                                                       |
| `x_title`                                                                                                                                                             | *Optional[str]*                                                                                                                                                       | :heavy_minus_sign:                                                                                                                                                    | The app display name allows you to customize how your app appears in OpenRouter's dashboard.<br/>                                                                     |                                                                                                                                                                       |
| `limit`                                                                                                                                                               | *OptionalNullable[float]*                                                                                                                                             | :heavy_minus_sign:                                                                                                                                                    | Optional spending limit for the API key in USD                                                                                                                        | 50                                                                                                                                                                    |
| `limit_reset`                                                                                                                                                         | [OptionalNullable[operations.CreateKeysLimitReset]](../../operations/createkeyslimitreset.md)                                                                         | :heavy_minus_sign:                                                                                                                                                    | Type of limit reset for the API key (daily, weekly, monthly, or null for no reset). Resets happen automatically at midnight UTC, and weeks are Monday through Sunday. | monthly                                                                                                                                                               |
| `include_byok_in_limit`                                                                                                                                               | *Optional[bool]*                                                                                                                                                      | :heavy_minus_sign:                                                                                                                                                    | Whether to include BYOK usage in the limit                                                                                                                            | true                                                                                                                                                                  |
| `expires_at`                                                                                                                                                          | [date](https://docs.python.org/3/library/datetime.html#date-objects)                                                                                                  | :heavy_minus_sign:                                                                                                                                                    | Optional ISO 8601 UTC timestamp when the API key should expire. Must be UTC, other timezones will be rejected                                                         | 2027-12-31T23:59:59Z                                                                                                                                                  |
| `retries`                                                                                                                                                             | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                      | :heavy_minus_sign:                                                                                                                                                    | Configuration to override the default retry behavior of the client.                                                                                                   |                                                                                                                                                                       |

### Response

**[operations.CreateKeysResponse](../../operations/createkeysresponse.md)**

### Errors

| Error Type                          | Status Code                         | Content Type                        |
| ----------------------------------- | ----------------------------------- | ----------------------------------- |
| errors.BadRequestResponseError      | 400                                 | application/json                    |
| errors.UnauthorizedResponseError    | 401                                 | application/json                    |
| errors.TooManyRequestsResponseError | 429                                 | application/json                    |
| errors.InternalServerResponseError  | 500                                 | application/json                    |
| errors.OpenRouterDefaultError       | 4XX, 5XX                            | \*/\*                               |

## update

Update an existing API key. [Management key](/docs/guides/overview/auth/management-api-keys) required.

### Example Usage

<!-- UsageSnippet language="python" operationID="updateKeys" method="patch" path="/keys/{hash}" -->
```python
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.api_keys.update(hash="f01d52606dc8f0a8303a7b5cc3fa07109c2e346cec7c0a16b40de462992ce943")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                              | Type                                                                                                                                                                   | Required                                                                                                                                                               | Description                                                                                                                                                            | Example                                                                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hash`                                                                                                                                                                 | *str*                                                                                                                                                                  | :heavy_check_mark:                                                                                                                                                     | The hash identifier of the API key to update                                                                                                                           | f01d52606dc8f0a8303a7b5cc3fa07109c2e346cec7c0a16b40de462992ce943                                                                                                       |
| `http_referer`                                                                                                                                                         | *Optional[str]*                                                                                                                                                        | :heavy_minus_sign:                                                                                                                                                     | The app identifier should be your app's URL and is used as the primary identifier for rankings.<br/>This is used to track API usage per application.<br/>              |                                                                                                                                                                        |
| `x_title`                                                                                                                                                              | *Optional[str]*                                                                                                                                                        | :heavy_minus_sign:                                                                                                                                                     | The app display name allows you to customize how your app appears in OpenRouter's dashboard.<br/>                                                                      |                                                                                                                                                                        |
| `name`                                                                                                                                                                 | *Optional[str]*                                                                                                                                                        | :heavy_minus_sign:                                                                                                                                                     | New name for the API key                                                                                                                                               | Updated API Key Name                                                                                                                                                   |
| `disabled`                                                                                                                                                             | *Optional[bool]*                                                                                                                                                       | :heavy_minus_sign:                                                                                                                                                     | Whether to disable the API key                                                                                                                                         | false                                                                                                                                                                  |
| `limit`                                                                                                                                                                | *OptionalNullable[float]*                                                                                                                                              | :heavy_minus_sign:                                                                                                                                                     | New spending limit for the API key in USD                                                                                                                              | 75                                                                                                                                                                     |
| `limit_reset`                                                                                                                                                          | [OptionalNullable[operations.UpdateKeysLimitReset]](../../operations/updatekeyslimitreset.md)                                                                          | :heavy_minus_sign:                                                                                                                                                     | New limit reset type for the API key (daily, weekly, monthly, or null for no reset). Resets happen automatically at midnight UTC, and weeks are Monday through Sunday. | daily                                                                                                                                                                  |
| `include_byok_in_limit`                                                                                                                                                | *Optional[bool]*                                                                                                                                                       | :heavy_minus_sign:                                                                                                                                                     | Whether to include BYOK usage in the limit                                                                                                                             | true                                                                                                                                                                   |
| `retries`                                                                                                                                                              | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                       | :heavy_minus_sign:                                                                                                                                                     | Configuration to override the default retry behavior of the client.                                                                                                    |                                                                                                                                                                        |

### Response

**[operations.UpdateKeysResponse](../../operations/updatekeysresponse.md)**

### Errors

| Error Type                          | Status Code                         | Content Type                        |
| ----------------------------------- | ----------------------------------- | ----------------------------------- |
| errors.BadRequestResponseError      | 400                                 | application/json                    |
| errors.UnauthorizedResponseError    | 401                                 | application/json                    |
| errors.NotFoundResponseError        | 404                                 | application/json                    |
| errors.TooManyRequestsResponseError | 429                                 | application/json                    |
| errors.InternalServerResponseError  | 500                                 | application/json                    |
| errors.OpenRouterDefaultError       | 4XX, 5XX                            | \*/\*                               |

## delete

Delete an existing API key. [Management key](/docs/guides/overview/auth/management-api-keys) required.

### Example Usage

<!-- UsageSnippet language="python" operationID="deleteKeys" method="delete" path="/keys/{hash}" -->
```python
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.api_keys.delete(hash="f01d52606dc8f0a8303a7b5cc3fa07109c2e346cec7c0a16b40de462992ce943")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                         | Type                                                                                                                                              | Required                                                                                                                                          | Description                                                                                                                                       | Example                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hash`                                                                                                                                            | *str*                                                                                                                                             | :heavy_check_mark:                                                                                                                                | The hash identifier of the API key to delete                                                                                                      | f01d52606dc8f0a8303a7b5cc3fa07109c2e346cec7c0a16b40de462992ce943                                                                                  |
| `http_referer`                                                                                                                                    | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app identifier should be your app's URL and is used as the primary identifier for rankings.<br/>This is used to track API usage per application.<br/> |                                                                                                                                                   |
| `x_title`                                                                                                                                         | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app display name allows you to customize how your app appears in OpenRouter's dashboard.<br/>                                                 |                                                                                                                                                   |
| `retries`                                                                                                                                         | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                  | :heavy_minus_sign:                                                                                                                                | Configuration to override the default retry behavior of the client.                                                                               |                                                                                                                                                   |

### Response

**[operations.DeleteKeysResponse](../../operations/deletekeysresponse.md)**

### Errors

| Error Type                          | Status Code                         | Content Type                        |
| ----------------------------------- | ----------------------------------- | ----------------------------------- |
| errors.UnauthorizedResponseError    | 401                                 | application/json                    |
| errors.NotFoundResponseError        | 404                                 | application/json                    |
| errors.TooManyRequestsResponseError | 429                                 | application/json                    |
| errors.InternalServerResponseError  | 500                                 | application/json                    |
| errors.OpenRouterDefaultError       | 4XX, 5XX                            | \*/\*                               |

## get

Get a single API key by hash. [Management key](/docs/guides/overview/auth/management-api-keys) required.

### Example Usage

<!-- UsageSnippet language="python" operationID="getKey" method="get" path="/keys/{hash}" -->
```python
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.api_keys.get(hash="f01d52606dc8f0a8303a7b5cc3fa07109c2e346cec7c0a16b40de462992ce943")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                         | Type                                                                                                                                              | Required                                                                                                                                          | Description                                                                                                                                       | Example                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hash`                                                                                                                                            | *str*                                                                                                                                             | :heavy_check_mark:                                                                                                                                | The hash identifier of the API key to retrieve                                                                                                    | f01d52606dc8f0a8303a7b5cc3fa07109c2e346cec7c0a16b40de462992ce943                                                                                  |
| `http_referer`                                                                                                                                    | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app identifier should be your app's URL and is used as the primary identifier for rankings.<br/>This is used to track API usage per application.<br/> |                                                                                                                                                   |
| `x_title`                                                                                                                                         | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app display name allows you to customize how your app appears in OpenRouter's dashboard.<br/>                                                 |                                                                                                                                                   |
| `retries`                                                                                                                                         | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                  | :heavy_minus_sign:                                                                                                                                | Configuration to override the default retry behavior of the client.                                                                               |                                                                                                                                                   |

### Response

**[operations.GetKeyResponse](../../operations/getkeyresponse.md)**

### Errors

| Error Type                          | Status Code                         | Content Type                        |
| ----------------------------------- | ----------------------------------- | ----------------------------------- |
| errors.UnauthorizedResponseError    | 401                                 | application/json                    |
| errors.NotFoundResponseError        | 404                                 | application/json                    |
| errors.TooManyRequestsResponseError | 429                                 | application/json                    |
| errors.InternalServerResponseError  | 500                                 | application/json                    |
| errors.OpenRouterDefaultError       | 4XX, 5XX                            | \*/\*                               |

## get_current_key_metadata

Get information on the API key associated with the current authentication session

### Example Usage

<!-- UsageSnippet language="python" operationID="getCurrentKey" method="get" path="/key" -->
```python
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.api_keys.get_current_key_metadata()

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                         | Type                                                                                                                                              | Required                                                                                                                                          | Description                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `http_referer`                                                                                                                                    | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app identifier should be your app's URL and is used as the primary identifier for rankings.<br/>This is used to track API usage per application.<br/> |
| `x_title`                                                                                                                                         | *Optional[str]*                                                                                                                                   | :heavy_minus_sign:                                                                                                                                | The app display name allows you to customize how your app appears in OpenRouter's dashboard.<br/>                                                 |
| `retries`                                                                                                                                         | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                  | :heavy_minus_sign:                                                                                                                                | Configuration to override the default retry behavior of the client.                                                                               |

### Response

**[operations.GetCurrentKeyResponse](../../operations/getcurrentkeyresponse.md)**

### Errors

| Error Type                         | Status Code                        | Content Type                       |
| ---------------------------------- | ---------------------------------- | ---------------------------------- |
| errors.UnauthorizedResponseError   | 401                                | application/json                   |
| errors.InternalServerResponseError | 500                                | application/json                   |
| errors.OpenRouterDefaultError      | 4XX, 5XX                           | \*/\*                              |