# ForbiddenResponseError

Forbidden - Authentication successful but insufficient permissions


## Fields

| Field                                                                                | Type                                                                                 | Required                                                                             | Description                                                                          | Example                                                                              |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `error`                                                                              | [components.ForbiddenResponseErrorData](../components/forbiddenresponseerrordata.md) | :heavy_check_mark:                                                                   | Error data for ForbiddenResponse                                                     | {<br/>"code": 403,<br/>"message": "Only management keys can perform this operation"<br/>} |
| `user_id`                                                                            | *OptionalNullable[str]*                                                              | :heavy_minus_sign:                                                                   | N/A                                                                                  |                                                                                      |