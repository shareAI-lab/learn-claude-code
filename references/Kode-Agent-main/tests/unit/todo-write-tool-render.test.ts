import { describe, expect, test } from 'bun:test'
import { __getTodoRenderModelForTests } from '@tools/interaction/TodoWriteTool/TodoWriteTool'

describe('TodoWriteTool.renderToolResultMessage (render model)', () => {
  test('empty list shows reference CLI empty message', () => {
    expect(__getTodoRenderModelForTests([] as any)).toEqual({
      kind: 'empty',
      message: 'No todos currently tracked',
    })
  })

  test('in_progress is bold with unchecked box', () => {
    const model = __getTodoRenderModelForTests([
      {
        id: '1',
        content: 'Write unit tests',
        status: 'in_progress',
        activeForm: 'Writing unit tests',
        priority: 'medium',
      },
    ] as any)

    expect(model).toEqual({
      kind: 'list',
      items: [
        {
          checkbox: '☐',
          checkboxDim: false,
          content: 'Write unit tests',
          contentBold: true,
          contentDim: false,
          contentStrikethrough: false,
        },
      ],
    })
  })

  test('pending items are unchecked and not bold', () => {
    const model = __getTodoRenderModelForTests([
      {
        id: '1',
        content: 'First pending',
        status: 'pending',
        activeForm: 'Working on first pending',
        priority: 'medium',
      },
      {
        id: '2',
        content: 'Second pending',
        status: 'pending',
        activeForm: 'Working on second pending',
        priority: 'medium',
      },
    ] as any)

    expect(model).toEqual({
      kind: 'list',
      items: [
        {
          checkbox: '☐',
          checkboxDim: false,
          content: 'First pending',
          contentBold: false,
          contentDim: false,
          contentStrikethrough: false,
        },
        {
          checkbox: '☐',
          checkboxDim: false,
          content: 'Second pending',
          contentBold: false,
          contentDim: false,
          contentStrikethrough: false,
        },
      ],
    })
  })

  test('completed items are checked, dim, and strikethrough', () => {
    const model = __getTodoRenderModelForTests([
      {
        id: '1',
        content: 'Finished task',
        status: 'completed',
        activeForm: 'Finishing task',
        priority: 'medium',
      },
    ] as any)

    expect(model).toEqual({
      kind: 'list',
      items: [
        {
          checkbox: '☒',
          checkboxDim: true,
          content: 'Finished task',
          contentBold: false,
          contentDim: true,
          contentStrikethrough: true,
        },
      ],
    })
  })
})
