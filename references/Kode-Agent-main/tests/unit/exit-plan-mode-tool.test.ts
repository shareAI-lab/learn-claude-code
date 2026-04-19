import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { ExitPlanModeTool } from '@tools/agent/PlanModeTool/ExitPlanModeTool'
import {
  __resetPlanModeForTests,
  getPlanConversationKey,
  getPlanFilePath,
} from '@utils/plan/planMode'
import { __getExitPlanModePlanTextForTests } from '@tools/agent/PlanModeTool/ExitPlanModeTool'

const makeContext = () => ({
  abortController: new AbortController(),
  messageId: 'test',
  options: {
    commands: [],
    tools: [],
    verbose: false,
    safeMode: false,
    forkNumber: 0,
    messageLogName: 'exit-plan-mode',
    maxThinkingTokens: 0,
  },
  readFileTimestamps: {},
})

describe('ExitPlanModeTool', () => {
  let configDir = ''

  beforeEach(() => {
    configDir = mkdtempSync(join(tmpdir(), 'kode-test-config-'))
    process.env.KODE_CONFIG_DIR = configDir
    __resetPlanModeForTests()
  })

  afterEach(() => {
    if (configDir) {
      rmSync(configDir, { recursive: true, force: true })
      configDir = ''
    }
  })

  test('throws when no plan file exists', async () => {
    const ctx = makeContext()
    const conversationKey = getPlanConversationKey(ctx as any)
    const planFilePath = getPlanFilePath(undefined, conversationKey)

    if (existsSync(planFilePath)) {
      rmSync(planFilePath, { force: true })
    }

    const gen = ExitPlanModeTool.call({}, ctx as any)
    await expect(gen.next()).rejects.toThrow(
      `No plan file found at ${planFilePath}. Please write your plan to this file before calling ExitPlanMode.`,
    )
  })

  test('approved output includes filePath and plan content', async () => {
    const ctx = makeContext()
    const conversationKey = getPlanConversationKey(ctx as any)
    const planFilePath = getPlanFilePath(undefined, conversationKey)

    writeFileSync(planFilePath, '# Plan\n\n- Do the thing\n', 'utf-8')

    const gen = ExitPlanModeTool.call({}, ctx as any)
    const first = await gen.next()

    expect(first.done).toBe(false)
    if (first.done || !first.value) {
      throw new Error('Expected ExitPlanModeTool to yield a result')
    }
    expect(first.value.type).toBe('result')
    expect(first.value.data.filePath).toBe(planFilePath)
    expect(first.value.data.plan).toContain('Do the thing')
    expect(first.value.resultForAssistant).toContain(planFilePath)
  })

  test('rejection display reads and includes the plan file content', () => {
    const ctx = makeContext()
    const conversationKey = getPlanConversationKey(ctx as any)
    const planFilePath = getPlanFilePath(undefined, conversationKey)

    writeFileSync(planFilePath, '# Plan\n\n- Keep planning\n', 'utf-8')

    expect(__getExitPlanModePlanTextForTests(conversationKey)).toContain(
      'Keep planning',
    )
  })
})
