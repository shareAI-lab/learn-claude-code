import type { Tool as ToolType, ToolUseContext } from '@tool'
import type { AssistantMessage } from '@query'
import type { ToolPermissionContextUpdate } from '@kode-types/toolPermissionContext'

export type CanUseToolFn = (
  tool: ToolType,
  input: { [key: string]: unknown },
  toolUseContext: ToolUseContext,
  assistantMessage: AssistantMessage,
) => Promise<
  | { result: true }
  | {
      result: false
      message: string
      shouldPromptUser?: boolean
      suggestions?: ToolPermissionContextUpdate[]
    }
>

