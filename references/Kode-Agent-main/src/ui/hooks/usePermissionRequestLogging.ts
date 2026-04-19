import { useEffect } from 'react'

import { logUnaryEvent, CompletionType } from '@utils/log/unaryLogging'
import { ToolUseConfirm } from '@components/permissions/PermissionRequest'
import { env } from '@utils/config/env'

export type UnaryEvent = {
  completion_type: CompletionType
  language_name: string | Promise<string>
}

export function usePermissionRequestLogging(
  toolUseConfirm: ToolUseConfirm,
  unaryEvent: UnaryEvent,
): void {
  useEffect(() => {
    const languagePromise = Promise.resolve(unaryEvent.language_name)

    languagePromise.then(language => {
      logUnaryEvent({
        completion_type: unaryEvent.completion_type,
        event: 'response',
        metadata: {
          language_name: language,
          message_id: toolUseConfirm.assistantMessage.message.id,
          platform: env.platform,
        },
      })
    })
  }, [toolUseConfirm, unaryEvent])
}
