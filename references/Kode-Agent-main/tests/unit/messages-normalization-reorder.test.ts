import { describe, expect, test } from 'bun:test'
import {
  createAssistantAPIErrorMessage,
  createAssistantMessage,
  createProgressMessage,
  createUserMessage,
  filterUserTextMessagesForUndo,
  getInProgressToolUseIDs,
  getUnresolvedToolUseIDs,
  normalizeMessages,
  normalizeMessagesForAPI,
  reorderMessages,
} from '@utils/messages'

function makeToolUseAssistant(toolUseID: string) {
  const base = createAssistantMessage('ignored')
  return {
    ...base,
    message: {
      ...base.message,
      content: [{ type: 'tool_use', id: toolUseID, name: 'Echo', input: {} }],
    },
  } as any
}

function makeToolResult(toolUseID: string, content = 'ok') {
  return createUserMessage([
    { type: 'tool_result', tool_use_id: toolUseID, content },
  ] as any)
}

describe('messages normalization + reordering parity', () => {
  test('normalizeMessagesForAPI merges consecutive user messages and keeps tool_result blocks first', () => {
    const merged = normalizeMessagesForAPI([
      makeToolResult('t1'),
      makeToolResult('t2'),
      createUserMessage('meta'),
      createAssistantMessage('ok'),
    ])

    expect(merged).toHaveLength(2)
    expect(merged[0]!.type).toBe('user')
    expect(merged[1]!.type).toBe('assistant')

    const content = (merged[0] as any).message.content
    expect(Array.isArray(content)).toBe(true)
    expect(content[0]).toMatchObject({ type: 'tool_result', tool_use_id: 't1' })
    expect(content[1]).toMatchObject({ type: 'tool_result', tool_use_id: 't2' })
    expect(content[2]).toMatchObject({ type: 'text', text: 'meta' })
  })

  test('normalizeMessagesForAPI filters synthetic api error assistant messages', () => {
    const out = normalizeMessagesForAPI([
      createUserMessage('hi'),
      createAssistantAPIErrorMessage('oops'),
      createAssistantMessage('ok'),
    ])
    expect(out.map(m => m.type)).toEqual(['user', 'assistant'])
    expect((out[1] as any).message.content[0]?.text).toBe('ok')
  })

  test('normalizeMessagesForAPI merges assistant messages by id (ignoring intervening tool results)', () => {
    const a1 = createAssistantMessage('part 1')
    const a2 = {
      ...createAssistantMessage('part 2'),
      message: {
        ...createAssistantMessage('part 2').message,
        id: a1.message.id,
      },
    }

    const out = normalizeMessagesForAPI([a1, makeToolResult('t1'), a2 as any])
    expect(out).toHaveLength(2)
    expect(out[0]!.type).toBe('assistant')
    expect((out[0] as any).message.content.map((b: any) => b.type)).toEqual([
      'text',
      'text',
    ])
  })

  test('reorderMessages inserts progress after tool_use and tool_result after progress', () => {
    const toolUse = makeToolUseAssistant('t1')
    const toolResult = makeToolResult('t1', 'done')
    const progress = createProgressMessage(
      't1',
      new Set(['t1']),
      createAssistantMessage('working'),
      [],
      [],
    )

    const normalized = normalizeMessages([toolUse, toolResult, progress])
    const reordered = reorderMessages(normalized)

    expect(reordered.map(m => m.type)).toEqual([
      'assistant',
      'progress',
      'user',
    ])
    expect(getUnresolvedToolUseIDs(reordered)).toEqual(new Set())
  })

  test('getInProgressToolUseIDs includes first unresolved and any unresolved with progress', () => {
    const t1 = makeToolUseAssistant('t1')
    const t2 = makeToolUseAssistant('t2')
    const progressT2 = createProgressMessage(
      't2',
      new Set(['t1', 't2']),
      createAssistantMessage('working'),
      [],
      [],
    )

    const normalized = normalizeMessages([t1, t2, progressT2])
    expect(getUnresolvedToolUseIDs(normalized)).toEqual(new Set(['t1', 't2']))
    expect(getInProgressToolUseIDs(normalized)).toEqual(new Set(['t1', 't2']))
  })

  test('filterUserTextMessagesForUndo excludes tool_result-only messages', () => {
    const messages = [
      createUserMessage('hello'),
      makeToolResult('t1'),
      createAssistantMessage('response'),
    ]
    const result = filterUserTextMessagesForUndo(messages as any)
    expect(result).toHaveLength(1)
    expect(result[0]!.message.content).toBe('hello')
  })

  test('filterUserTextMessagesForUndo keeps user text after tool_results', () => {
    const messages = [
      createUserMessage('first'),
      createAssistantMessage('response'),
      makeToolResult('t1'),
      makeToolResult('t2'),
      createUserMessage('second'),
    ]
    const result = filterUserTextMessagesForUndo(messages as any)
    expect(result).toHaveLength(2)
    expect(result[0]!.message.content).toBe('first')
    expect(result[1]!.message.content).toBe('second')
  })
})
