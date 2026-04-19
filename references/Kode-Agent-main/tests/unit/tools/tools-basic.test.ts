import { afterEach, beforeEach, test, expect, describe } from 'bun:test'
import { getAllTools } from '@tools'
import {
  __resetPlanModeForTests,
  enterPlanMode,
  exitPlanMode,
  getPlanConversationKey,
  getPlanFilePath,
  isPlanModeEnabled,
  setActivePlanConversationKey,
} from '@utils/plan/planMode'
import { hasPermissionsToUseTool } from '@permissions'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { BashTool } from '@tools/BashTool/BashTool'
import { BunShell } from '@utils/bun/shell'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'

const makeContext = (safeMode = true) => ({
  abortController: new AbortController(),
  messageId: 'test',
  options: {
    commands: [],
    tools: [],
    verbose: false,
    slowAndCapableModel: undefined,
    safeMode,
    forkNumber: 0,
    messageLogName: 'test',
    maxThinkingTokens: 0,
  },
  readFileTimestamps: {},
})

let configDir = ''

beforeEach(() => {
  configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
  process.env.KODE_CONFIG_DIR = configDir
  BunShell.restart()
})

afterEach(() => {
  BunShell.restart()
  if (configDir) {
    rmSync(configDir, { recursive: true, force: true })
    configDir = ''
  }
})

describe('Tool registry', () => {
  test('includes core built-in tools', () => {
    const toolNames = getAllTools().map(t => t.name)
    expect(toolNames).toContain('Bash')
    expect(toolNames).toContain('WebFetch')
    expect(toolNames).toContain('WebSearch')
    expect(toolNames).toContain('AskUserQuestion')
    expect(toolNames).toContain('EnterPlanMode')
    expect(toolNames).toContain('ExitPlanMode')
    expect(toolNames).toContain('TaskOutput')
    expect(toolNames).toContain('KillShell')
  })
})

describe('Plan mode gating', () => {
  test('does not auto-deny write tool while in plan mode', async () => {
    __resetPlanModeForTests()
    const ctx = makeContext()
    setActivePlanConversationKey(getPlanConversationKey(ctx as any))
    enterPlanMode(ctx as any)
    expect(isPlanModeEnabled(ctx as any)).toBe(true)
    const result = await hasPermissionsToUseTool(
      FileWriteTool as any,
      { file_path: '/tmp/a', content: 'x' },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
    exitPlanMode(ctx as any)
  })

  test('allows read tool while in plan mode', async () => {
    __resetPlanModeForTests()
    const ctx = makeContext(false)
    setActivePlanConversationKey(getPlanConversationKey(ctx as any))
    enterPlanMode(ctx as any)
    const result = await hasPermissionsToUseTool(
      FileReadTool as any,
      { file_path: '/tmp/a' },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
    exitPlanMode(ctx as any)
  })

  test('allows writing the plan file while in plan mode', async () => {
    __resetPlanModeForTests()
    const ctx = makeContext()
    setActivePlanConversationKey(getPlanConversationKey(ctx as any))
    enterPlanMode(ctx as any)
    const planFilePath = getPlanFilePath(
      undefined,
      getPlanConversationKey(ctx as any),
    )
    const result = await hasPermissionsToUseTool(
      FileWriteTool as any,
      { file_path: planFilePath, content: '# Plan\n' },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(true)
    exitPlanMode(ctx as any)
  })

  test('allows writing agent plan files while in plan mode', async () => {
    __resetPlanModeForTests()
    const ctx = makeContext()
    const conversationKey = getPlanConversationKey(ctx as any)
    setActivePlanConversationKey(conversationKey)
    enterPlanMode(ctx as any)
    const agentPlanFilePath = getPlanFilePath('agent-1', conversationKey)
    const result = await hasPermissionsToUseTool(
      FileWriteTool as any,
      { file_path: agentPlanFilePath, content: '# Agent plan\n' },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(false)
    expect((result as any).shouldPromptUser).not.toBe(false)
    exitPlanMode(ctx as any)
  })
})

describe('Bash background execution', () => {
  test('executes background command and reports output', async () => {
    const { bashId } = BunShell.getInstance().execInBackground('echo hello')
    expect(bashId).toBeTruthy()
    expect(bashId).toMatch(/^b[0-9a-f]{6}$/i)
    await new Promise(resolve => setTimeout(resolve, 200))
    const output = BunShell.getInstance().getBackgroundOutput(bashId)
    expect(output).not.toBeNull()
    if (output) {
      expect(output.stdout.trim()).toBe('hello')
    }
  })

  test('readBackgroundOutput returns only new output', async () => {
    const { bashId } =
      BunShell.getInstance().execInBackground('printf "a\\nb\\n"')
    expect(bashId).toBeTruthy()
    expect(bashId).toMatch(/^b[0-9a-f]{6}$/i)
    await new Promise(resolve => setTimeout(resolve, 200))

    const first = BunShell.getInstance().readBackgroundOutput(bashId)
    expect(first).not.toBeNull()
    if (first) {
      expect(first.stdout).toContain('a')
      expect(first.stdout).toContain('b')
    }

    const second = BunShell.getInstance().readBackgroundOutput(bashId)
    expect(second).not.toBeNull()
    if (second) {
      expect(second.stdout).toBe('')
      expect(second.stderr).toBe('')
    }
  })
})
