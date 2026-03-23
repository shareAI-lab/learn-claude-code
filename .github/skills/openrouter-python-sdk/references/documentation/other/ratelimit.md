# ~~RateLimit~~

Legacy rate limit information about a key. Will always return -1.

> :warning: **DEPRECATED**: This will be removed in a future release, please migrate away from it as soon as possible.


## Fields

| Field                                        | Type                                         | Required                                     | Description                                  | Example                                      |
| -------------------------------------------- | -------------------------------------------- | -------------------------------------------- | -------------------------------------------- | -------------------------------------------- |
| `requests`                                   | *float*                                      | :heavy_check_mark:                           | Number of requests allowed per interval      | 1000                                         |
| `interval`                                   | *str*                                        | :heavy_check_mark:                           | Rate limit interval                          | 1h                                           |
| `note`                                       | *str*                                        | :heavy_check_mark:                           | Note about the rate limit                    | This field is deprecated and safe to ignore. |