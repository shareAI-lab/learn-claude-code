import { env } from '@utils/config/env'
import { CompletionType, logUnaryEvent } from '@utils/log/unaryLogging'
import { ToolUseConfirm } from './PermissionRequest'

export function logUnaryPermissionEvent(
  completion_type: CompletionType,
  {
    assistantMessage: {
      message: { id: message_id },
    },
  }: ToolUseConfirm,
  event: 'accept' | 'reject',
): void {
  logUnaryEvent({
    completion_type,
    event,
    metadata: {
      language_name: 'none',
      message_id,
      platform: env.platform,
    },
  })
}
