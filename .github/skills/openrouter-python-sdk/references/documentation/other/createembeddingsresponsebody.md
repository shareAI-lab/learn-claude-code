# CreateEmbeddingsResponseBody

Embedding response


## Fields

| Field                                                                          | Type                                                                           | Required                                                                       | Description                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `id`                                                                           | *Optional[str]*                                                                | :heavy_minus_sign:                                                             | N/A                                                                            |
| `object`                                                                       | [operations.Object](../operations/object.md)                                   | :heavy_check_mark:                                                             | N/A                                                                            |
| `data`                                                                         | List[[operations.CreateEmbeddingsData](../operations/createembeddingsdata.md)] | :heavy_check_mark:                                                             | N/A                                                                            |
| `model`                                                                        | *str*                                                                          | :heavy_check_mark:                                                             | N/A                                                                            |
| `usage`                                                                        | [Optional[operations.Usage]](../operations/usage.md)                           | :heavy_minus_sign:                                                             | N/A                                                                            |