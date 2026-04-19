import { describe, expect, test } from 'bun:test'
import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

type JsonRpcMessage = {
  jsonrpc?: string
  id?: string | number | null
  method?: string
  params?: any
  result?: any
  error?: any
}

function createAcpHarness(options: { configDir: string }) {
  const repoRoot = process.cwd()
  const configDir = options.configDir

  const proc = spawn('bun', ['src/entrypoints/acp.ts'], {
    cwd: repoRoot,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      ...process.env,
      NODE_ENV: 'test',
      KODE_CONFIG_DIR: configDir,
      KODE_ACP_ECHO: '1',
    },
  })

  const stdoutBuffer: string[] = []
  const stderrChunks: string[] = []
  const messages: JsonRpcMessage[] = []

  let stdoutPartial = ''
  let waiters: Array<() => void> = []

  const notify = () => {
    const current = waiters
    waiters = []
    for (const w of current) w()
  }

  proc.stdout?.on('data', chunk => {
    const text = chunk.toString('utf8')
    stdoutBuffer.push(text)
    stdoutPartial += text
    while (true) {
      const idx = stdoutPartial.indexOf('\n')
      if (idx < 0) break
      const line = stdoutPartial.slice(0, idx).trim()
      stdoutPartial = stdoutPartial.slice(idx + 1)
      if (!line) continue
      try {
        messages.push(JSON.parse(line))
        notify()
      } catch {
      }
    }
  })

  proc.stderr?.on('data', chunk => {
    stderrChunks.push(chunk.toString('utf8'))
  })

  const send = (msg: JsonRpcMessage) => {
    proc.stdin?.write(`${JSON.stringify(msg)}\n`)
  }

  const waitFor = async (predicate: (msg: JsonRpcMessage) => boolean, timeoutMs: number) => {
    const deadline = Date.now() + timeoutMs
    while (true) {
      const idx = messages.findIndex(predicate)
      if (idx >= 0) {
        return messages.splice(idx, 1)[0]!
      }
      const remaining = deadline - Date.now()
      if (remaining <= 0) {
        throw new Error(
          `ACP waitFor timeout after ${timeoutMs}ms\n\nstderr:\n${stderrChunks.join('')}\n\nstdout:\n${stdoutBuffer.join('')}`,
        )
      }
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => {
          cleanup()
          reject(new Error('timeout'))
        }, remaining)
        const cleanup = () => {
          clearTimeout(timer)
          waiters = waiters.filter(w => w !== resolve)
        }
        waiters.push(resolve)
      })
    }
  }

  const stop = async () => {
    try {
      proc.stdin?.end()
    } catch {}
    try {
      proc.kill('SIGTERM')
    } catch {}
  }

  return { proc, send, waitFor, stop }
}

describe('ACP (toad-style smoke)', () => {
  test('initialize → session/new → session/prompt (echo) → restart → session/load replays', async () => {
    const repoRoot = process.cwd()
    const cwd = repoRoot
    const configDir = mkdtempSync(join(tmpdir(), 'kode-acp-test-'))

    let sessionId = ''
    try {
      const acp1 = createAcpHarness({ configDir })
      try {
        acp1.send({
          jsonrpc: '2.0',
          id: 1,
          method: 'initialize',
          params: {
            protocolVersion: 1,
            clientCapabilities: {
              terminal: true,
              fs: { readTextFile: true, writeTextFile: true },
            },
            clientInfo: { name: 'toad', title: 'Toad', version: '0.5.2' },
          },
        })

        const initRes = await acp1.waitFor(m => m.id === 1, 5_000)
        expect(initRes.result.protocolVersion).toBe(1)
        expect(initRes.result.agentCapabilities.loadSession).toBe(true)
        expect(initRes.result.agentCapabilities.promptCapabilities.embeddedContent).toBe(true)
        expect(initRes.result.agentCapabilities.promptCapabilities.embeddedContext).toBe(true)

        acp1.send({
          jsonrpc: '2.0',
          id: 2,
          method: 'session/new',
          params: { cwd, mcpServers: [] },
        })

        const newRes = await acp1.waitFor(m => m.id === 2, 15_000)
        sessionId = newRes.result.sessionId
        expect(typeof sessionId).toBe('string')

        const commandsUpdate = await acp1.waitFor(
          m =>
            m.method === 'session/update' &&
            m.params?.sessionId === sessionId &&
            m.params?.update?.sessionUpdate === 'available_commands_update',
          15_000,
        )
        expect(Array.isArray(commandsUpdate.params.update.availableCommands)).toBe(true)

        const modeUpdate = await acp1.waitFor(
          m =>
            m.method === 'session/update' &&
            m.params?.sessionId === sessionId &&
            m.params?.update?.sessionUpdate === 'current_mode_update',
          15_000,
        )
        expect(typeof modeUpdate.params.update.currentModeId).toBe('string')

        acp1.send({
          jsonrpc: '2.0',
          id: 3,
          method: 'session/prompt',
          params: { sessionId, prompt: [{ type: 'text', text: 'hello' }] },
        })

        const echoUpdate = await acp1.waitFor(
          m =>
            m.method === 'session/update' &&
            m.params?.sessionId === sessionId &&
            m.params?.update?.sessionUpdate === 'agent_message_chunk',
          15_000,
        )
        expect(echoUpdate.params.update.content.text).toContain('hello')

        const promptRes = await acp1.waitFor(m => m.id === 3, 15_000)
        expect(promptRes.result.stopReason).toBe('end_turn')
      } finally {
        await acp1.stop()
      }

      const acp2 = createAcpHarness({ configDir })
      try {
        acp2.send({
          jsonrpc: '2.0',
          id: 1,
          method: 'initialize',
          params: {
            protocolVersion: 1,
            clientCapabilities: {
              terminal: true,
              fs: { readTextFile: true, writeTextFile: true },
            },
            clientInfo: { name: 'toad', title: 'Toad', version: '0.5.2' },
          },
        })

        await acp2.waitFor(m => m.id === 1, 5_000)

        acp2.send({
          jsonrpc: '2.0',
          id: 2,
          method: 'session/load',
          params: { sessionId, cwd, mcpServers: [] },
        })

        const replayed = await acp2.waitFor(
          m =>
            m.method === 'session/update' &&
            m.params?.sessionId === sessionId &&
            m.params?.update?.sessionUpdate === 'agent_message_chunk' &&
            String(m.params?.update?.content?.text ?? '').includes('hello'),
          15_000,
        )
        expect(replayed.params.update.content.text).toContain('hello')

        const loadRes = await acp2.waitFor(m => m.id === 2, 15_000)
        expect(loadRes.result.modes).toBeDefined()
      } finally {
        await acp2.stop()
      }
    } finally {
      rmSync(configDir, { recursive: true, force: true })
    }
  })
})
