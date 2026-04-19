import { describe, expect, test } from 'bun:test'
import {
  isPackagedRuntime,
  maybeTruncateVerboseToolOutput,
  truncateTextForDisplay,
} from '@utils/tooling/toolOutputDisplay'

async function withEnv<T>(
  updates: Record<string, string | undefined>,
  fn: () => Promise<T> | T,
): Promise<T> {
  const previous: Record<string, string | undefined> = {}
  for (const [k, v] of Object.entries(updates)) {
    previous[k] = process.env[k]
    if (v === undefined) delete process.env[k]
    else process.env[k] = v
  }
  try {
    return await fn()
  } finally {
    for (const [k, v] of Object.entries(previous)) {
      if (v === undefined) delete process.env[k]
      else process.env[k] = v
    }
  }
}

async function withExecPath<T>(
  execPath: string,
  fn: () => Promise<T> | T,
): Promise<T> {
  const previous = process.execPath
  ;(process as any).execPath = execPath
  try {
    return await fn()
  } finally {
    ;(process as any).execPath = previous
  }
}

describe('toolOutputDisplay', () => {
  test('isPackagedRuntime: KODE_PACKAGED=1 forces true', async () => {
    await withEnv({ KODE_PACKAGED: '1' }, async () => {
      await withExecPath('/usr/local/bin/bun', () => {
        expect(isPackagedRuntime()).toBe(true)
      })
    })
  })

  test('isPackagedRuntime: heuristic treats bun/node as not packaged', async () => {
    await withEnv({ KODE_PACKAGED: undefined }, async () => {
      await withExecPath('/usr/local/bin/bun', () => {
        expect(isPackagedRuntime()).toBe(false)
      })
      await withExecPath('/usr/local/bin/node', () => {
        expect(isPackagedRuntime()).toBe(false)
      })
      await withExecPath('C:\\\\Program Files\\\\nodejs\\\\node.exe', () => {
        expect(isPackagedRuntime()).toBe(false)
      })
    })
  })

  test('isPackagedRuntime: heuristic treats other execPath as packaged', async () => {
    await withEnv({ KODE_PACKAGED: undefined }, async () => {
      await withExecPath('/usr/local/bin/kode', () => {
        expect(isPackagedRuntime()).toBe(true)
      })
      await withExecPath('C:\\\\kode\\\\kode.exe', () => {
        expect(isPackagedRuntime()).toBe(true)
      })
    })
  })

  test('isPackagedRuntime: empty execPath returns false', async () => {
    await withEnv({ KODE_PACKAGED: undefined }, async () => {
      await withExecPath('', () => {
        expect(isPackagedRuntime()).toBe(false)
      })
    })
  })

  test('isPackagedRuntime: handles execPath getter throwing', async () => {
    await withEnv({ KODE_PACKAGED: undefined }, async () => {
      const original = Object.getOwnPropertyDescriptor(process, 'execPath')
      try {
        Object.defineProperty(process, 'execPath', {
          configurable: true,
          enumerable: true,
          get() {
            throw new Error('boom')
          },
        })
        expect(isPackagedRuntime()).toBe(false)
      } finally {
        if (original) Object.defineProperty(process, 'execPath', original)
      }
    })
  })

  test('truncateTextForDisplay: no truncation', () => {
    const res = truncateTextForDisplay('a\nb\nc', {
      maxLines: 10,
      maxChars: 100,
    })
    expect(res.truncated).toBe(false)
    expect(res.omittedLines).toBe(0)
    expect(res.omittedChars).toBe(0)
    expect(res.text).toBe('a\nb\nc')
  })

  test('truncateTextForDisplay: truncates by lines', () => {
    const text = ['l1', 'l2', 'l3', 'l4', 'l5'].join('\n')
    const res = truncateTextForDisplay(text, { maxLines: 3, maxChars: 10_000 })
    expect(res.truncated).toBe(true)
    expect(res.omittedLines).toBe(2)
    expect(res.omittedChars).toBe(0)
    expect(res.text).toContain('... [truncated 2 lines] ...')
    expect(res.text.startsWith(['l1', 'l2', 'l3'].join('\n'))).toBe(true)
  })

  test('truncateTextForDisplay: truncates by chars', () => {
    const text = '0123456789ABCDEFG'
    const res = truncateTextForDisplay(text, { maxLines: 10_000, maxChars: 10 })
    expect(res.truncated).toBe(true)
    expect(res.omittedLines).toBe(0)
    expect(res.omittedChars).toBe(7)
    expect(res.text.startsWith('0123456789')).toBe(true)
    expect(res.text).toContain('... [truncated 7 chars] ...')
  })

  test('truncateTextForDisplay: truncates by lines then chars', () => {
    const text = ['abcdefghij', 'klmnopqrst', 'uvwxyzABCD', 'EFGHIJKLMN'].join(
      '\n',
    )
    const res = truncateTextForDisplay(text, { maxLines: 3, maxChars: 15 })
    expect(res.truncated).toBe(true)
    expect(res.omittedLines).toBe(1)
    expect(res.omittedChars).toBe(17)
    expect(res.text).toContain('... [truncated 1 lines · 17 chars] ...')
  })

  test('maybeTruncateVerboseToolOutput: does not truncate when not packaged', async () => {
    const longText = Array.from({ length: 200 }, (_, i) => `L${i + 1}`).join(
      '\n',
    )
    await withEnv({ KODE_PACKAGED: undefined }, async () => {
      await withExecPath('/usr/local/bin/bun', () => {
        const out = maybeTruncateVerboseToolOutput(longText)
        expect(out.truncated).toBe(false)
        expect(out.text).toBe(longText)
      })
    })
  })

  test('maybeTruncateVerboseToolOutput: truncates in packaged runtime', async () => {
    const longText = Array.from({ length: 200 }, (_, i) => `L${i + 1}`).join(
      '\n',
    )
    await withEnv(
      { KODE_PACKAGED: '1', KODE_TOOL_OUTPUT_FULL: undefined },
      () => {
        const out = maybeTruncateVerboseToolOutput(longText)
        expect(out.truncated).toBe(true)
        expect(out.text).toContain('[truncated')
      },
    )
  })

  test('maybeTruncateVerboseToolOutput: KODE_TOOL_OUTPUT_FULL disables truncation', async () => {
    const longText = Array.from({ length: 200 }, (_, i) => `L${i + 1}`).join(
      '\n',
    )
    await withEnv({ KODE_PACKAGED: '1', KODE_TOOL_OUTPUT_FULL: '1' }, () => {
      const out = maybeTruncateVerboseToolOutput(longText)
      expect(out.truncated).toBe(false)
      expect(out.text).toBe(longText)
    })
  })

  test('maybeTruncateVerboseToolOutput: env overrides max lines/chars', async () => {
    const longText = ['a', 'b', 'c', 'd'].join('\n')
    await withEnv(
      {
        KODE_PACKAGED: '1',
        KODE_TOOL_OUTPUT_FULL: undefined,
        KODE_TOOL_OUTPUT_MAX_LINES: '2',
        KODE_TOOL_OUTPUT_MAX_CHARS: '3',
      },
      () => {
        const out = maybeTruncateVerboseToolOutput(longText)
        expect(out.truncated).toBe(true)
        expect(out.text).toContain('[truncated')
      },
    )
  })

  test('maybeTruncateVerboseToolOutput: invalid env overrides are ignored', async () => {
    const longText = ['a', 'b', 'c', 'd'].join('\n')
    await withEnv(
      {
        KODE_PACKAGED: '1',
        KODE_TOOL_OUTPUT_FULL: undefined,
        KODE_TOOL_OUTPUT_MAX_LINES: 'not-a-number',
        KODE_TOOL_OUTPUT_MAX_CHARS: 'not-a-number',
      },
      () => {
        const out = maybeTruncateVerboseToolOutput(longText, {
          maxLines: 2,
          maxChars: 10_000,
        })
        expect(out.truncated).toBe(true)
        expect(out.text).toContain('truncated 2 lines')
      },
    )
  })
})
