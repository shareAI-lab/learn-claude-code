# Architecture

Model architecture information


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        | Example                                                            |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `tokenizer`                                                        | [Nullable[components.Tokenizer]](../components/tokenizer.md)       | :heavy_check_mark:                                                 | N/A                                                                | GPT                                                                |
| `instruct_type`                                                    | [Nullable[components.InstructType]](../components/instructtype.md) | :heavy_check_mark:                                                 | Instruction format type                                            |                                                                    |
| `modality`                                                         | *Nullable[str]*                                                    | :heavy_check_mark:                                                 | Primary modality of the model                                      | text                                                               |
| `input_modalities`                                                 | List[[components.InputModality](../components/inputmodality.md)]   | :heavy_check_mark:                                                 | Supported input modalities                                         |                                                                    |
| `output_modalities`                                                | List[[components.OutputModality](../components/outputmodality.md)] | :heavy_check_mark:                                                 | Supported output modalities                                        |                                                                    |