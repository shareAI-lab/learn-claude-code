# SystemMessage

System message for setting behavior


## Fields

| Field                                                                    | Type                                                                     | Required                                                                 | Description                                                              | Example                                                                  |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `role`                                                                   | [components.SystemMessageRole](../components/systemmessagerole.md)       | :heavy_check_mark:                                                       | N/A                                                                      |                                                                          |
| `content`                                                                | [components.SystemMessageContent](../components/systemmessagecontent.md) | :heavy_check_mark:                                                       | System message content                                                   | You are a helpful assistant.                                             |
| `name`                                                                   | *Optional[str]*                                                          | :heavy_minus_sign:                                                       | Optional name for the system message                                     | Assistant Config                                                         |