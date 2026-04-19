export function createPrintModeControlRequestHandler(args: {
  printOptions: any
  mcpClients: any[]
}): (msg: any) => Promise<any> {
  return async msg => {
    const subtype = msg.request?.subtype

    if (subtype === 'initialize') {
      return
    }

    if (subtype === 'set_permission_mode') {
      const mode = (msg.request as any)?.mode
      if (
        mode === 'default' ||
        mode === 'acceptEdits' ||
        mode === 'plan' ||
        mode === 'dontAsk' ||
        mode === 'bypassPermissions'
      ) {
        if (args.printOptions.toolPermissionContext) {
          args.printOptions.toolPermissionContext.mode = mode
        }
      }
      return
    }

    if (subtype === 'set_model') {
      const requested = (msg.request as any)?.model
      if (requested === 'default') {
        args.printOptions.model = undefined as any
      } else if (typeof requested === 'string' && requested.trim()) {
        args.printOptions.model = requested.trim()
      }
      return
    }

    if (subtype === 'set_max_thinking_tokens') {
      const value = (msg.request as any)?.max_thinking_tokens
      if (value === null) {
        args.printOptions.maxThinkingTokens = 0
      } else if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
        args.printOptions.maxThinkingTokens = value
      }
      return
    }

    if (subtype === 'mcp_status') {
      return {
        mcpServers: args.mcpClients.map(c => ({
          name: c.name,
          status: c.type,
          ...(c.type === 'connected' && c.capabilities
            ? { serverInfo: c.capabilities }
            : {}),
        })),
      }
    }

    if (subtype === 'mcp_message') {
      const serverName = (msg.request as any)?.server_name
      const message = (msg.request as any)?.message
      if (typeof serverName === 'string' && serverName) {
        const found = args.mcpClients.find(c => c.name === serverName)
        if (found && found.type === 'connected') {
          const transport = (found.client as any)?.transport
          if (transport && typeof transport.onmessage === 'function') {
            transport.onmessage(message)
          }
        }
      }
      return
    }

    if (subtype === 'mcp_set_servers') {
      return { ok: true, sdkServersChanged: false }
    }

    if (subtype === 'rewind_files') {
      throw new Error('rewind_files is not supported in Kode yet.')
    }

    throw new Error(`Unsupported control request subtype: ${String(subtype)}`)
  }
}

