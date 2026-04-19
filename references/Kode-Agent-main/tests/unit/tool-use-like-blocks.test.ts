import { describe, expect, test } from 'bun:test'
import { __ToolUseQueueForTests, __isToolUseLikeBlockForTests } from '@query'
import { z } from 'zod'
import type { Tool } from '@tool'
import {
  createAssistantMessage,
  createUserMessage,
  getToolUseID,
  getUnresolvedToolUseIDs,
  normalizeMessages,
} from '@utils/messages'

function makeTool(name: string): Tool {
  return {
    name,
    inputSchema: z.object({}) as any,
    async prompt() {
      return ''
    },
    async isEnabled() {
      return true
    },
    isReadOnly() {
      return true
    },
    isConcurrencySafe() {
      return true
    },
    needsPermissions() {
      return false
    },
    renderResultForAssistant() {
      return ''
    },
    renderToolUseMessage() {
      return ''
    },
    async *call() {
      yield { type: 'result', data: { ok: true }, resultForAssistant: 'ok' }
    },
  } satisfies Tool as any
}

describe('tool_use-like blocks', () => {
  test('__isToolUseLikeBlockForTests matches reference CLI ql0', () => {
    expect(__isToolUseLikeBlockForTests({ type: 'tool_use' })).toBe(true)
    expect(__isToolUseLikeBlockForTests({ type: 'server_tool_use' })).toBe(true)
    expect(__isToolUseLikeBlockForTests({ type: 'mcp_tool_use' })).toBe(true)
    expect(__isToolUseLikeBlockForTests({ type: 'text' })).toBe(false)
  })

  test('ToolUseQueue can process server_tool_use and mcp_tool_use blocks', async () => {
    const EchoTool = makeTool('Echo')

    const toolUseContext: any = {
      abortController: new AbortController(),
      readFileTimestamps: {},
      setToolJSX: () => {},
      options: {
        tools: [EchoTool],
        commands: [],
        forkNumber: 0,
        messageLogName: 'tool-use-like-blocks-test',
        verbose: false,
        safeMode: false,
        maxThinkingTokens: 0,
      },
    }

    const queue: any = new __ToolUseQueueForTests({
      toolDefinitions: [EchoTool],
      canUseTool: async () => ({ result: true }),
      toolUseContext,
      siblingToolUseIDs: new Set(['srv', 'mcp']),
    })

    const assistantMessage = createAssistantMessage('tools')

    const toolUses = [
      { type: 'server_tool_use', id: 'srv', name: 'Echo', input: {} },
      { type: 'mcp_tool_use', id: 'mcp', name: 'Echo', input: {} },
    ].filter(__isToolUseLikeBlockForTests)

    for (const toolUse of toolUses) {
      queue.addTool(toolUse, assistantMessage)
    }

    const out: any[] = []
    for await (const msg of queue.getRemainingResults()) out.push(msg)

    const toolResultIds = out
      .filter(m => m.type === 'user')
      .flatMap(m =>
        Array.isArray(m.message.content)
          ? m.message.content.filter((b: any) => b.type === 'tool_result')
          : [],
      )
      .map((b: any) => b.tool_use_id)

    expect(toolResultIds).toContain('srv')
    expect(toolResultIds).toContain('mcp')
  })

  test('messages utils treat server_tool_use/mcp_tool_use as unresolved tool uses', () => {
    const assistant: any = {
      ...createAssistantMessage('ignored'),
      message: {
        ...createAssistantMessage('ignored').message,
        content: [{ type: 'mcp_tool_use', id: 't1', name: 'Echo', input: {} }],
      },
    }

    const normalized = normalizeMessages([assistant])
    expect(getToolUseID(normalized[0]!)).toBe('t1')
    expect(getUnresolvedToolUseIDs(normalized)).toEqual(new Set(['t1']))

    const withResult = normalizeMessages([
      assistant,
      createUserMessage([
        { type: 'tool_result', tool_use_id: 't1', content: 'ok' },
      ]),
    ])
    expect(getUnresolvedToolUseIDs(withResult)).toEqual(new Set())
  })
})
