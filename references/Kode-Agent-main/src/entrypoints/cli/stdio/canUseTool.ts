export function createStdioCanUseTool(args: {
  normalizedPermissionPromptTool: string | null
  structured: any | null
  permissionTimeoutMs: number
  cwd: string
  printOptions: any
  hasPermissionsToUseTool: any
  applyToolPermissionContextUpdates: any
  persistToolPermissionUpdateToDisk: any
}): any {
  if (args.normalizedPermissionPromptTool !== 'stdio' || !args.structured) {
    return args.hasPermissionsToUseTool
  }

  return (async (
    tool: any,
    input: any,
    toolUseContext: any,
    assistantMessage: any,
  ) => {
    const base = await args.hasPermissionsToUseTool(
      tool,
      input,
      toolUseContext,
      assistantMessage,
    )

    if (base.result === true) return { result: true as const }

    const denied = base as Extract<typeof base, { result: false }>
    if (denied.shouldPromptUser === false) {
      return { result: false as const, message: denied.message }
    }

    try {
      const blockedPath =
        typeof (denied as any).blockedPath === 'string'
          ? String((denied as any).blockedPath)
          : typeof (input as any)?.file_path === 'string'
            ? String((input as any).file_path)
            : typeof (input as any)?.notebook_path === 'string'
              ? String((input as any).notebook_path)
              : typeof (input as any)?.path === 'string'
                ? String((input as any).path)
                : undefined

      const decisionReason =
        typeof (denied as any).decisionReason === 'string'
          ? String((denied as any).decisionReason)
          : undefined

      const response = await args.structured.sendRequest(
        {
          subtype: 'can_use_tool',
          tool_name: tool.name,
          input,
          ...(typeof toolUseContext?.toolUseId === 'string' && toolUseContext.toolUseId
            ? { tool_use_id: toolUseContext.toolUseId }
            : {}),
          ...(typeof toolUseContext?.agentId === 'string' && toolUseContext.agentId
            ? { agent_id: toolUseContext.agentId }
            : {}),
          ...(Array.isArray((denied as any).suggestions)
            ? {
                permission_suggestions: (denied as any).suggestions,
              }
            : {}),
          ...(blockedPath ? { blocked_path: blockedPath } : {}),
          ...(decisionReason ? { decision_reason: decisionReason } : {}),
        },
        {
          signal: toolUseContext.abortController.signal,
          timeoutMs: args.permissionTimeoutMs,
        },
      )

      if (response && (response as any).behavior === 'allow') {
        const updatedInput =
          (response as any).updatedInput && typeof (response as any).updatedInput === 'object'
            ? (response as any).updatedInput
            : null
        if (updatedInput) {
          Object.assign(input, updatedInput)
        }

        const updatedPermissionsRaw = (response as any).updatedPermissions
        const updatedPermissions =
          Array.isArray(updatedPermissionsRaw) &&
          updatedPermissionsRaw.every(
            u => u && typeof u === 'object' && typeof (u as any).type === 'string',
          )
            ? (updatedPermissionsRaw as any[])
            : null

        if (updatedPermissions && args.printOptions.toolPermissionContext) {
          const next = args.applyToolPermissionContextUpdates(
            args.printOptions.toolPermissionContext,
            updatedPermissions as any,
          )
          args.printOptions.toolPermissionContext = next
          if (toolUseContext?.options) {
            toolUseContext.options.toolPermissionContext = next
          }
          for (const update of updatedPermissions as any) {
            args.persistToolPermissionUpdateToDisk({
              update,
              projectDir: args.cwd,
            })
          }
        }

        return { result: true as const }
      }

      if (response && (response as any).behavior === 'deny') {
        if ((response as any).interrupt === true) {
          toolUseContext.abortController.abort()
        }
      }

      return {
        result: false as const,
        message:
          typeof (response as any)?.message === 'string'
            ? String((response as any).message)
            : denied.message,
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      return {
        result: false as const,
        message: `Permission prompt failed: ${msg}`,
        shouldPromptUser: false,
      }
    }
  }) as any
}
