export type CompletionType =
  | 'str_replace_single'
  | 'write_file_single'
  | 'tool_use_single'

type LogEvent = {
  completion_type: CompletionType
  event: 'accept' | 'reject' | 'response'
  metadata: {
    language_name: string
    message_id: string
    platform: string
  }
}

export function logUnaryEvent(event: LogEvent): void {
}
