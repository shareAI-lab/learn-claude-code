import { useInput } from 'ink'
import * as React from 'react'
import { Tool } from '@tool'
import { AssistantMessage } from '@query'
import type { ToolUseContext } from '@tool'
import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { BashTool } from '@tools/BashTool/BashTool'
import { FileEditPermissionRequest } from './file-edit-permission-request/FileEditPermissionRequest'
import { BashPermissionRequest } from './bash-permission-request/BashPermissionRequest'
import { FallbackPermissionRequest } from './FallbackPermissionRequest'
import { useNotifyAfterTimeout } from '@hooks/useNotifyAfterTimeout'
import { FileWritePermissionRequest } from './file-write-permission-request/FileWritePermissionRequest'
import { type CommandSubcommandPrefixResult } from '@utils/commands'
import { FilesystemPermissionRequest } from './filesystem-permission-request/FilesystemPermissionRequest'
import { NotebookEditTool } from '@tools/NotebookEditTool/NotebookEditTool'
import { GlobTool } from '@tools/GlobTool/GlobTool'
import { GrepTool } from '@tools/search/GrepTool/GrepTool'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { PRODUCT_NAME } from '@constants/product'
import { SlashCommandTool } from '@tools/interaction/SlashCommandTool/SlashCommandTool'
import { SkillTool } from '@tools/ai/SkillTool/SkillTool'
import { SlashCommandPermissionRequest } from './slash-command-permission-request/SlashCommandPermissionRequest'
import { SkillPermissionRequest } from './skill-permission-request/SkillPermissionRequest'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'
import { WebFetchPermissionRequest } from './web-fetch-permission-request/WebFetchPermissionRequest'
import { EnterPlanModeTool } from '@tools/agent/PlanModeTool/EnterPlanModeTool'
import { ExitPlanModeTool } from '@tools/agent/PlanModeTool/ExitPlanModeTool'
import { EnterPlanModePermissionRequest } from './plan-mode-permission-request/EnterPlanModePermissionRequest'
import { ExitPlanModePermissionRequest } from './plan-mode-permission-request/ExitPlanModePermissionRequest'
import { AskUserQuestionTool } from '@tools/interaction/AskUserQuestionTool/AskUserQuestionTool'
import { AskUserQuestionPermissionRequest } from './ask-user-question-permission-request/AskUserQuestionPermissionRequest'
import type { ToolPermissionContextUpdate } from '@kode-types/toolPermissionContext'

function permissionComponentForTool(tool: Tool) {
  switch (tool) {
    case FileEditTool:
      return FileEditPermissionRequest
    case FileWriteTool:
      return FileWritePermissionRequest
    case BashTool:
      return BashPermissionRequest
    case GlobTool:
    case GrepTool:
    case FileReadTool:
    case NotebookEditTool:
      return FilesystemPermissionRequest
    case SlashCommandTool:
      return SlashCommandPermissionRequest
    case SkillTool:
      return SkillPermissionRequest
    case WebFetchTool:
      return WebFetchPermissionRequest
    case EnterPlanModeTool:
      return EnterPlanModePermissionRequest
    case ExitPlanModeTool:
      return ExitPlanModePermissionRequest
    case AskUserQuestionTool:
      return AskUserQuestionPermissionRequest
    default:
      return FallbackPermissionRequest
  }
}

export type PermissionRequestProps = {
  toolUseConfirm: ToolUseConfirm
  onDone(): void
  verbose: boolean
}

export function toolUseConfirmGetPrefix(
  toolUseConfirm: ToolUseConfirm,
): string | null {
  return (
    (toolUseConfirm.commandPrefix &&
      !(toolUseConfirm.commandPrefix as any).commandInjectionDetected &&
      (toolUseConfirm.commandPrefix as any).commandPrefix) ||
    null
  )
}

export type ToolUseConfirm = {
  assistantMessage: AssistantMessage
  tool: Tool
  description: string
  input: { [key: string]: unknown }
  commandPrefix: CommandSubcommandPrefixResult | null
  toolUseContext: ToolUseContext
  suggestions?: ToolPermissionContextUpdate[]
  riskScore: number | null
  onAbort(): void
  onAllow(type: 'permanent' | 'temporary'): void
  onReject(rejectionMessage?: string): void
}

export function PermissionRequest({
  toolUseConfirm,
  onDone,
  verbose,
}: PermissionRequestProps): React.ReactNode {
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      onDone()
      toolUseConfirm.onReject()
    }
  })

  const toolName =
    toolUseConfirm.tool.userFacingName?.() || toolUseConfirm.tool.name || 'Tool'
  useNotifyAfterTimeout(
    `${PRODUCT_NAME} needs your permission to use ${toolName}`,
  )

  const PermissionComponent = permissionComponentForTool(toolUseConfirm.tool)

  return (
    <PermissionComponent
      toolUseConfirm={toolUseConfirm}
      onDone={onDone}
      verbose={verbose}
    />
  )
}
