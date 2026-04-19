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

describe('Plugin hooks: PreToolUse command hooks (hooks/hooks.json)', () => {
  const runnerCwd = process.cwd()

  let projectDir: string
  let pluginDir: string

  beforeEach(async () => {
    __resetKodeHooksCacheForTests()
    __resetSessionPluginsForTests()

    projectDir = mkdtempSync(join(tmpdir(), 'kode-plugin-hooks-project-'))
    await setCwd(projectDir)

    pluginDir = join(projectDir, 'demo-plugin')
    mkdirSync(join(pluginDir, '.claude-plugin'), { recursive: true })
    writeFileSync(
      join(pluginDir, '.claude-plugin', 'plugin.json'),
      JSON.stringify({ name: 'demo-plugin', version: '0.1.0' }, null, 2) + '\n',
      'utf8',
    )

    const hookScriptPath = join(pluginDir, 'hook.js')
    writeFileSync(
      hookScriptPath,
      `
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let data = {};
try { data = JSON.parse(raw); } catch {}
if (!data.session_id) { console.error('MISSING session_id'); process.exit(2); }
if (!data.cwd) { console.error('MISSING cwd'); process.exit(2); }
if (!data.tool_use_id) { console.error('MISSING tool_use_id'); process.exit(2); }
if (data.hook_event_name !== 'PreToolUse') { console.error('BAD hook_event_name'); process.exit(2); }
if (data.tool_name !== 'FakeTool') { console.error('BAD tool_name'); process.exit(2); }
const cmd = data?.tool_input?.command || '';
if (String(cmd).includes('block')) { console.error('BLOCKED'); process.exit(2); }
if (String(cmd).includes('warn')) { console.error('WARN'); process.exit(1); }
process.exit(0);
`,
      'utf8',
    )

    writeJson(join(pluginDir, 'hooks', 'hooks.json'), {
      description: 'demo plugin hook',
      hooks: {
        PreToolUse: [
          {
            matcher: 'FakeTool|OtherTool',
            hooks: [
              {
                type: 'command',
                command: 'bun \"${CLAUDE_PLUGIN_ROOT}/hook.js\"',
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

  test('exit code 1 warns user-only and allows tool execution', async () => {
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
      id: 'toolu_warn',
      name: 'FakeTool',
      input: { command: 'warn' },
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
      true,
    )) {
      messages.push(msg)
    }

    expect(called).toBe(true)
    expect(
      messages.some(
        m =>
          m.type === 'progress' &&
          m.content?.message?.content?.[0]?.text?.includes('WARN'),
      ),
    ).toBe(true)
  })

  test('exit code 2 blocks tool execution and shows stderr to model', async () => {
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
      id: 'toolu_block',
      name: 'FakeTool',
      input: { command: 'block' },
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
      true,
    )) {
      messages.push(msg)
    }

    expect(called).toBe(false)
    expect(messages.length).toBe(1)
    expect(messages[0]?.type).toBe('user')
    expect(messages[0]?.message?.content?.[0]?.type).toBe('tool_result')
    expect(messages[0]?.message?.content?.[0]?.is_error).toBe(true)
    expect(String(messages[0]?.message?.content?.[0]?.content)).toContain(
      'BLOCKED',
    )
  })
})

describe('Plugin hooks: PreToolUse inline command hooks (plugin.json hooks field)', () => {
  const runnerCwd = process.cwd()

  let projectDir: string
  let pluginDir: string

  beforeEach(async () => {
    __resetKodeHooksCacheForTests()
    __resetSessionPluginsForTests()

    projectDir = mkdtempSync(
      join(tmpdir(), 'kode-plugin-hooks-inline-project-'),
    )
    await setCwd(projectDir)

    pluginDir = join(projectDir, 'demo-plugin-inline')
    mkdirSync(join(pluginDir, '.claude-plugin'), { recursive: true })

    const hookScriptPath = join(pluginDir, 'hook.js')
    writeFileSync(
      hookScriptPath,
      `
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let data = {};
try { data = JSON.parse(raw); } catch {}
if (!data.session_id) { console.error('MISSING session_id'); process.exit(2); }
if (!data.cwd) { console.error('MISSING cwd'); process.exit(2); }
if (!data.tool_use_id) { console.error('MISSING tool_use_id'); process.exit(2); }
if (data.hook_event_name !== 'PreToolUse') { console.error('BAD hook_event_name'); process.exit(2); }
if (data.tool_name !== 'FakeTool') { console.error('BAD tool_name'); process.exit(2); }
const cmd = data?.tool_input?.command || '';
if (String(cmd).includes('block')) { console.error('BLOCKED'); process.exit(2); }
if (String(cmd).includes('warn')) { console.error('WARN'); process.exit(1); }
process.exit(0);
`,
      'utf8',
    )

    writeFileSync(
      join(pluginDir, '.claude-plugin', 'plugin.json'),
      JSON.stringify(
        {
          name: 'demo-plugin-inline',
          version: '0.1.0',
          hooks: {
            PreToolUse: [
              {
                matcher: 'FakeTool|OtherTool',
                hooks: [
                  {
                    type: 'command',
                    command: 'bun \"${CLAUDE_PLUGIN_ROOT}/hook.js\"',
                  },
                ],
              },
            ],
          },
        },
        null,
        2,
      ) + '\n',
      'utf8',
    )

    await configureSessionPlugins({ pluginDirs: [pluginDir] })
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    __resetKodeHooksCacheForTests()
    __resetSessionPluginsForTests()
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('exit code 1 warns user-only and allows tool execution', async () => {
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
      id: 'toolu_warn_inline',
      name: 'FakeTool',
      input: { command: 'warn' },
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
      true,
    )) {
      messages.push(msg)
    }

    expect(called).toBe(true)
    expect(
      messages.some(
        m =>
          m.type === 'progress' &&
          m.content?.message?.content?.[0]?.text?.includes('WARN'),
      ),
    ).toBe(true)
  })

  test('exit code 2 blocks tool execution and shows stderr to model', async () => {
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
      id: 'toolu_block_inline',
      name: 'FakeTool',
      input: { command: 'block' },
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
      true,
    )) {
      messages.push(msg)
    }

    expect(called).toBe(false)
    expect(messages.length).toBe(1)
    expect(messages[0]?.type).toBe('user')
    expect(messages[0]?.message?.content?.[0]?.type).toBe('tool_result')
    expect(messages[0]?.message?.content?.[0]?.is_error).toBe(true)
    expect(String(messages[0]?.message?.content?.[0]?.content)).toContain(
      'BLOCKED',
    )
  })
})
