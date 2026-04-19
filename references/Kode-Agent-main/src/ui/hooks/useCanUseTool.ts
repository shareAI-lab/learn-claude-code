import React, { useCallback } from 'react'
import { hasPermissionsToUseTool } from '@permissions'
import { BashTool, inputSchema } from '@tools/BashTool/BashTool'
import { getCommandSubcommandPrefix } from '@utils/commands'
import {
  REJECT_MESSAGE,
  REJECT_MESSAGE_WITH_FEEDBACK_PREFIX,
} from '@utils/messages'
import { ToolUseConfirm } from '@components/permissions/PermissionRequest'
import { AbortError } from '@utils/text/errors'
import { logError } from '@utils/log'
import type { CanUseToolFn } from '@kode-types/canUseTool'

type SetState<T> = React.Dispatch<React.SetStateAction<T>>

export type { CanUseToolFn }

function useCanUseTool(
  setToolUseConfirm: SetState<ToolUseConfirm | null>,
): CanUseToolFn {
  return useCallback<CanUseToolFn>(
    async (tool, input, toolUseContext, assistantMessage) => {
      return new Promise(resolve => {
        function logCancelledEvent() {}

        function resolveWithCancelledAndAbortAllToolCalls(message?: string) {
          resolve({
            result: false,
            message: message
              ? `${REJECT_MESSAGE_WITH_FEEDBACK_PREFIX}${message}`
              : REJECT_MESSAGE,
          })
          toolUseContext.abortController.abort()
        }

        if (toolUseContext.abortController.signal.aborted) {
          logCancelledEvent()
          resolveWithCancelledAndAbortAllToolCalls()
          return
        }

        return hasPermissionsToUseTool(
          tool,
          input,
          toolUseContext,
          assistantMessage,
        )
          .then(async result => {
            if (result.result === true) {
              resolve({ result: true })
              return
            }

            const deniedResult = result as Extract<
              typeof result,
              { result: false }
            >

            if (deniedResult.shouldPromptUser === false) {
              resolve({ result: false, message: deniedResult.message })
              return
            }

            const [description, commandPrefix] = await Promise.all([
              typeof tool.description === 'function'
                ? tool.description(input as never)
                : Promise.resolve(tool.description ?? `Tool: ${tool.name}`),
              tool === BashTool
                ? getCommandSubcommandPrefix(
                    inputSchema.parse(input).command,
                    toolUseContext.abortController.signal,
                  )
                : Promise.resolve(null),
            ])

            if (toolUseContext.abortController.signal.aborted) {
              logCancelledEvent()
              resolveWithCancelledAndAbortAllToolCalls()
              return
            }

            setToolUseConfirm({
              assistantMessage,
              tool,
              description,
              input,
              commandPrefix,
              toolUseContext,
              suggestions: deniedResult.suggestions,
              riskScore: null,
              onAbort() {
                logCancelledEvent()
                resolveWithCancelledAndAbortAllToolCalls()
              },
              onAllow(type) {
                if (type === 'permanent') {
                } else {
                }
                resolve({ result: true })
              },
              onReject(rejectionMessage) {
                resolveWithCancelledAndAbortAllToolCalls(rejectionMessage)
              },
            })
          })
          .catch(error => {
            if (error instanceof AbortError) {
              logCancelledEvent()
              resolveWithCancelledAndAbortAllToolCalls()
            } else {
              logError(error)
            }
          })
      })
    },
    [setToolUseConfirm],
  )
}

export default useCanUseTool
