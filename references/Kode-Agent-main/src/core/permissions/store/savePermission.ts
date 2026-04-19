import type { Tool, ToolUseContext } from '@tool'
import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { NotebookEditTool } from '@tools/NotebookEditTool/NotebookEditTool'
import { getCurrentProjectConfig, saveCurrentProjectConfig } from '@utils/config'
import { logError } from '@utils/log'
import { grantWritePermissionForPath } from '@utils/permissions/filesystem'
import { persistToolPermissionUpdateToDisk } from '@utils/permissions/toolPermissionSettings'
import { applyToolPermissionContextUpdateForConversationKey } from '@utils/permissions/toolPermissionContextState'
import { getPermissionKey } from '../rules'

export async function savePermission(
  tool: Tool,
  input: { [k: string]: unknown },
  prefix: string | null,
  context?: ToolUseContext,
): Promise<void> {
  const key = getPermissionKey(tool, input, prefix)

  if (
    tool === FileEditTool ||
    tool === FileWriteTool ||
    tool === NotebookEditTool
  ) {
    const filePath =
      tool === NotebookEditTool
        ? typeof (input as any).notebook_path === 'string'
          ? (input as any).notebook_path
          : ''
        : typeof (input as any).file_path === 'string'
          ? (input as any).file_path
          : ''
    if (filePath) {
      grantWritePermissionForPath(filePath)
    }
    return
  }

  try {
    const update = {
      type: 'addRules' as const,
      destination: 'localSettings' as const,
      behavior: 'allow' as const,
      rules: [key],
    }
    persistToolPermissionUpdateToDisk({ update })

    const messageLogName = context?.options?.messageLogName
    const forkNumber = context?.options?.forkNumber ?? 0
    if (messageLogName) {
      const conversationKey = `${messageLogName}:${forkNumber}`
      const nextToolPermissionContext =
        applyToolPermissionContextUpdateForConversationKey({
          conversationKey,
          isBypassPermissionsModeAvailable: !(context?.options?.safeMode ?? false),
          update,
        })
      if (context?.options) {
        ;(context.options as any).toolPermissionContext = nextToolPermissionContext
      }
    }
  } catch (error) {
    logError(error)
  }

  const projectConfig = getCurrentProjectConfig()
  if (projectConfig.allowedTools.includes(key)) {
    return
  }

  projectConfig.allowedTools.push(key)
  projectConfig.allowedTools.sort()

  saveCurrentProjectConfig(projectConfig)
}
