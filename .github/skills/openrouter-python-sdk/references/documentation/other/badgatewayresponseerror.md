# BadGatewayResponseError

Bad Gateway - Provider/upstream API failure


## Fields

| Field                                                                                  | Type                                                                                   | Required                                                                               | Description                                                                            | Example                                                                                |
| -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `error`                                                                                | [components.BadGatewayResponseErrorData](../components/badgatewayresponseerrordata.md) | :heavy_check_mark:                                                                     | Error data for BadGatewayResponse                                                      | {<br/>"code": 502,<br/>"message": "Provider returned error"<br/>}                      |
| `user_id`                                                                              | *OptionalNullable[str]*                                                                | :heavy_minus_sign:                                                                     | N/A                                                                                    |                                                                                        |