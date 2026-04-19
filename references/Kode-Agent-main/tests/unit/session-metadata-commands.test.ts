import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import rename from '@commands/rename'
import tag from '@commands/tag'
import {
  getKodeAgentSessionId,
  resetKodeAgentSessionIdForTests,
  setKodeAgentSessionId,
} from '@utils/protocol/kodeAgentSessionId'
import {
  getCurrentSessionCustomTitle,
  getCurrentSessionTag,
  getSessionLogFilePath,
  resetSessionJsonlStateForTests,
} from '@utils/protocol/kodeAgentSessionLog'
import { loadKodeAgentSessionLogData } from '@utils/protocol/kodeAgentSessionLoad'
import { setCwd } from '@utils/state'

describe('/rename + /tag (session metadata records)', () => {
  const originalConfigDir = process.env.KODE_CONFIG_DIR
  const runnerCwd = process.cwd()

  let configDir: string
  let projectDir: string

  beforeEach(async () => {
    resetSessionJsonlStateForTests()
    setKodeAgentSessionId('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    configDir = mkdtempSync(join(tmpdir(), 'kode-session-metadata-config-'))
    projectDir = mkdtempSync(join(tmpdir(), 'kode-session-metadata-project-'))
    process.env.KODE_CONFIG_DIR = configDir
    await setCwd(projectDir)
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    resetSessionJsonlStateForTests()
    resetKodeAgentSessionIdForTests()
    if (originalConfigDir === undefined) {
      delete process.env.KODE_CONFIG_DIR
    } else {
      process.env.KODE_CONFIG_DIR = originalConfigDir
    }
    rmSync(configDir, { recursive: true, force: true })
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('persists custom-title and tag records for current session', async () => {
    const ctx = {} as any

    const renameOut = await rename.call('My Session', ctx)
    expect(renameOut).toContain('Session renamed to:')
    expect(getCurrentSessionCustomTitle()).toBe('My Session')

    const tagOut = await tag.call('pr', ctx)
    expect(tagOut).toContain('Session tagged as:')
    expect(getCurrentSessionTag()).toBe('pr')

    const logPath = getSessionLogFilePath({
      cwd: projectDir,
      sessionId: getKodeAgentSessionId(),
    })
    const lines = readFileSync(logPath, 'utf8')
      .split('\n')
      .filter(Boolean)
      .map(l => JSON.parse(l))

    expect(
      lines.some(
        l => l.type === 'custom-title' && l.customTitle === 'My Session',
      ),
    ).toBe(true)
    expect(lines.some(l => l.type === 'tag' && l.tag === 'pr')).toBe(true)

    const data = loadKodeAgentSessionLogData({
      cwd: projectDir,
      sessionId: getKodeAgentSessionId(),
    })
    expect(data.customTitles.get(getKodeAgentSessionId())).toBe('My Session')
    expect(data.tags.get(getKodeAgentSessionId())).toBe('pr')
  })
})
