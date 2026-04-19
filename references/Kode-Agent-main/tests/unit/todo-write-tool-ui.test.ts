import { describe, expect, test } from 'bun:test'
import { TodoWriteTool } from '@tools/interaction/TodoWriteTool/TodoWriteTool'

const makeContext = () => ({
  abortController: new AbortController(),
  messageId: 'test',
  readFileTimestamps: {},
})

describe('TodoWriteTool UI parity (Reference CLI)', () => {
  test('renderToolUseMessage returns null (suppressed tool-use line)', () => {
    const msg = TodoWriteTool.renderToolUseMessage(
      {
        todos: [
          {
            content: 'Task',
            status: 'pending',
            activeForm: 'Doing task',
          },
        ],
      } as any,
      { verbose: false },
    )
    expect(msg).toBeNull()
  })

  test('renderToolResultMessage returns null (TodoWrite does not print todo list by default)', () => {
    const node = TodoWriteTool.renderToolResultMessage?.(
      {
        oldTodos: [],
        newTodos: [],
        agentId: undefined,
      } as any,
      { verbose: false },
    )
    expect(node).toBeNull()
  })

  test('call throws on storage failures so query can emit tool_result.is_error=true', async () => {
    const tooManyTodos = Array.from({ length: 101 }, (_, i) => ({
      content: `Todo ${i}`,
      status: 'pending',
      activeForm: `Doing todo ${i}`,
    }))

    const gen = TodoWriteTool.call(
      { todos: tooManyTodos } as any,
      makeContext() as any,
    )
    await expect(gen.next()).rejects.toThrow('Todo limit exceeded')
  })
})
