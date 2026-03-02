# OpenResponsesRequestTrace

Metadata for observability and tracing. Known keys (trace_id, trace_name, span_name, generation_name, parent_span_id) have special handling. Additional keys are passed through as custom metadata to configured broadcast destinations.


## Fields

| Field                      | Type                       | Required                   | Description                |
| -------------------------- | -------------------------- | -------------------------- | -------------------------- |
| `trace_id`                 | *Optional[str]*            | :heavy_minus_sign:         | N/A                        |
| `trace_name`               | *Optional[str]*            | :heavy_minus_sign:         | N/A                        |
| `span_name`                | *Optional[str]*            | :heavy_minus_sign:         | N/A                        |
| `generation_name`          | *Optional[str]*            | :heavy_minus_sign:         | N/A                        |
| `parent_span_id`           | *Optional[str]*            | :heavy_minus_sign:         | N/A                        |
| `__pydantic_extra__`       | Dict[str, *Nullable[Any]*] | :heavy_minus_sign:         | N/A                        |