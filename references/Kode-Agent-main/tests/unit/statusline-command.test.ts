import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import statusline from '@commands/statusline'
import { SlashCommandTool } from '@tools/interaction/SlashCommandTool/SlashCommandTool'
import { clearAgentCache, getAgentByType } from '@utils/agent/loader'
import { setCwd } from '@utils/state'

describe('/statusline (prompt command + built-in agent)', () => {
  const runnerCwd = process.cwd()
  let projectDir: string

  beforeEach(async () => {
    clearAgentCache()
    projectDir = mkdtempSync(join(tmpdir(), 'kode-statusline-proj-'))
    await setCwd(projectDir)
  })

  afterEach(async () => {
    clearAgentCache()
    await setCwd(runnerCwd)
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('expands to Task(statusline-setup) instruction', async () => {
    expect((statusline as any).disableNonInteractive).toBe(true)

    const prompt = await (statusline as any).getPromptForCommand('hello')
    const text = (prompt?.[0] as any)?.content?.[0]?.text as string
    expect(text).toContain('subagent_type "statusline-setup"')
    expect(text).toContain('hello')
  })

  test('built-in agent statusline-setup is available', async () => {
    const agent = await getAgentByType('statusline-setup')
    expect(agent).toBeTruthy()
    expect(agent!.location).toBe('built-in')
  })

  test('SlashCommandTool blocks non-interactive /statusline', async () => {
    const ctx: any = {
      abortController: new AbortController(),
      messageId: 'm',
      readFileTimestamps: {},
      options: {
        commands: [statusline as any],
        tools: [],
        safeMode: false,
        forkNumber: 0,
        messageLogName: 'test',
        maxThinkingTokens: 0,
      },
    }

    const validation = await SlashCommandTool.validateInput(
      { command: '/statusline' } as any,
      ctx,
    )
    expect(validation.result).toBe(false)
    expect(validation.message).toContain('non-interactive')
  })
})
