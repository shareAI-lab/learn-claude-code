# CompletionTokensDetails

Detailed completion token usage


## Fields

| Field                        | Type                         | Required                     | Description                  |
| ---------------------------- | ---------------------------- | ---------------------------- | ---------------------------- |
| `reasoning_tokens`           | *OptionalNullable[float]*    | :heavy_minus_sign:           | Tokens used for reasoning    |
| `audio_tokens`               | *OptionalNullable[float]*    | :heavy_minus_sign:           | Tokens used for audio output |
| `accepted_prediction_tokens` | *OptionalNullable[float]*    | :heavy_minus_sign:           | Accepted prediction tokens   |
| `rejected_prediction_tokens` | *OptionalNullable[float]*    | :heavy_minus_sign:           | Rejected prediction tokens   |