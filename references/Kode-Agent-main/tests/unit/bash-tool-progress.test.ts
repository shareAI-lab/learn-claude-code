import { describe, expect, test } from 'bun:test'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { BashTool } from '@tools/BashTool/BashTool'

function makeContext(): any {
  return {
    abortController: new AbortController(),
    messageId: 'test',
    safeMode: false,
    options: {
      safeMode: false,
      verbose: false,
      tools: [],
      commands: [],
      forkNumber: 0,
      messageLogName: 'bash-tool-progress-test',
      maxThinkingTokens: 0,
      bashLlmGateQuery: async () => {
        return 'ALLOW'
      },
    },
    readFileTimestamps: {},
  }
}

describe('BashTool progress parity (Reference CLI gH5)', () => {
  test('yields progress for long-running commands and then yields final result', async () => {
    const configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
    process.env.KODE_CONFIG_DIR = configDir
    try {
      const ctx = makeContext()
      const gen = BashTool.call(
        {
          command: 'echo a; sleep 3; echo b',
          description: 'Produce output with a delay',
          timeout: 10_000,
        },
        ctx,
      )

      const events: any[] = []
      for await (const ev of gen) events.push(ev)

      const progress = events.filter(e => e.type === 'progress')
      const results = events.filter(e => e.type === 'result')

      expect(progress.length).toBeGreaterThan(0)
      expect(results).toHaveLength(1)

      const progressText: string =
        progress[0]?.content?.message?.content?.[0]?.text ?? ''
      expect(progressText).toContain('<tool-progress>')
    } finally {
      rmSync(configDir, { recursive: true, force: true })
    }
  })

  test('abort still produces a final tool result (interrupted=true)', async () => {
    const configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
    process.env.KODE_CONFIG_DIR = configDir
    try {
      const ctx = makeContext()
      const gen = BashTool.call(
        {
          command: 'echo a; sleep 10',
          description: 'Test abort handling',
          timeout: 60_000,
        },
        ctx,
      )

      const events: any[] = []
      for await (const ev of gen) {
        events.push(ev)
        if (ev.type === 'progress') {
          ctx.abortController.abort()
        }
      }

      const result = events.find(e => e.type === 'result')
      expect(result).toBeTruthy()
      expect(result.data.interrupted).toBe(true)
    } finally {
      rmSync(configDir, { recursive: true, force: true })
    }
  })
})
