import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { reloadCustomCommands } from '@services/customCommands'
import { SkillTool } from '@tools/ai/SkillTool/SkillTool'
import { setCwd } from '@utils/state'

describe('SkillTool prompt parity (official sections)', () => {
  const originalConfigDir = process.env.KODE_CONFIG_DIR
  const runnerCwd = process.cwd()

  let configDir: string
  let projectDir: string

  beforeEach(async () => {
    configDir = mkdtempSync(join(tmpdir(), 'kode-skilltool-prompt-cfg-'))
    projectDir = mkdtempSync(join(tmpdir(), 'kode-skilltool-prompt-proj-'))
    process.env.KODE_CONFIG_DIR = configDir
    await setCwd(projectDir)
  })

  test('includes slash-command-as-skill guidance and canonical examples', async () => {
    reloadCustomCommands()
    const prompt = await SkillTool.prompt()

    expect(prompt).toContain('Execute a skill within the main conversation')
    expect(prompt).toContain(
      'When users ask you to run a "slash command" or reference "/<something>"',
    )
    expect(prompt).toContain('<example>')
    expect(prompt).toContain('User: "run /commit"')
    expect(prompt).toContain(
      'Assistant: [Calls Skill tool with skill: "commit"]',
    )
    expect(prompt).toContain('`skill: "pdf"`')
    expect(prompt).toContain('`skill: "commit", args: "-m')
    expect(prompt).toContain('`skill: "review-pr", args: "123"`')
    expect(prompt).toContain('`skill: "ms-office-suite:pdf"`')
    expect(prompt).toContain('<available_skills>')
    expect(prompt).toContain('</available_skills>')
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    if (originalConfigDir === undefined) delete process.env.KODE_CONFIG_DIR
    else process.env.KODE_CONFIG_DIR = originalConfigDir
    rmSync(configDir, { recursive: true, force: true })
    rmSync(projectDir, { recursive: true, force: true })
  })
})
