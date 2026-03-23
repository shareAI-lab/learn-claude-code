<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from openrouter import OpenRouter
import os


with OpenRouter(
    http_referer="<value>",
    x_title="<value>",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
) as open_router:

    res = open_router.beta.responses.send(service_tier="auto", stream=False)

    with res as event_stream:
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
        http_referer="<value>",
        x_title="<value>",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    ) as open_router:

        res = await open_router.beta.responses.send_async(service_tier="auto", stream=False)

        async with res as event_stream:
            async for event in event_stream:
                # handle event
                print(event, flush=True)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->