import { describe, expect, test } from 'bun:test'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { BashTool } from '@tools/BashTool/BashTool'
import { BunShell } from '@utils/bun/shell'

function makeContext(overrides?: Partial<any>): any {
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
      messageLogName: 'bash-tool-ctrl-b-test',
      maxThinkingTokens: 0,
      bashLlmGateQuery: async () => {
        return 'ALLOW'
      },
    },
    readFileTimestamps: {},
    ...overrides,
  }
}

describe('BashTool ctrl+b backgrounding parity (Reference CLI K41 + gH5)', () => {
  test('shows ctrl+b hint after the initial delay', async () => {
    if (process.platform === 'win32') return
    const configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
    process.env.KODE_CONFIG_DIR = configDir
    try {
      BunShell.restart()

      const toolJSXCalls: Array<{ at: number; value: any }> = []
      const startedAt = Date.now()
      const ctx = makeContext({
        setToolJSX: (value: any) => {
          toolJSXCalls.push({ at: Date.now(), value })
        },
      })

      const gen = BashTool.call(
        { command: 'sleep 3', description: 'Wait briefly', timeout: 10_000 },
        ctx,
      )
      for await (const _ev of gen) {
      }

      const firstNonNull = toolJSXCalls.find(c => c.value !== null)
      expect(firstNonNull).toBeTruthy()
      expect(firstNonNull!.value.shouldHidePromptInput).toBe(false)
      expect(firstNonNull!.at - startedAt).toBeGreaterThanOrEqual(1800)
    } finally {
      BunShell.restart()
      rmSync(configDir, { recursive: true, force: true })
    }
  })

  test('can request background and returns a background id', async () => {
    if (process.platform === 'win32') return
    const configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
    process.env.KODE_CONFIG_DIR = configDir
    try {
      BunShell.restart()

      let triggered = false
      const ctx = makeContext({
        setToolJSX: (value: any) => {
          if (triggered) return
          if (!value || !value.jsx) return
          const jsx: any = value.jsx
          const onBackground = jsx?.props?.onBackground
          if (typeof onBackground !== 'function') return
          triggered = true
          setTimeout(() => onBackground(), 0)
        },
      })

      const gen = BashTool.call(
        {
          command:
            'i=0; while [ $i -lt 30 ]; do i=$((i+1)); echo "tick-$i"; sleep 0.1; done',
          description: 'Emit progress ticks',
          timeout: 30_000,
        },
        ctx,
      )

      const events: any[] = []
      for await (const ev of gen) events.push(ev)

      const result = events.find(e => e.type === 'result')
      expect(result).toBeTruthy()
      expect(result.data.bashId).toBeTruthy()
      expect(result.data.backgroundTaskId).toBe(result.data.bashId)

      const bashId = result.data.bashId as string
      await new Promise(resolve => setTimeout(resolve, 120))
      const first = BunShell.getInstance().readBackgroundOutput(bashId)
      expect(first).not.toBeNull()
      expect(first?.stdout).not.toBe('')

      await new Promise(resolve => setTimeout(resolve, 250))
      const second = BunShell.getInstance().readBackgroundOutput(bashId)
      expect(second).not.toBeNull()
      expect(second?.stdout).not.toBe('')

      await new Promise(resolve => setTimeout(resolve, 1200))
      const final = BunShell.getInstance().getBackgroundOutput(bashId)
      expect(final).not.toBeNull()
      expect(final?.code).toBe(0)
    } finally {
      BunShell.restart()
      rmSync(configDir, { recursive: true, force: true })
    }
  })

  test('foreground execution still works when not backgrounded', async () => {
    const configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
    process.env.KODE_CONFIG_DIR = configDir
    try {
      BunShell.restart()
      const ctx = makeContext()

      const events: any[] = []
      for await (const ev of BashTool.call(
        { command: 'echo hello', description: 'Print greeting', timeout: 10_000 },
        ctx,
      )) {
        events.push(ev)
      }

      const result = events.find(e => e.type === 'result')
      expect(result).toBeTruthy()
      expect(result.data.bashId).toBeUndefined()
      expect(result.data.backgroundTaskId).toBeUndefined()
    } finally {
      BunShell.restart()
      rmSync(configDir, { recursive: true, force: true })
    }
  })
})
