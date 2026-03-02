# OpenRouter SDK (Beta)

The [OpenRouter SDK](https://openrouter.ai/docs/sdks/python) is a Python toolkit designed to help you build AI-powered features and solutions. Giving you easy access to over 300 models across providers in an easy and type-safe way.

To learn more about how to use the OpenRouter SDK, check out our [API Reference](https://openrouter.ai/docs/sdks/python/reference) and [Documentation](https://openrouter.ai/docs/sdks/python).

<!-- No Summary [summary] -->

<!-- No Table of Contents [toc] -->

<!-- Start SDK Installation [installation] -->
## SDK Installation

> [!NOTE]
> **Python version upgrade policy**
>
> Once a Python version reaches its [official end of life date](https://devguide.python.org/versions/), a 3-month grace period is provided for users to upgrade. Following this grace period, the minimum python version supported in the SDK will be updated.

The SDK can be installed with *uv*, *pip*, or *poetry* package managers.

### uv

*uv* is a fast Python package installer and resolver, designed as a drop-in replacement for pip and pip-tools. It's recommended for its speed and modern Python tooling capabilities.

```bash
uv add openrouter
```

### PIP

*PIP* is the default package installer for Python, enabling easy installation and management of packages from PyPI via the command line.

```bash
pip install openrouter
```

### Poetry

*Poetry* is a modern tool that simplifies dependency management and package publishing by using a single `pyproject.toml` file to handle project metadata and dependencies.

```bash
poetry add openrouter
```

### Shell and script usage with `uv`

You can use this SDK in a Python shell with [uv](https://docs.astral.sh/uv/) and the `uvx` command that comes with it like so:

```shell
uvx --from openrouter python
```

It's also possible to write a standalone Python script without needing to set up a whole project like so:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "openrouter",
# ]
# ///

from openrouter import OpenRouter

sdk = OpenRouter(
  # SDK arguments
)

# Rest of script here...
```

Once that is saved to a file, you can run it with `uv run script.py` where
`script.py` can be replaced with the actual file name.
<!-- End SDK Installation [installation] -->

<!-- Start Requirements [requirements] -->
## Requirements

This SDK requires Python 3.9 or higher. For Python version support policy, see the SDK Installation section above.
<!-- End Requirements [requirements] -->

<!-- Start IDE Support [idesupport] -->
## IDE Support

### PyCharm

Generally, the SDK will work well with most IDEs out of the box. However, when using PyCharm, you can enjoy much better integration with Pydantic by installing an additional plugin.

- [PyCharm Pydantic Plugin](https://docs.pydantic.dev/latest/integrations/pycharm/)
<!-- End IDE Support [idesupport] -->

<!-- No SDK Example Usage [usage] -->
## SDK Usage

```python
# Synchronous Example
from openrouter import OpenRouter
import os


with OpenRouter(
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.chat.send(messages=[
        {
            "role": "user",
            "content": "Hello, how are you?",
        },
    ], model="anthropic/claude-4.5-sonnet", provider={
        "zdr": True,
        "sort": "price",
    }, stream=True)

    for event in event_stream:
        # handle event
        print(event, flush=True)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from openrouter import OpenRouter
import os

async def main():

    async with OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    ) as open_router:

        res = await open_router.chat.send_async(messages=[
        {
            "role": "user",
            "content": "Hello, how are you?",
        },
    ], model="anthropic/claude-4.5-sonnet", provider={
        "zdr": True,
        "sort": "price",
    }, stream=True)

        async for event in event_stream:
            # handle event
            print(event, flush=True)

asyncio.run(main())
```

<!-- No Authentication [security] -->

<!-- No Available Resources and Operations [operations] -->

<!-- No Standalone functions [standalone-funcs] -->

<!-- No React hooks with TanStack Query [react-query] -->

<!-- No Server-sent event streaming [eventstream] -->

<!-- No Retries [retries] -->

<!-- No Error Handling [errors] -->

<!-- No Server Selection [server] -->

<!-- No Custom HTTP Client [http-client] -->

<!-- Start Resource Management [resource-management] -->
## Resource Management

The `OpenRouter` class implements the context manager protocol and registers a finalizer function to close the underlying sync and async HTTPX clients it uses under the hood. This will close HTTP connections, release memory and free up other resources held by the SDK. In short-lived Python programs and notebooks that make a few SDK method calls, resource management may not be a concern. However, in longer-lived programs, it is beneficial to create a single SDK instance via a [context manager][context-manager] and reuse it across the application.

[context-manager]: https://docs.python.org/3/reference/datamodel.html#context-managers

```python
from openrouter import OpenRouter
import os
def main():

    with OpenRouter(
        http_referer="<value>",
        x_title="<value>",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    ) as open_router:
        # Rest of application here...


# Or when using async:
async def amain():

    async with OpenRouter(
        http_referer="<value>",
        x_title="<value>",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    ) as open_router:
        # Rest of application here...
```
<!-- End Resource Management [resource-management] -->

<!-- Start Debugging [debug] -->
## Debugging

You can setup your SDK to emit debug logs for SDK requests and responses.

You can pass your own logger class directly into your SDK.
```python
from openrouter import OpenRouter
import logging

logging.basicConfig(level=logging.DEBUG)
s = OpenRouter(debug_logger=logging.getLogger("openrouter"))
```

You can also enable a default debug logger by setting an environment variable `OPENROUTER_DEBUG` to true.
<!-- End Debugging [debug] -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

# Development

## Running Tests

To run the test suite, you'll need to set up your environment with an OpenRouter API key.

### Local Development

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your OpenRouter API key:

   ```bash
   OPENROUTER_API_KEY=your_api_key_here
   ```

3. Run the tests:

   ```bash
   pytest
   ```

## Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version. 