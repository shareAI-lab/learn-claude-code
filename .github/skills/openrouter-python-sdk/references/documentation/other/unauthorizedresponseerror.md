# UnauthorizedResponseError

Unauthorized - Authentication required or invalid credentials


## Fields

| Field                                                                                      | Type                                                                                       | Required                                                                                   | Description                                                                                | Example                                                                                    |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `error`                                                                                    | [components.UnauthorizedResponseErrorData](../components/unauthorizedresponseerrordata.md) | :heavy_check_mark:                                                                         | Error data for UnauthorizedResponse                                                        | {<br/>"code": 401,<br/>"message": "Missing Authentication header"<br/>}                    |
| `user_id`                                                                                  | *OptionalNullable[str]*                                                                    | :heavy_minus_sign:                                                                         | N/A                                                                                        |                                                                                            |