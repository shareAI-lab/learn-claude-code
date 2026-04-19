import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import {
  loadCustomCommands,
  reloadCustomCommands,
} from '@services/customCommands'
import { SkillTool } from '@tools/ai/SkillTool/SkillTool'
import { setCwd } from '@utils/state'

async function withEnv<T>(
  updates: Record<string, string | undefined>,
  fn: () => Promise<T> | T,
): Promise<T> {
  const previous: Record<string, string | undefined> = {}
  for (const [k, v] of Object.entries(updates)) {
    previous[k] = process.env[k]
    if (v === undefined) delete process.env[k]
    else process.env[k] = v
  }
  try {
    return await fn()
  } finally {
    for (const [k, v] of Object.entries(previous)) {
      if (v === undefined) delete process.env[k]
      else process.env[k] = v
    }
  }
}

describe('Agent Skills compatibility (discovery + prompt)', () => {
  const runnerCwd = process.cwd()

  let projectDir: string
  let homeDir: string

  beforeEach(async () => {
    projectDir = mkdtempSync(join(tmpdir(), 'kode-skill-proj-'))
    homeDir = mkdtempSync(join(tmpdir(), 'kode-skill-home-'))
    await setCwd(projectDir)
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    rmSync(projectDir, { recursive: true, force: true })
    rmSync(homeDir, { recursive: true, force: true })
  })

  test('loads .kode/skills/<name>/SKILL.md and splits allowed-tools string', async () => {
    await withEnv(
      {
        KODE_CONFIG_DIR: join(homeDir, '.kode'),
        KODE_SKILLS_STRICT: undefined,
      },
      async () => {
        const skillDir = join(projectDir, '.kode', 'skills', 'test-skill')
        mkdirSync(skillDir, { recursive: true })
        writeFileSync(
          join(skillDir, 'SKILL.md'),
          [
            '---',
            'name: test-skill',
            'description: Test skill for parsing',
            'allowed-tools: Read Bash(git:*) Bash(jq:*)',
            '---',
            '',
            '# Test',
          ].join('\n'),
          'utf8',
        )

        reloadCustomCommands()
        const cmds = await loadCustomCommands()
        const skill = cmds.find(c => c.isSkill && c.name === 'test-skill')
        expect(skill).toBeTruthy()
        expect(skill?.allowedTools).toEqual([
          'Read',
          'Bash(git:*)',
          'Bash(jq:*)',
        ])
        expect(skill?.filePath).toContain('test-skill')
        expect(skill?.filePath?.toLowerCase().endsWith('skill.md')).toBe(true)
        expect(skill?.progressMessage).toBe('loading')
        expect(skill?.userFacingName()).toBe('test-skill')
      },
    )
  })

  test('accepts lowercase skill.md when SKILL.md is missing', async () => {
    await withEnv(
      {
        KODE_CONFIG_DIR: join(homeDir, '.kode'),
        KODE_SKILLS_STRICT: undefined,
      },
      async () => {
        const skillDir = join(projectDir, '.kode', 'skills', 'lower-skill')
        mkdirSync(skillDir, { recursive: true })
        writeFileSync(
          join(skillDir, 'skill.md'),
          [
            '---',
            'name: lower-skill',
            'description: Lowercase file name should load',
            '---',
            '',
            '# Lower',
          ].join('\n'),
          'utf8',
        )

        reloadCustomCommands()
        const cmds = await loadCustomCommands()
        const skill = cmds.find(c => c.isSkill && c.name === 'lower-skill')
        expect(skill).toBeTruthy()
        expect(skill?.filePath?.toLowerCase().endsWith('skill.md')).toBe(true)
      },
    )
  })

  test('strict mode skips skills whose frontmatter name mismatches directory', async () => {
    await withEnv(
      { KODE_CONFIG_DIR: join(homeDir, '.kode'), KODE_SKILLS_STRICT: '1' },
      async () => {
        const skillDir = join(projectDir, '.kode', 'skills', 'dir-name')
        mkdirSync(skillDir, { recursive: true })
        writeFileSync(
          join(skillDir, 'SKILL.md'),
          [
            '---',
            'name: other-name',
            'description: Should be skipped in strict mode',
            '---',
            '',
            '# Bad',
          ].join('\n'),
          'utf8',
        )

        reloadCustomCommands()
        const cmds = await loadCustomCommands()
        const skill = cmds.find(c => c.isSkill && c.name === 'dir-name')
        expect(skill).toBeFalsy()
      },
    )
  })

  test('SkillTool.prompt includes official guidance/examples even when no skills are available', async () => {
    await withEnv(
      {
        KODE_CONFIG_DIR: join(homeDir, '.kode'),
        KODE_SKILLS_STRICT: undefined,
      },
      async () => {
        reloadCustomCommands()
        const prompt = await SkillTool.prompt()
        expect(prompt).toContain('When users ask you to run a "slash command"')
        expect(prompt).toContain('skill: "pdf"')
        expect(prompt).toContain('skill: "ms-office-suite:pdf"')
        expect(prompt).not.toContain('No skills are currently available')
      },
    )
  })

  test('SkillTool.prompt includes skill location path when available', async () => {
    await withEnv(
      {
        KODE_CONFIG_DIR: join(homeDir, '.kode'),
        KODE_SKILLS_STRICT: undefined,
      },
      async () => {
        const skillDir = join(projectDir, '.kode', 'skills', 'alpha')
        mkdirSync(skillDir, { recursive: true })
        const skillFile = join(skillDir, 'SKILL.md')
        writeFileSync(
          skillFile,
          [
            '---',
            'name: alpha',
            'description: Alpha skill',
            '---',
            '',
            '# A',
          ].join('\n'),
          'utf8',
        )

        reloadCustomCommands()
        const prompt = await SkillTool.prompt()
        expect(prompt).toContain('<name>\nalpha\n</name>')
        expect(prompt).toContain(`<location>\n${skillFile}\n</location>`)
      },
    )
  })
})
