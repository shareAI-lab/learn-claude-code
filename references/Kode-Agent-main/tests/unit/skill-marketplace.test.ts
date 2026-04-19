import { beforeEach, afterEach, describe, expect, test } from 'bun:test'
import {
  mkdtempSync,
  mkdirSync,
  rmSync,
  writeFileSync,
  existsSync,
  readFileSync,
} from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { setCwd } from '@utils/state'
import {
  addMarketplace,
  installSkillPlugin,
  listInstalledSkillPlugins,
  listMarketplaces,
  refreshMarketplaceAsync,
  uninstallSkillPlugin,
} from '@services/skillMarketplace'

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

describe('skill marketplace (local .kode-plugin/marketplace.json)', () => {
  const runnerCwd = process.cwd()

  let projectDir: string
  let homeDir: string
  let repoDir: string

  beforeEach(async () => {
    projectDir = mkdtempSync(join(tmpdir(), 'kode-skill-mkt-proj-'))
    homeDir = mkdtempSync(join(tmpdir(), 'kode-skill-mkt-home-'))
    await setCwd(projectDir)

    repoDir = join(projectDir, 'skills-repo')
    mkdirSync(join(repoDir, '.kode-plugin'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'pdf'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'xlsx'), { recursive: true })

    writeFileSync(
      join(repoDir, '.kode-plugin', 'marketplace.json'),
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
    rmSync(projectDir, { recursive: true, force: true })
    rmSync(homeDir, { recursive: true, force: true })
  })

  test('add marketplace + install/uninstall skills into user dir', async () => {
    await withEnv({ KODE_CONFIG_DIR: join(homeDir, '.kode') }, async () => {
      const { name } = await addMarketplace(repoDir)
      expect(name).toBe('my-marketplace')

      const marketplaces = listMarketplaces()
      expect(Object.keys(marketplaces)).toContain('my-marketplace')

      const install = installSkillPlugin('document-skills@my-marketplace')
      expect(install.installedSkills.sort()).toEqual(['pdf', 'xlsx'])
      expect(existsSync(join(homeDir, '.kode', 'skills', 'pdf'))).toBe(true)
      expect(existsSync(join(homeDir, '.kode', 'skills', 'xlsx'))).toBe(true)

      const installed = listInstalledSkillPlugins()
      expect(installed['document-skills@my-marketplace']).toBeTruthy()

      const uninstall = uninstallSkillPlugin('document-skills@my-marketplace')
      expect(uninstall.removedSkills.sort()).toEqual(['pdf', 'xlsx'])
      expect(existsSync(join(homeDir, '.kode', 'skills', 'pdf'))).toBe(false)
      expect(existsSync(join(homeDir, '.kode', 'skills', 'xlsx'))).toBe(false)
    })
  })

  test('project install writes to ./.kode/skills based on agent cwd', async () => {
    await withEnv({ KODE_CONFIG_DIR: join(homeDir, '.kode') }, async () => {
      await addMarketplace(repoDir)
      const install = installSkillPlugin('document-skills@my-marketplace', {
        project: true,
      })
      expect(install.installedSkills.sort()).toEqual(['pdf', 'xlsx'])
      expect(existsSync(join(projectDir, '.kode', 'skills', 'pdf'))).toBe(true)
      expect(existsSync(join(projectDir, '.kode', 'skills', 'xlsx'))).toBe(true)
    })
  })

  test('marketplace update refreshes cached directory from local source', async () => {
    await withEnv({ KODE_CONFIG_DIR: join(homeDir, '.kode') }, async () => {
      await addMarketplace(repoDir)

      const marketplaces = listMarketplaces()
      const installLocation = marketplaces['my-marketplace']!.installLocation
      const cachedMarketplacePath = join(
        installLocation,
        '.kode-plugin',
        'marketplace.json',
      )

      expect(readFileSync(cachedMarketplacePath, 'utf8')).toContain(
        'Test marketplace',
      )

      writeFileSync(
        join(repoDir, '.kode-plugin', 'marketplace.json'),
        JSON.stringify(
          {
            name: 'my-marketplace',
            owner: { name: 'Test', email: 'test@example.com' },
            metadata: { description: 'Updated marketplace', version: '1.0.0' },
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

      await refreshMarketplaceAsync('my-marketplace')
      expect(readFileSync(cachedMarketplacePath, 'utf8')).toContain(
        'Updated marketplace',
      )
    })
  })
})
