import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { addMarketplace, installSkillPlugin } from '@services/skillMarketplace'
import {
  disableSkillPlugin,
  enableSkillPlugin,
  listEnabledInstalledPluginPackRoots,
  uninstallSkillPlugin,
} from '@services/skillMarketplace'
import { configureSessionPlugins } from '@services/pluginRuntime'
import {
  loadCustomCommands,
  reloadCustomCommands,
} from '@services/customCommands'
import { __resetSessionPluginsForTests } from '@utils/session/sessionPlugins'
import { setCwd } from '@utils/state'

describe('plugin pack install/runtime (marketplace → full plugin dir)', () => {
  const runnerCwd = process.cwd()
  const originalConfigDir = process.env.KODE_CONFIG_DIR

  let projectDir: string
  let homeDir: string
  let repoDir: string

  beforeEach(async () => {
    projectDir = mkdtempSync(join(tmpdir(), 'kode-plugin-pack-proj-'))
    homeDir = mkdtempSync(join(tmpdir(), 'kode-plugin-pack-home-'))
    process.env.KODE_CONFIG_DIR = join(homeDir, '.kode')
    await setCwd(projectDir)

    repoDir = join(projectDir, 'plugins-repo')
    mkdirSync(join(repoDir, '.claude-plugin'), { recursive: true })

    const pluginRoot = join(repoDir, 'plugins', 'hookify')
    mkdirSync(join(pluginRoot, '.claude-plugin'), { recursive: true })
    writeFileSync(
      join(pluginRoot, '.claude-plugin', 'plugin.json'),
      JSON.stringify({ name: 'hookify', version: '1.0.0' }, null, 2) + '\n',
      'utf8',
    )
    mkdirSync(join(pluginRoot, 'commands'), { recursive: true })
    writeFileSync(join(pluginRoot, 'commands', 'hookify.md'), '# Hookify\n')
    writeFileSync(join(pluginRoot, 'commands', 'list.md'), '# List\n')

    writeFileSync(
      join(repoDir, '.claude-plugin', 'marketplace.json'),
      JSON.stringify(
        {
          $schema: 'https://example.com/marketplace.schema.json',
          name: 'my-marketplace',
          description: 'Test marketplace',
          plugins: [
            {
              name: 'hookify',
              description: 'Hookify plugin',
              version: '1.0.0',
              source: './plugins/hookify',
              category: 'learning',
            },
          ],
        },
        null,
        2,
      ),
      'utf8',
    )
  })

  afterEach(async () => {
    __resetSessionPluginsForTests()
    reloadCustomCommands()
    await setCwd(runnerCwd)
    if (originalConfigDir === undefined) delete process.env.KODE_CONFIG_DIR
    else process.env.KODE_CONFIG_DIR = originalConfigDir
    rmSync(projectDir, { recursive: true, force: true })
    rmSync(homeDir, { recursive: true, force: true })
  })

  test('install/disable/enable/uninstall plugin pack and load via session plugins', async () => {
    await addMarketplace(repoDir)
    const install = installSkillPlugin('hookify@my-marketplace')
    expect(install.installedSkills).toEqual([])

    const roots1 = listEnabledInstalledPluginPackRoots()
    expect(roots1.length).toBe(1)
    const root = roots1[0]!
    expect(existsSync(join(root, '.claude-plugin', 'plugin.json'))).toBe(true)

    await configureSessionPlugins({ pluginDirs: roots1 })
    const cmds1 = await loadCustomCommands()
    const names1 = cmds1.map(c => c.userFacingName())
    expect(names1).toContain('hookify')
    expect(names1).toContain('hookify:list')

    disableSkillPlugin('hookify@my-marketplace')
    expect(listEnabledInstalledPluginPackRoots()).toEqual([])

    enableSkillPlugin('hookify@my-marketplace')
    const roots2 = listEnabledInstalledPluginPackRoots()
    expect(roots2.length).toBe(1)

    uninstallSkillPlugin('hookify@my-marketplace')
    expect(listEnabledInstalledPluginPackRoots()).toEqual([])
    expect(existsSync(root)).toBe(false)
  })
})
