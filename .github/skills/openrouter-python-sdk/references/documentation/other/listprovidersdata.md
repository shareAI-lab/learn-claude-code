# ListProvidersData


## Fields

| Field                                    | Type                                     | Required                                 | Description                              | Example                                  |
| ---------------------------------------- | ---------------------------------------- | ---------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| `name`                                   | *str*                                    | :heavy_check_mark:                       | Display name of the provider             | OpenAI                                   |
| `slug`                                   | *str*                                    | :heavy_check_mark:                       | URL-friendly identifier for the provider | openai                                   |
| `privacy_policy_url`                     | *Nullable[str]*                          | :heavy_check_mark:                       | URL to the provider's privacy policy     | https://openai.com/privacy               |
| `terms_of_service_url`                   | *OptionalNullable[str]*                  | :heavy_minus_sign:                       | URL to the provider's terms of service   | https://openai.com/terms                 |
| `status_page_url`                        | *OptionalNullable[str]*                  | :heavy_minus_sign:                       | URL to the provider's status page        | https://status.openai.com                |