import type { Message as KodeMessage } from '@query'


export type SdkMessage =
  | {
      type: 'system'
      subtype: string
      session_id?: string
      model?: string
      cwd?: string
      tools?: string[]
      slash_commands?: string[]
      status?: string
      uuid?: string
    }
  | {
      type: 'user'
      session_id?: string
      uuid?: string
      parent_tool_use_id?: string | null
      message: { role: 'user'; content: any }
    }
  | {
      type: 'assistant'
      session_id?: string
      uuid?: string
      parent_tool_use_id?: string | null
      message: { role: 'assistant'; content: any[] }
    }
  | {
      type: 'result'
      subtype: 'success' | 'error_during_execution' | 'error_max_turns'
      result?: string
      structured_output?: Record<string, unknown>
      num_turns: number
      usage?: any
      total_cost_usd: number
      duration_ms: number
      duration_api_ms: number
      is_error: boolean
      session_id: string
    }
  | {
      type: 'log'
      log: { level: 'debug' | 'info' | 'warn' | 'error'; message: string }
    }

function normalizeToolUseBlockTypes(block: any): any {
  if (!block || typeof block !== 'object') return block
  if (block.type === 'server_tool_use' || block.type === 'mcp_tool_use') {
    return { ...block, type: 'tool_use' }
  }
  return block
}

export function makeSdkInitMessage(args: {
  sessionId: string
  cwd: string
  model?: string
  tools?: string[]
  slashCommands?: string[]
}): SdkMessage {
  return {
    type: 'system',
    subtype: 'init',
    session_id: args.sessionId,
    cwd: args.cwd,
    model: args.model,
    tools: args.tools,
    ...(args.slashCommands ? { slash_commands: args.slashCommands } : {}),
  }
}

export function makeSdkResultMessage(args: {
  sessionId: string
  result: string
  structuredOutput?: Record<string, unknown>
  numTurns: number
  usage?: any
  totalCostUsd: number
  durationMs: number
  durationApiMs: number
  isError: boolean
}): SdkMessage {
  return {
    type: 'result',
    subtype: args.isError ? 'error_during_execution' : 'success',
    result: args.result,
    ...(args.structuredOutput
      ? { structured_output: args.structuredOutput }
      : {}),
    num_turns: args.numTurns,
    usage: args.usage,
    total_cost_usd: args.totalCostUsd,
    duration_ms: args.durationMs,
    duration_api_ms: args.durationApiMs,
    is_error: args.isError,
    session_id: args.sessionId,
  }
}

export function kodeMessageToSdkMessage(
  message: KodeMessage,
  sessionId: string,
): SdkMessage | null {
  if (message.type === 'progress') return null

  if (message.type === 'user') {
    return {
      type: 'user',
      session_id: sessionId,
      uuid: message.uuid,
      parent_tool_use_id: null,
      message: {
        role: 'user',
        content: message.message.content as any,
      },
    }
  }

  if (message.type === 'assistant') {
    const content = Array.isArray(message.message.content)
      ? message.message.content.map(normalizeToolUseBlockTypes)
      : []
    return {
      type: 'assistant',
      session_id: sessionId,
      uuid: message.uuid,
      parent_tool_use_id: null,
      message: {
        role: 'assistant',
        content: content as any[],
      },
    }
  }

  return null
}
