import { describe, expect, test } from 'bun:test'
import { __ToolUseQueueForTests } from '@query'
import { z } from 'zod'
import type { Tool } from '@tool'
import { createAssistantMessage } from '@utils/messages'
import { isBashCommandReadOnly } from '@utils/permissions/bashReadOnly'
import { BashTool } from '@tools/BashTool/BashTool'

function deferred<T = void>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function makeBashLikeTool(options: { callImpl: Tool['call'] }): Tool {
  const inputSchema = z.strictObject({
    command: z.string(),
  })

  return {
    name: 'Bash',
    inputSchema: inputSchema as any,
    async prompt() {
      return ''
    },
    async isEnabled() {
      return true
    },
    isReadOnly(input?: any) {
      return (
        typeof input?.command === 'string' &&
        isBashCommandReadOnly(input.command)
      )
    },
    isConcurrencySafe(input?: any) {
      return this.isReadOnly(input)
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
    call: options.callImpl as any,
  } satisfies Tool as any
}

function makeToolUse(id: string, input: any) {
  return { id, name: 'Bash', input, type: 'tool_use' } as any
}

describe('Bash read-only detection + scheduler concurrency parity', () => {
  test('read-only detector is conservative for complex commands', () => {
    expect(isBashCommandReadOnly('pwd')).toBe(true)
    expect(isBashCommandReadOnly('ls -la')).toBe(true)
    expect(isBashCommandReadOnly('git status')).toBe(true)

    expect(isBashCommandReadOnly('ls | grep foo')).toBe(false)
    expect(isBashCommandReadOnly('ls && pwd')).toBe(false)
    expect(isBashCommandReadOnly('cat foo > bar')).toBe(false)
    expect(isBashCommandReadOnly('git -c core.pager=cat status')).toBe(false)
  })

  test('BashTool concurrency-safe matches read-only detection', () => {
    expect(BashTool.isReadOnly({ command: 'pwd' } as any)).toBe(true)
    expect(BashTool.isConcurrencySafe({ command: 'pwd' } as any)).toBe(true)
    expect(BashTool.isReadOnly({ command: 'cat foo > bar' } as any)).toBe(false)
    expect(
      BashTool.isConcurrencySafe({ command: 'cat foo > bar' } as any),
    ).toBe(false)
  })

  test('two read-only Bash tool uses can start concurrently', async () => {
    const started: string[] = []
    const gateA = deferred()
    const gateB = deferred()

    const Bash = makeBashLikeTool({
      callImpl: async function* (_input: any, ctx: any) {
        started.push(ctx.toolUseId)
        if (ctx.toolUseId === 'a') await gateA.promise
        if (ctx.toolUseId === 'b') await gateB.promise
        yield { type: 'result', data: { ok: true }, resultForAssistant: 'ok' }
      },
    })

    const toolUseContext: any = {
      abortController: new AbortController(),
      readFileTimestamps: {},
      setToolJSX: () => {},
      options: {
        tools: [Bash],
        commands: [],
        forkNumber: 0,
        messageLogName: 'bash-readonly-concurrency',
        verbose: false,
        safeMode: false,
        maxThinkingTokens: 0,
      },
    }

    const queue: any = new __ToolUseQueueForTests({
      toolDefinitions: [Bash],
      canUseTool: async () => ({ result: true }),
      toolUseContext,
      siblingToolUseIDs: new Set(['a', 'b']),
    })

    const assistantMessage = createAssistantMessage('tools')

    let consumePromise: Promise<any[]> | null = null
    try {
      queue.addTool(makeToolUse('a', { command: 'pwd' }), assistantMessage)
      queue.addTool(makeToolUse('b', { command: 'pwd' }), assistantMessage)

      consumePromise = (async () => {
        const out: any[] = []
        for await (const msg of queue.getRemainingResults()) out.push(msg)
        return out
      })()

      await new Promise(r => setTimeout(r, 0))
      expect(new Set(started)).toEqual(new Set(['a', 'b']))

      gateA.resolve()
      gateB.resolve()
      await consumePromise
    } finally {
      gateA.resolve()
      gateB.resolve()
      if (consumePromise) await consumePromise
    }
  })

  test('non-read-only Bash tool use blocks subsequent Bash tool uses', async () => {
    const started: string[] = []
    const gateA = deferred()
    const gateB = deferred()

    const Bash = makeBashLikeTool({
      callImpl: async function* (_input: any, ctx: any) {
        started.push(ctx.toolUseId)
        if (ctx.toolUseId === 'a') await gateA.promise
        if (ctx.toolUseId === 'b') await gateB.promise
        yield { type: 'result', data: { ok: true }, resultForAssistant: 'ok' }
      },
    })

    const toolUseContext: any = {
      abortController: new AbortController(),
      readFileTimestamps: {},
      setToolJSX: () => {},
      options: {
        tools: [Bash],
        commands: [],
        forkNumber: 0,
        messageLogName: 'bash-readonly-barrier',
        verbose: false,
        safeMode: false,
        maxThinkingTokens: 0,
      },
    }

    const queue: any = new __ToolUseQueueForTests({
      toolDefinitions: [Bash],
      canUseTool: async () => ({ result: true }),
      toolUseContext,
      siblingToolUseIDs: new Set(['a', 'b']),
    })

    const assistantMessage = createAssistantMessage('tools')

    let consumePromise: Promise<any[]> | null = null
    try {
      queue.addTool(
        makeToolUse('a', { command: 'cat foo > bar' }),
        assistantMessage,
      )
      queue.addTool(makeToolUse('b', { command: 'pwd' }), assistantMessage)

      consumePromise = (async () => {
        const out: any[] = []
        for await (const msg of queue.getRemainingResults()) out.push(msg)
        return out
      })()

      await new Promise(r => setTimeout(r, 0))
      expect(started).toEqual(['a'])

      gateA.resolve()
      await new Promise(r => setTimeout(r, 0))
      expect(started).toEqual(['a', 'b'])

      gateB.resolve()
      await consumePromise
    } finally {
      gateA.resolve()
      gateB.resolve()
      if (consumePromise) await consumePromise
    }
  })
})
