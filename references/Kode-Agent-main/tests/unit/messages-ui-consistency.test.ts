import { describe, expect, test } from 'bun:test'
import {
  createAssistantMessage,
  createProgressMessage,
  createUserMessage,
  extractTag,
  getInProgressToolUseIDs,
  getUnresolvedToolUseIDs,
  normalizeMessages,
  reorderMessages,
} from '@utils/messages'
import { getReplStaticPrefixLength } from '@utils/terminal/replStaticSplit'

function makeToolUseAssistantWithSiblings(toolUseIDs: string[]) {
  const base = createAssistantMessage('ignored') as any
  base.message.content = toolUseIDs.map(id => ({
    type: 'tool_use',
    id,
    name: 'Bash',
    input: { command: `echo ${id}` },
  }))
  return base
}

function makeToolResult(toolUseID: string, content = 'ok') {
  return createUserMessage([
    { type: 'tool_result', tool_use_id: toolUseID, content },
  ] as any)
}

function makeProgress(
  toolUseID: string,
  siblingToolUseIDs: Set<string>,
  text: string,
) {
  return createProgressMessage(
    toolUseID,
    siblingToolUseIDs,
    createAssistantMessage(`<tool-progress>${text}</tool-progress>`),
    [],
    [],
  )
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

describe('UI messages consistency (no duplicate tool rendering)', () => {
  test('reorderMessages replaces multiple progress messages for the same tool_use_id', () => {
    const toolUse = makeToolUseAssistantWithSiblings(['t1'])
    const siblings = new Set(['t1'])

    const p1 = makeProgress('t1', siblings, 'Running…')
    const p2 = makeProgress('t1', siblings, 'Still running…')

    const normalized = normalizeMessages([toolUse, p1, p2] as any)
    const ordered = reorderMessages(normalized)

    const progress = ordered.filter(m => m.type === 'progress')
    expect(progress).toHaveLength(1)

    const firstBlock = (progress[0] as any).content.message.content[0]
    const rawText = String(firstBlock.text ?? '')
    expect(extractTag(rawText, 'tool-progress')).toBe('Still running…')
  })

  test('queued Waiting… progress does not count as in-progress for non-first tools', () => {
    const t1 = makeToolUseAssistantWithSiblings(['t1']) as any
    const t2 = makeToolUseAssistantWithSiblings(['t2']) as any
    const siblings = new Set(['t1', 't2'])

    const waitingT2 = makeProgress('t2', siblings, 'Waiting…')
    const normalized1 = normalizeMessages([t1, t2, waitingT2] as any)
    expect(getUnresolvedToolUseIDs(normalized1)).toEqual(new Set(['t1', 't2']))
    expect(getInProgressToolUseIDs(normalized1)).toEqual(new Set(['t1']))

    const runningT2 = makeProgress('t2', siblings, 'Running…')
    const normalized2 = normalizeMessages([t1, t2, waitingT2, runningT2] as any)
    expect(getInProgressToolUseIDs(normalized2)).toEqual(new Set(['t1', 't2']))
  })

  test('Static prefix remains append-only across queued→running progress replacement', () => {
    const user = createUserMessage('hi')
    const toolUse = makeToolUseAssistantWithSiblings(['t1', 't2']) as any
    const siblings = new Set(['t1', 't2'])

    const runningT1 = makeProgress('t1', siblings, 'Running…')
    const waitingT2 = makeProgress('t2', siblings, 'Waiting…')
    const runningT2 = makeProgress('t2', siblings, 'Running…')

    const timeline: any[][] = [
      [user, toolUse],
      [user, toolUse, runningT1],
      [user, toolUse, runningT1, waitingT2],
      [user, toolUse, runningT1, waitingT2, makeToolResult('t1', 'done')],
      [
        user,
        toolUse,
        runningT1,
        waitingT2,
        makeToolResult('t1', 'done'),
        runningT2,
      ],
      [
        user,
        toolUse,
        runningT1,
        waitingT2,
        makeToolResult('t1', 'done'),
        runningT2,
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
})
