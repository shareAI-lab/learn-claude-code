import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import plugin from '@commands/plugin'
import { setCwd } from '@utils/state'

describe('/plugin slash command', () => {
  const originalConfigDir = process.env.KODE_CONFIG_DIR
  const runnerCwd = process.cwd()

  let configDir: string
  let projectDir: string
  let repoDir: string

  beforeEach(async () => {
    configDir = mkdtempSync(join(tmpdir(), 'kode-plugin-cfg-'))
    projectDir = mkdtempSync(join(tmpdir(), 'kode-plugin-proj-'))
    process.env.KODE_CONFIG_DIR = configDir
    await setCwd(projectDir)

    repoDir = join(projectDir, 'skills-repo')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'pdf'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'xlsx'), { recursive: true })

    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          name: 'my-marketplace',
          owner: { name: 'Test', email: 'test@example.com' },
          metadata: { description: 'Test marketplace', version: '1.0.0' },
          plugins: [
            {
              name: 'document-skills',
              description: 'Doc skills pack',
              source: './',
              strict: false,
              skills: ['./skills/xlsx', './skills/pdf'],
            },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )

    for (const skillName of ['pdf', 'xlsx']) {
      writeFileSync(
        join(repoDir, 'skills', skillName, 'SKILL.md'),
        [
          '---',
          `name: ${skillName}`,
          `description: ${skillName} skill`,
          'allowed-tools: Read',
          '---',
          '',
          `# ${skillName}`,
        ].join('\n'),
        'utf8',
      )
    }
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    if (originalConfigDir === undefined) delete process.env.KODE_CONFIG_DIR
    else process.env.KODE_CONFIG_DIR = originalConfigDir
    rmSync(configDir, { recursive: true, force: true })
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('marketplace add + install + disable/enable + uninstall', async () => {
    const ctx = {} as any

    const added = await plugin.call(`marketplace add ${repoDir}`, ctx)
    expect(added).toContain('Successfully added marketplace: my-marketplace')

    const installed = await plugin.call(
      'install document-skills@my-marketplace --scope user',
      ctx,
    )
    expect(installed).toContain('Installed document-skills@my-marketplace')
    expect(existsSync(join(configDir, 'skills', 'pdf'))).toBe(true)

    const listed = await plugin.call('list --scope user', ctx)
    expect(listed).toContain('document-skills@my-marketplace')

    const disabled = await plugin.call(
      'disable document-skills@my-marketplace --scope user',
      ctx,
    )
    expect(disabled).toContain('Disabled document-skills@my-marketplace')
    expect(existsSync(join(configDir, 'skills', 'pdf'))).toBe(false)

    const enabled = await plugin.call(
      'enable document-skills@my-marketplace --scope user',
      ctx,
    )
    expect(enabled).toContain('Enabled document-skills@my-marketplace')
    expect(existsSync(join(configDir, 'skills', 'pdf'))).toBe(true)

    const uninstalled = await plugin.call(
      'uninstall document-skills@my-marketplace --scope user',
      ctx,
    )
    expect(uninstalled).toContain('Uninstalled document-skills@my-marketplace')
    expect(existsSync(join(configDir, 'skills', 'pdf'))).toBe(false)
  })
})
