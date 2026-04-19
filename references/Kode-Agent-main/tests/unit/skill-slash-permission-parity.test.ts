import { beforeEach, describe, expect, test } from 'bun:test'
import { homedir } from 'os'
import { join } from 'path'
import { hasPermissionsToUseTool } from '@permissions'
import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { SlashCommandTool } from '@tools/interaction/SlashCommandTool/SlashCommandTool'
import { SkillTool } from '@tools/ai/SkillTool/SkillTool'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'

const makeContext = (overrides?: any) => ({
  abortController: new AbortController(),
  messageId: 'test',
  options: {
    commands: [],
    tools: [],
    verbose: false,
    safeMode: false,
    forkNumber: 0,
    messageLogName: 'test',
    maxThinkingTokens: 0,
    model: 'main',
    ...(overrides?.options ?? {}),
  },
  readFileTimestamps: {},
  ...overrides,
})

beforeEach(() => {
  const cfg = getCurrentProjectConfig()
  saveCurrentProjectConfig({
    ...cfg,
    allowedTools: [],
    deniedTools: [],
    askedTools: [],
  } as any)
})

describe('Skill/SlashCommand parity: contextModifier effects', () => {
  test('SkillTool maps haiku/sonnet/opus to model pointers and sets maxThinkingTokens', async () => {
    const cmd = {
      type: 'prompt',
      name: 'pdf',
      disableModelInvocation: false,
      allowedTools: ['Read(~/**)'],
      model: 'haiku',
      maxThinkingTokens: 123,
      userFacingName() {
        return 'pdf'
      },
      async getPromptForCommand() {
        return [{ role: 'user', content: 'do something' }]
      },
    }

    const ctx = makeContext({ options: { commands: [cmd] } })
    const gen = SkillTool.call({ skill: 'pdf' } as any, ctx as any)
    const first = await gen.next()
    const firstValue = first.value as any
    expect(firstValue?.type).toBe('result')
    expect(firstValue?.contextModifier).toBeTruthy()
    const nextCtx = firstValue.contextModifier.modifyContext(ctx)
    expect(nextCtx.options.model).toBe('quick')
    expect(nextCtx.options.maxThinkingTokens).toBe(123)
    expect(nextCtx.options.commandAllowedTools).toContain('Read(~/**)')
  })

  test('SlashCommandTool sets model/maxThinkingTokens and accumulates allowed tools', async () => {
    const cmd = {
      type: 'prompt',
      name: 'review-pr',
      disableModelInvocation: false,
      allowedTools: ['Edit(~/.kode/settings.json)'],
      model: 'sonnet',
      maxThinkingTokens: 456,
      userFacingName() {
        return 'review-pr'
      },
      async getPromptForCommand() {
        return [{ role: 'user', content: 'expand' }]
      },
    }

    const ctx = makeContext({ options: { commands: [cmd] } })
    const gen = SlashCommandTool.call(
      { command: '/review-pr 123' } as any,
      ctx as any,
    )
    const first = await gen.next()
    const firstValue = first.value as any
    expect(firstValue?.type).toBe('result')
    const nextCtx = firstValue.contextModifier.modifyContext(ctx)
    expect(nextCtx.options.model).toBe('task')
    expect(nextCtx.options.maxThinkingTokens).toBe(456)
    expect(nextCtx.options.commandAllowedTools).toContain(
      'Edit(~/.kode/settings.json)',
    )
  })
})

describe('Permission parity: matching rule patterns + skill prefixes', () => {
  test('FileReadTool matches allowedTools path patterns (Read(~/**))', async () => {
    const cfg = getCurrentProjectConfig()
    cfg.allowedTools = ['Read(~/**)']
    saveCurrentProjectConfig(cfg)

    const filePath = join(homedir(), 'some-file.txt')
    const ctx = makeContext()
    const result = await hasPermissionsToUseTool(
      FileReadTool as any,
      { file_path: filePath },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(true)
  })

  test('FileEditTool matches allowedTools path patterns (Edit(~/**))', async () => {
    const cfg = getCurrentProjectConfig()
    cfg.allowedTools = ['Edit(~/**)']
    saveCurrentProjectConfig(cfg)

    const filePath = join(homedir(), 'some-file.txt')
    const ctx = makeContext()
    const result = await hasPermissionsToUseTool(
      FileEditTool as any,
      { file_path: filePath, old_string: 'a', new_string: 'b' },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(true)
  })

  test('SkillTool supports namespace prefix rules (Skill(ns:*))', async () => {
    const cfg = getCurrentProjectConfig()
    cfg.allowedTools = ['Skill(ms-office-suite:*)']
    saveCurrentProjectConfig(cfg)

    const ctx = makeContext()
    const result = await hasPermissionsToUseTool(
      SkillTool as any,
      { skill: 'ms-office-suite:pdf' },
      ctx as any,
      {} as any,
    )
    expect(result.result).toBe(true)
  })
})
