import { describe, expect, test } from 'bun:test'
import {
  createAssistantMessage,
  createProgressMessage,
  createUserMessage,
  getUnresolvedToolUseIDs,
  normalizeMessages,
  reorderMessages,
} from '@utils/messages'
import { getReplStaticPrefixLength } from '@utils/terminal/replStaticSplit'

function makeToolResult(toolUseID: string, content = 'ok') {
  return createUserMessage([
    { type: 'tool_result', tool_use_id: toolUseID, content },
  ] as any)
}

function getStaticPrefixUuids(messages: any[]): string[] {
  const normalized = normalizeMessages(messages as any)
  const ordered = reorderMessages(normalized)
  const unresolved = getUnresolvedToolUseIDs(normalized)
  const prefixLen = getReplStaticPrefixLength(ordered, normalized, unresolved)
  return ordered.slice(0, prefixLen).map(m => m.uuid as string)
}

function expectPrefix(prefix: string[], full: string[]) {
  expect(full.slice(0, prefix.length)).toEqual(prefix)
}

describe('REPL Static prefix append-only (regression)', () => {
  test('static prefix uuids only ever append as tool siblings resolve', () => {
    const user = createUserMessage('hi')
    const assistant = createAssistantMessage('ok')

    const siblingToolUseIDs = new Set(['t1', 't2'])
    const toolUseMessage = createAssistantMessage('ignored') as any
    toolUseMessage.message.content = [
      { type: 'tool_use', id: 't1', name: 'Bash', input: {} },
      { type: 'tool_use', id: 't2', name: 'Read', input: {} },
      { type: 'text', text: 'after tools', citations: [] },
    ]

    const progress1 = createProgressMessage(
      't1',
      siblingToolUseIDs,
      createAssistantMessage('running 1'),
      [],
      [],
    )
    const progress2 = createProgressMessage(
      't2',
      siblingToolUseIDs,
      createAssistantMessage('running 2'),
      [],
      [],
    )

    const timeline: any[][] = [
      [user, assistant],
      [user, assistant, toolUseMessage],
      [user, assistant, toolUseMessage, progress1],
      [
        user,
        assistant,
        toolUseMessage,
        progress1,
        makeToolResult('t1', 'done'),
      ],
      [
        user,
        assistant,
        toolUseMessage,
        progress1,
        makeToolResult('t1', 'done'),
        progress2,
      ],
      [
        user,
        assistant,
        toolUseMessage,
        progress1,
        makeToolResult('t1', 'done'),
        progress2,
        makeToolResult('t2', 'done'),
      ],
    ]

    let prev: string[] | null = null
    for (const step of timeline) {
      const next = getStaticPrefixUuids(step)
      if (prev) expectPrefix(prev, next)
      prev = next
    }
  })

  test('normalizeMessages per-block uuids remain stable across later messages', () => {
    const base = createAssistantMessage('ignored') as any
    base.message.content = [
      { type: 'tool_use', id: 't1', name: 'Bash', input: {} },
      { type: 'tool_use', id: 't2', name: 'Read', input: {} },
      { type: 'text', text: 'after tools', citations: [] },
    ]

    const before = normalizeMessages([base] as any)
    const beforeUuids = before
      .filter(
        m => typeof m.uuid === 'string' && m.uuid.startsWith(`${base.uuid}:`),
      )
      .map(m => m.uuid as string)

    const after = normalizeMessages([base, makeToolResult('t1', 'done')] as any)
    const afterUuids = after
      .filter(
        m => typeof m.uuid === 'string' && m.uuid.startsWith(`${base.uuid}:`),
      )
      .map(m => m.uuid as string)

    expect(afterUuids).toEqual(beforeUuids)
  })
})
