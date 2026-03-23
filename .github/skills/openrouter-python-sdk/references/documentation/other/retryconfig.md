# RetryConfig

Allows customizing the default retry configuration. Only usable with methods that mention they support retries.

## Fields

| Name                      | Type                                | Description                             | Example   |
| ------------------------- | ----------------------------------- | --------------------------------------- | --------- |
| `strategy`                | `*str*`                             | The retry strategy to use.              | `backoff` |
| `backoff`                 | [BackoffStrategy](#backoffstrategy) | Configuration for the backoff strategy. |           |
| `retry_connection_errors` | `*bool*`                            | Whether to retry on connection errors.  | `true`    |

## BackoffStrategy

The backoff strategy allows retrying a request with an exponential backoff between each retry.

### Fields

| Name               | Type      | Description                               | Example  |
| ------------------ | --------- | ----------------------------------------- | -------- |
| `initial_interval` | `*int*`   | The initial interval in milliseconds.     | `500`    |
| `max_interval`     | `*int*`   | The maximum interval in milliseconds.     | `60000`  |
| `exponent`         | `*float*` | The exponent to use for the backoff.      | `1.5`    |
| `max_elapsed_time` | `*int*`   | The maximum elapsed time in milliseconds. | `300000` |