# OpenResponsesRequestMaxPrice

The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion.


## Fields

| Field                           | Type                            | Required                        | Description                     | Example                         |
| ------------------------------- | ------------------------------- | ------------------------------- | ------------------------------- | ------------------------------- |
| `prompt`                        | *Optional[str]*                 | :heavy_minus_sign:              | Price per million prompt tokens | 1000                            |
| `completion`                    | *Optional[str]*                 | :heavy_minus_sign:              | N/A                             | 1000                            |
| `image`                         | *Optional[str]*                 | :heavy_minus_sign:              | N/A                             | 1000                            |
| `audio`                         | *Optional[str]*                 | :heavy_minus_sign:              | N/A                             | 1000                            |
| `request`                       | *Optional[str]*                 | :heavy_minus_sign:              | N/A                             | 1000                            |