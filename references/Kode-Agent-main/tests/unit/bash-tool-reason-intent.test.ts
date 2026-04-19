import { describe, expect, test } from 'bun:test'
import { BashTool } from '@tools/BashTool/BashTool'

describe('BashTool schema (Reference CLI parity)', () => {
  test('rejects non-reference fields (reason/intent)', () => {
    expect(() =>
      BashTool.inputSchema.parse({ command: 'echo hi' }),
    ).not.toThrow()
    expect(() =>
      BashTool.inputSchema.parse({ command: 'echo hi', reason: 'Say hi' }),
    ).toThrow()
    expect(() =>
      BashTool.inputSchema.parse({ command: 'echo hi', intent: 'Say hi' }),
    ).toThrow()
  })

  test('renderToolUseMessage only includes description in verbose mode', () => {
    const input = { command: 'echo hi', description: 'Say hi' } as any
    expect(BashTool.renderToolUseMessage(input, { verbose: false })).toContain(
      'echo hi',
    )
    expect(BashTool.renderToolUseMessage(input, { verbose: true })).toContain(
      'Say hi',
    )
  })
})
