import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import plugin from '@commands/plugin'
import {
  formatValidationResult,
  validatePluginOrMarketplacePath,
} from '@services/pluginValidation'
import { setCwd } from '@utils/state'

describe('plugin/marketplace validation parity', () => {
  const originalConfigDir = process.env.KODE_CONFIG_DIR
  const runnerCwd = process.cwd()

  let configDir: string
  let projectDir: string

  beforeEach(async () => {
    configDir = mkdtempSync(join(tmpdir(), 'kode-plugin-validate-cfg-'))
    projectDir = mkdtempSync(join(tmpdir(), 'kode-plugin-validate-proj-'))
    process.env.KODE_CONFIG_DIR = configDir
    await setCwd(projectDir)
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    if (originalConfigDir === undefined) delete process.env.KODE_CONFIG_DIR
    else process.env.KODE_CONFIG_DIR = originalConfigDir
    rmSync(configDir, { recursive: true, force: true })
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('valid marketplace directory validates and /plugin validate works', async () => {
    const repoDir = join(projectDir, 'skills-repo')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'pdf'), { recursive: true })

    writeFileSync(
      join(repoDir, 'skills', 'pdf', 'SKILL.md'),
      ['---', 'name: pdf', 'description: PDF skill', '---', '', '# pdf'].join(
        '\n',
      ),
      'utf8',
    )

    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          name: 'my-marketplace',
          metadata: { description: 'Test marketplace' },
          plugins: [
            {
              name: 'document-skills',
              source: './',
              skills: ['./skills/pdf'],
            },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )

    const result = validatePluginOrMarketplacePath(repoDir)
    expect(result.fileType).toBe('marketplace')
    expect(result.success).toBe(true)
    expect(result.errors).toHaveLength(0)

    const formatted = formatValidationResult(result)
    expect(formatted).toContain('Validation passed')

    const slash = await plugin.call(`validate ${repoDir}`, {} as any)
    expect(slash).toContain('Validating marketplace manifest:')
    expect(slash).toContain('Validation passed')
  })

  test('marketplace duplicate plugin names fail', () => {
    const repoDir = join(projectDir, 'dup-marketplace')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'pdf'), { recursive: true })
    writeFileSync(
      join(repoDir, 'skills', 'pdf', 'SKILL.md'),
      ['---', 'name: pdf', 'description: PDF skill', '---', '', '# pdf'].join(
        '\n',
      ),
      'utf8',
    )
    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          name: 'my-marketplace',
          metadata: { description: 'Test marketplace' },
          plugins: [
            { name: 'document-skills', source: './', skills: ['./skills/pdf'] },
            { name: 'document-skills', source: './', skills: ['./skills/pdf'] },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )

    const result = validatePluginOrMarketplacePath(repoDir)
    expect(result.fileType).toBe('marketplace')
    expect(result.success).toBe(false)
    expect(
      result.errors.some(e => e.message.includes('Duplicate plugin name')),
    ).toBe(true)
  })

  test('official-shaped marketplace manifest validates (passthrough fields)', () => {
    const repoDir = join(projectDir, 'official-shaped-marketplace')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'pdf'), { recursive: true })

    writeFileSync(
      join(repoDir, 'skills', 'pdf', 'SKILL.md'),
      ['---', 'name: pdf', 'description: PDF skill', '---', '', '# pdf'].join(
        '\n',
      ),
      'utf8',
    )

    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          $schema: 'https://example.com/marketplace.schema.json',
          name: 'claude-plugins-official',
          description: 'Official marketplace shape',
          owner: { name: 'Test', email: 'test@example.com' },
          plugins: [
            {
              name: 'document-skills',
              description: 'Doc skills pack',
              version: '1.0.0',
              author: { name: 'Test', email: 'test@example.com' },
              category: 'learning',
              homepage: 'https://example.com/plugins/document-skills',
              source: './',
              strict: false,
              skills: ['./skills/pdf'],
              lspServers: {
                typescript: {
                  command: 'typescript-language-server',
                  args: ['--stdio'],
                  extensionToLanguage: { '.ts': 'typescript' },
                },
              },
            },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )

    const result = validatePluginOrMarketplacePath(repoDir)
    expect(result.fileType).toBe('marketplace')
    expect(result.success).toBe(true)
    expect(result.errors).toHaveLength(0)
  })

  test('official-shaped marketplace still enforces safe relative source paths', () => {
    const repoDir = join(projectDir, 'bad-source-marketplace')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })
    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          $schema: 'https://example.com/marketplace.schema.json',
          name: 'my-marketplace',
          description: 'Test marketplace',
          plugins: [
            {
              name: 'bad-plugin',
              source: '../escape',
              version: '1.0.0',
            },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )

    const result = validatePluginOrMarketplacePath(repoDir)
    expect(result.fileType).toBe('marketplace')
    expect(result.success).toBe(false)
    expect(
      result.errors.some(e => e.path.endsWith('.source') && e.message),
    ).toBe(true)
  })

  test('marketplace skill frontmatter name mismatch fails', () => {
    const repoDir = join(projectDir, 'bad-skill')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })
    mkdirSync(join(repoDir, 'skills', 'pdf'), { recursive: true })
    writeFileSync(
      join(repoDir, 'skills', 'pdf', 'SKILL.md'),
      [
        '---',
        'name: pdf-processing',
        'description: PDF skill',
        '---',
        '',
        '# pdf',
      ].join('\n'),
      'utf8',
    )
    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          name: 'my-marketplace',
          metadata: { description: 'Test marketplace' },
          plugins: [
            { name: 'document-skills', source: './', skills: ['./skills/pdf'] },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )

    const result = validatePluginOrMarketplacePath(repoDir)
    expect(result.success).toBe(false)
    expect(
      result.errors.some(e =>
        e.message.includes('Frontmatter name must match directory name'),
      ),
    ).toBe(true)
  })

  test('plugin invalid semver fails', () => {
    const pluginDir = join(projectDir, 'bad-plugin')
    mkdirSync(join(pluginDir, '.claude-plugin'), { recursive: true })
    mkdirSync(join(pluginDir, 'commands'), { recursive: true })
    writeFileSync(
      join(pluginDir, '.claude-plugin', 'plugin.json'),
      JSON.stringify(
        {
          name: 'bad-plugin',
          version: '1.0',
          description: 'Some plugin',
          author: { name: 'Test' },
          commands: ['./commands'],
        },
        null,
        2,
      ),
      'utf8',
    )

    const result = validatePluginOrMarketplacePath(pluginDir)
    expect(result.fileType).toBe('plugin')
    expect(result.success).toBe(false)
    expect(result.errors.some(e => e.path === 'version')).toBe(true)
  })
})
