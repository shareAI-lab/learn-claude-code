import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { configureSessionPlugins } from '@services/pluginRuntime'
import {
  loadCustomCommands,
  reloadCustomCommands,
} from '@services/customCommands'
import { __resetSessionPluginsForTests } from '@utils/session/sessionPlugins'
import { setCwd } from '@utils/state'

function writeJson(path: string, value: unknown) {
  mkdirSync(join(path, '..'), { recursive: true })
  writeFileSync(path, JSON.stringify(value, null, 2) + '\n', 'utf8')
}

describe('--plugin-dir runtime: commands & skills discovery', () => {
  const runnerCwd = process.cwd()
  let projectDir: string
  let pluginDir: string

  beforeEach(async () => {
    projectDir = mkdtempSync(join(tmpdir(), 'kode-plugin-dir-project-'))
    await setCwd(projectDir)

    pluginDir = join(projectDir, 'hookify')
    mkdirSync(join(pluginDir, '.kode-plugin'), { recursive: true })
    writeFileSync(
      join(pluginDir, '.kode-plugin', 'plugin.json'),
      JSON.stringify(
        { name: 'hookify', version: '0.1.0', commands: './extra-command.md' },
        null,
        2,
      ) + '\n',
      'utf8',
    )

    mkdirSync(join(pluginDir, 'commands'), { recursive: true })
    writeFileSync(
      join(pluginDir, 'commands', 'hookify.md'),
      '# Hookify\n',
      'utf8',
    )
    writeFileSync(join(pluginDir, 'commands', 'list.md'), '# List\n', 'utf8')
    writeFileSync(
      join(pluginDir, 'extra-command.md'),
      `---\ndescription: Extra command\n---\n\n# Extra\n`,
      'utf8',
    )

    mkdirSync(join(pluginDir, 'skills', 'writing-rules'), { recursive: true })
    writeFileSync(
      join(pluginDir, 'skills', 'writing-rules', 'SKILL.md'),
      `---\nname: writing-rules\ndescription: Writing rules\n---\n\n# Rules\n`,
      'utf8',
    )

    await configureSessionPlugins({ pluginDirs: [pluginDir] })
  })

  afterEach(async () => {
    __resetSessionPluginsForTests()
    reloadCustomCommands()
    await setCwd(runnerCwd)
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('loads namespaced plugin commands', async () => {
    const cmds = await loadCustomCommands()
    const names = cmds.map(c => c.userFacingName())
    expect(names).toContain('hookify')
    expect(names).toContain('hookify:list')
    expect(names).toContain('hookify:extra-command')
  })

  test('loads namespaced plugin skills', async () => {
    const cmds = await loadCustomCommands()
    const names = cmds
      .filter(c => (c as any).isSkill)
      .map(c => c.userFacingName())
    expect(names).toContain('hookify:writing-rules')
  })
})
