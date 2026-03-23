# ChatMessageTokenLogprobs

Log probabilities for the completion


## Fields

| Field                                                                                | Type                                                                                 | Required                                                                             | Description                                                                          |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `content`                                                                            | List[[components.ChatMessageTokenLogprob](../components/chatmessagetokenlogprob.md)] | :heavy_check_mark:                                                                   | Log probabilities for content tokens                                                 |
| `refusal`                                                                            | List[[components.ChatMessageTokenLogprob](../components/chatmessagetokenlogprob.md)] | :heavy_check_mark:                                                                   | Log probabilities for refusal tokens                                                 |