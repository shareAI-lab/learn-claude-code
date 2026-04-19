import { beforeEach, describe, expect, test } from 'bun:test'
import { Box, render } from 'ink'
import React from 'react'
import { PassThrough } from 'stream'
import stripAnsi from 'strip-ansi'
import { TodosViewForTests } from '@commands/todos'
import { setTodos } from '@utils/session/todoStorage'

async function renderToText(element: React.ReactElement): Promise<string> {
  const stdin = new PassThrough()
  ;(stdin as any).isTTY = true
  ;(stdin as any).isRaw = true
  ;(stdin as any).setRawMode = () => {}
  stdin.setEncoding('utf8')
  stdin.resume()

  const stdout = new PassThrough()
  ;(stdout as any).isTTY = true
  ;(stdout as any).columns = 100
  ;(stdout as any).rows = 30

  let rawOutput = ''
  stdout.on('data', chunk => {
    rawOutput += chunk.toString('utf8')
  })

  const instance = render(<Box>{element}</Box>, {
    stdin: stdin as any,
    stdout: stdout as any,
    exitOnCtrlC: false,
  })

  await new Promise(resolve => setTimeout(resolve, 0))
  instance.unmount()

  return stripAnsi(rawOutput)
}

describe('/todos command (Claude zE9 parity)', () => {
  beforeEach(() => {
    setTodos([])
  })

  test('empty list prints Claude empty message', async () => {
    const out = await renderToText(
      <TodosViewForTests agentId={undefined} onClose={() => {}} />,
    )

    expect(out).toContain('No todos currently tracked')
  })

  test('non-empty list prints count header and checkbox list', async () => {
    setTodos([
      {
        id: '1',
        content: 'Pending task',
        status: 'pending',
        activeForm: 'Working on pending task',
        priority: 'medium',
      },
      {
        id: '2',
        content: 'Completed task',
        status: 'completed',
        activeForm: 'Completing task',
        priority: 'medium',
      },
    ])

    const out = await renderToText(
      <TodosViewForTests agentId={undefined} onClose={() => {}} />,
    )

    expect(out).toContain('2 todos:')
    expect(out).toContain('☐ Pending task')
    expect(out).toContain('☒ Completed task')
  })
})
