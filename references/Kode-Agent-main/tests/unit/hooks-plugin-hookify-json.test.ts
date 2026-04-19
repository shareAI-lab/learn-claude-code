import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { dirname, join } from 'path'
import { z } from 'zod'
import type { Tool } from '@tool'
import { runToolUse } from '@query'
import { createAssistantMessage } from '@utils/messages'
import { setCwd } from '@utils/state'
import { __resetKodeHooksCacheForTests } from '@utils/session/kodeHooks'
import { __resetSessionPluginsForTests } from '@utils/session/sessionPlugins'
import { configureSessionPlugins } from '@services/pluginRuntime'

function writeJson(path: string, value: unknown) {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, JSON.stringify(value, null, 2) + '\n', 'utf8')
}

describe('Plugin hooks: hookify-style JSON outputs can block/allow', () => {
  const runnerCwd = process.cwd()

  let projectDir: string
  let pluginDir: string

  beforeEach(async () => {
    __resetKodeHooksCacheForTests()
    __resetSessionPluginsForTests()

    projectDir = mkdtempSync(join(tmpdir(), 'kode-hookify-json-project-'))
    await setCwd(projectDir)

    pluginDir = join(projectDir, 'hookify')
    mkdirSync(join(pluginDir, '.claude-plugin'), { recursive: true })
    writeFileSync(
      join(pluginDir, '.claude-plugin', 'plugin.json'),
      JSON.stringify({ name: 'hookify', version: '0.1.0' }, null, 2) + '\n',
      'utf8',
    )

    const hookScriptPath = join(pluginDir, 'pretooluse.js')
    writeFileSync(
      hookScriptPath,
      `
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let data = {};
try { data = JSON.parse(raw); } catch {}
if (data.hook_event_name !== 'PreToolUse') { console.error('BAD hook_event_name'); process.exit(2); }
const cmd = String(data?.tool_input?.command || '');
if (cmd.includes('rm -rf') || cmd.includes('danger')) {
  process.stdout.write(JSON.stringify({ hookSpecificOutput: { permissionDecision: 'deny', hookEventName: 'PreToolUse' }, systemMessage: 'HOOKIFY_BLOCKED' }));
  process.exit(0);
}
process.stdout.write(JSON.stringify({}));
process.exit(0);
`,
      'utf8',
    )

    writeJson(join(pluginDir, 'hooks', 'hooks.json'), {
      description: 'Hookify plugin - test fixture',
      hooks: {
        PreToolUse: [
          {
            hooks: [
              {
                type: 'command',
                command: 'bun \"${CLAUDE_PLUGIN_ROOT}/pretooluse.js\"',
                timeout: 10,
              },
            ],
          },
        ],
      },
    })

    await configureSessionPlugins({ pluginDirs: [pluginDir] })
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    __resetKodeHooksCacheForTests()
    __resetSessionPluginsForTests()
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('blocks tool execution when hook returns permissionDecision: deny', async () => {
    let called = false
    const fakeTool: Tool<any, any> = {
      name: 'FakeTool',
      inputSchema: z.strictObject({ command: z.string() }),
      async prompt() {
        return ''
      },
      async isEnabled() {
        return true
      },
      isReadOnly() {
        return false
      },
      isConcurrencySafe() {
        return true
      },
      needsPermissions() {
        return false
      },
      renderResultForAssistant() {
        return 'ok'
      },
      renderToolUseMessage() {
        return null
      },
      async *call() {
        called = true
        yield {
          type: 'result' as const,
          data: { ok: true },
          resultForAssistant: 'ok',
        }
      },
    }

    const toolUse: any = {
      type: 'tool_use',
      id: 'toolu_hookify_block',
      name: 'FakeTool',
      input: { command: 'rm -rf /' },
    }

    const ctx: any = {
      abortController: new AbortController(),
      readFileTimestamps: {},
      setToolJSX() {},
      messageId: 'm1',
      options: {
        tools: [fakeTool],
        commands: [],
        forkNumber: 0,
        messageLogName: 'test',
        verbose: false,
        safeMode: true,
        maxThinkingTokens: 0,
      },
    }

    const messages: any[] = []
    for await (const msg of runToolUse(
      toolUse,
      new Set([toolUse.id]),
      createAssistantMessage('') as any,
      async () => ({ result: true }),
      ctx,
      false,
    )) {
      messages.push(msg)
    }

    expect(called).toBe(false)
    expect(messages.length).toBe(1)
    expect(messages[0]?.type).toBe('user')
    expect(String(messages[0]?.message?.content?.[0]?.content)).toContain(
      'HOOKIFY_BLOCKED',
    )
  })

  test('allows tool execution when hook returns empty JSON', async () => {
    let called = false
    const fakeTool: Tool<any, any> = {
      name: 'FakeTool',
      inputSchema: z.strictObject({ command: z.string() }),
      async prompt() {
        return ''
      },
      async isEnabled() {
        return true
      },
      isReadOnly() {
        return false
      },
      isConcurrencySafe() {
        return true
      },
      needsPermissions() {
        return false
      },
      renderResultForAssistant() {
        return 'ok'
      },
      renderToolUseMessage() {
        return null
      },
      async *call() {
        called = true
        yield {
          type: 'result' as const,
          data: { ok: true },
          resultForAssistant: 'ok',
        }
      },
    }

    const toolUse: any = {
      type: 'tool_use',
      id: 'toolu_hookify_allow',
      name: 'FakeTool',
      input: { command: 'echo ok' },
    }

    const ctx: any = {
      abortController: new AbortController(),
      readFileTimestamps: {},
      setToolJSX() {},
      messageId: 'm1',
      options: {
        tools: [fakeTool],
        commands: [],
        forkNumber: 0,
        messageLogName: 'test',
        verbose: false,
        safeMode: true,
        maxThinkingTokens: 0,
      },
    }

    const messages: any[] = []
    for await (const msg of runToolUse(
      toolUse,
      new Set([toolUse.id]),
      createAssistantMessage('') as any,
      async () => ({ result: true }),
      ctx,
      false,
    )) {
      messages.push(msg)
    }

    expect(called).toBe(true)
    expect(
      messages.some(
        m =>
          m.type === 'user' &&
          Array.isArray(m.message?.content) &&
          m.message.content[0]?.type === 'tool_result' &&
          m.message.content[0]?.is_error !== true,
      ),
    ).toBe(true)
  })
})
