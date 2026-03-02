# PercentileThroughputCutoffs

Percentile-based throughput cutoffs. All specified cutoffs must be met for an endpoint to be preferred.


## Fields

| Field                               | Type                                | Required                            | Description                         |
| ----------------------------------- | ----------------------------------- | ----------------------------------- | ----------------------------------- |
| `p50`                               | *OptionalNullable[float]*           | :heavy_minus_sign:                  | Minimum p50 throughput (tokens/sec) |
| `p75`                               | *OptionalNullable[float]*           | :heavy_minus_sign:                  | Minimum p75 throughput (tokens/sec) |
| `p90`                               | *OptionalNullable[float]*           | :heavy_minus_sign:                  | Minimum p90 throughput (tokens/sec) |
| `p99`                               | *OptionalNullable[float]*           | :heavy_minus_sign:                  | Minimum p99 throughput (tokens/sec) |