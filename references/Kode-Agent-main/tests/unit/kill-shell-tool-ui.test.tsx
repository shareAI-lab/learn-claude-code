import { expect, test } from 'bun:test'
import React from 'react'
import { PassThrough } from 'stream'
import stripAnsi from 'strip-ansi'
import { render } from 'ink'
import { KillShellTool } from '@tools/KillShellTool/KillShellTool'

test('KillShellTool UI strings match reference CLI (uW9/pW9)', async () => {
  expect(
    KillShellTool.renderToolUseMessage({ shell_id: 'abc123' } as any),
  ).toBe('Kill shell: abc123')

  const stdout = new PassThrough()
  ;(stdout as any).isTTY = true
  ;(stdout as any).columns = 80
  stdout.setEncoding('utf8')

  let raw = ''
  stdout.on('data', chunk => {
    raw += chunk.toString('utf8')
  })

  const instance = render(
    <>
      {KillShellTool.renderToolResultMessage({
        message: 'ok',
        shell_id: 'abc123',
      })}
    </>,
    { stdout: stdout as any, exitOnCtrlC: false },
  )

  await new Promise(resolve => setTimeout(resolve, 10))
  instance.unmount()

  const output = stripAnsi(raw)
  expect(output).toContain('Shell abc123 killed')
})
