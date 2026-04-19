import { describe, expect, test } from 'bun:test'
import {
  createAssistantMessage,
  createUserMessage,
  getUnresolvedToolUseIDs,
  normalizeMessages,
  reorderMessages,
} from '@utils/messages'
import { getReplStaticPrefixLength } from '@utils/terminal/replStaticSplit'

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

describe('REPL Static prefix split', () => {
  test('static portion is always a prefix of the ordered messages', () => {
    const pre = createAssistantMessage('pre')
    const tool = makeToolUseAssistant('t1')
    const post = createAssistantMessage('post')

    const normalized = normalizeMessages([pre, tool, post])
    const ordered = reorderMessages(normalized)
    const unresolved = getUnresolvedToolUseIDs(normalized)

    expect(unresolved).toEqual(new Set(['t1']))

    const prefixLen = getReplStaticPrefixLength(ordered, normalized, unresolved)

    expect(prefixLen).toBe(1)
  })

  test('static prefix length is monotonic as tools resolve', () => {
    const pre = createAssistantMessage('pre')
    const post = createAssistantMessage('post')

    const tool1 = makeToolUseAssistant('t1')
    const tool2 = makeToolUseAssistant('t2')

    const step1 = [pre, tool1, post]
    const n1 = normalizeMessages(step1)
    const o1 = reorderMessages(n1)
    const u1 = getUnresolvedToolUseIDs(n1)
    const p1 = getReplStaticPrefixLength(o1, n1, u1)

    const step2 = [pre, tool1, makeToolResult('t1', 'done'), post]
    const n2 = normalizeMessages(step2)
    const o2 = reorderMessages(n2)
    const u2 = getUnresolvedToolUseIDs(n2)
    const p2 = getReplStaticPrefixLength(o2, n2, u2)

    const step3 = [pre, tool1, makeToolResult('t1', 'done'), post, tool2]
    const n3 = normalizeMessages(step3)
    const o3 = reorderMessages(n3)
    const u3 = getUnresolvedToolUseIDs(n3)
    const p3 = getReplStaticPrefixLength(o3, n3, u3)

    const step4 = [
      pre,
      tool1,
      makeToolResult('t1', 'done'),
      post,
      tool2,
      makeToolResult('t2', 'done'),
    ]
    const n4 = normalizeMessages(step4)
    const o4 = reorderMessages(n4)
    const u4 = getUnresolvedToolUseIDs(n4)
    const p4 = getReplStaticPrefixLength(o4, n4, u4)

    const prefixLengths = [p1, p2, p3, p4]
    const sorted = prefixLengths.slice().sort((a, b) => a - b)
    expect(prefixLengths).toEqual(sorted)
    expect(u2.size).toBe(0)
    expect(u4.size).toBe(0)
  })
})
