import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { configureSessionPlugins } from '@services/pluginRuntime'
import { clearAgentCache, getAgentByType } from '@utils/agent/loader'
import { __resetSessionPluginsForTests } from '@utils/session/sessionPlugins'
import { setCwd } from '@utils/state'

describe('--plugin-dir runtime: agent discovery', () => {
  const runnerCwd = process.cwd()
  let projectDir: string
  let pluginDir: string

  beforeEach(async () => {
    projectDir = mkdtempSync(join(tmpdir(), 'kode-plugin-dir-agents-'))
    await setCwd(projectDir)

    pluginDir = join(projectDir, 'demo-plugin')
    mkdirSync(join(pluginDir, '.kode-plugin'), { recursive: true })
    writeFileSync(
      join(pluginDir, '.kode-plugin', 'plugin.json'),
      JSON.stringify(
        { name: 'demo-plugin', version: '0.1.0', agents: './extra-agent.md' },
        null,
        2,
      ) + '\n',
      'utf8',
    )

    mkdirSync(join(pluginDir, 'agents'), { recursive: true })
    writeFileSync(
      join(pluginDir, 'agents', 'demo-agent.md'),
      `---\nname: demo-agent\ndescription: Demo agent\ntools: [\"Read\"]\n---\n\nYou are a demo agent.\n`,
      'utf8',
    )
    writeFileSync(
      join(pluginDir, 'extra-agent.md'),
      `---\nname: extra-agent\ndescription: Extra agent\ntools: [\"Read\"]\n---\n\nYou are an extra agent.\n`,
      'utf8',
    )

    await configureSessionPlugins({ pluginDirs: [pluginDir] })
    clearAgentCache()
  })

  afterEach(async () => {
    __resetSessionPluginsForTests()
    clearAgentCache()
    await setCwd(runnerCwd)
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('loads plugin agent', async () => {
    const agent = await getAgentByType('demo-agent')
    expect(agent).toBeTruthy()
    expect(agent?.agentType).toBe('demo-agent')
    expect(agent?.location).toBe('plugin')
  })

  test('loads plugin agent from manifest file path', async () => {
    const agent = await getAgentByType('extra-agent')
    expect(agent).toBeTruthy()
    expect(agent?.agentType).toBe('extra-agent')
    expect(agent?.location).toBe('plugin')
  })
})
