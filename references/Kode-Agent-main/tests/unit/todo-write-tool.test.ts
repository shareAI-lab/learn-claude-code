import { beforeEach, describe, expect, test } from 'bun:test'
import { TodoWriteTool } from '@tools/interaction/TodoWriteTool/TodoWriteTool'
import { getTodos, setTodos } from '@utils/session/todoStorage'

const makeContext = () => ({
  abortController: new AbortController(),
  messageId: 'test',
  readFileTimestamps: {},
})

async function runTodoWrite(input: any) {
  const gen = TodoWriteTool.call(input, makeContext() as any)
  const first = await gen.next()
  expect(first.done).toBe(false)
  if (first.done || !first.value) {
    throw new Error('Expected TodoWriteTool to yield a result')
  }
  expect(first.value.type).toBe('result')
  if (first.value.type !== 'result') {
    throw new Error(
      `Expected TodoWriteTool to yield result, got: ${first.value.type}`,
    )
  }
  return first.value
}

describe('TodoWriteTool', () => {
  beforeEach(() => {
    setTodos([])
  })

  test('schema rejects empty activeForm', () => {
    const result = TodoWriteTool.inputSchema.safeParse({
      todos: [
        {
          content: 'Write tests',
          status: 'pending',
          activeForm: '',
        },
      ],
    })

    expect(result.success).toBe(false)
    if (result.success) return

    expect(
      result.error.issues.some(
        issue =>
          issue.path.join('.') === 'todos.0.activeForm' &&
          issue.message === 'Active form cannot be empty',
      ),
    ).toBe(true)
  })

  test('validateInput rejects multiple in_progress', async () => {
    const result = await TodoWriteTool.validateInput?.({
      todos: [
        {
          content: 'Implement feature',
          status: 'in_progress',
          activeForm: 'Implementing feature',
        },
        {
          content: 'Write tests',
          status: 'in_progress',
          activeForm: 'Writing tests',
        },
      ],
    } as any)

    expect(result).toEqual({
      result: false,
      errorCode: 2,
      message: 'Only one task can be in_progress at a time',
      meta: { inProgressTasks: ['Implement feature', 'Write tests'] },
    })
  })

  test('call clears stored todos when all completed', async () => {
    await runTodoWrite({
      todos: [
        {
          content: 'First task',
          status: 'in_progress',
          activeForm: 'Working on first task',
        },
      ],
    })

    const result = await runTodoWrite({
      todos: [
        {
          content: 'First task',
          status: 'completed',
          activeForm: 'Working on first task',
        },
        {
          content: 'Second task',
          status: 'completed',
          activeForm: 'Working on second task',
        },
      ],
    })

    if (typeof result.data === 'string') {
      throw new Error(
        `Expected structured TodoWriteTool output, got string: ${result.data}`,
      )
    }

    expect(result.data.oldTodos).toEqual([
      {
        content: 'First task',
        status: 'in_progress',
        activeForm: 'Working on first task',
      },
    ])
    expect(result.data.newTodos).toEqual([
      {
        content: 'First task',
        status: 'completed',
        activeForm: 'Working on first task',
      },
      {
        content: 'Second task',
        status: 'completed',
        activeForm: 'Working on second task',
      },
    ])
    expect(getTodos()).toEqual([])
  })

  test('preserves input order and reuses ids for unchanged todos', async () => {
    await runTodoWrite({
      todos: [
        {
          content: 'Todo A',
          status: 'pending',
          activeForm: 'Doing todo A',
        },
        {
          content: 'Todo B',
          status: 'in_progress',
          activeForm: 'Doing todo B',
        },
      ],
    })

    const firstStored = getTodos()
    expect(firstStored.map(todo => todo.content)).toEqual(['Todo A', 'Todo B'])

    const idsByContent = new Map(
      firstStored.map(todo => [todo.content, todo.id]),
    )

    await runTodoWrite({
      todos: [
        {
          content: 'Todo B',
          status: 'in_progress',
          activeForm: 'Doing todo B',
        },
        {
          content: 'Todo A',
          status: 'pending',
          activeForm: 'Doing todo A',
        },
      ],
    })

    const secondStored = getTodos()
    expect(secondStored.map(todo => todo.content)).toEqual(['Todo B', 'Todo A'])
    expect(secondStored.map(todo => todo.id)).toEqual([
      idsByContent.get('Todo B'),
      idsByContent.get('Todo A'),
    ])
  })
})
