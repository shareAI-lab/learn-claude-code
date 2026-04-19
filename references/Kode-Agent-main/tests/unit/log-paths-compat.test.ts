import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { dirname, join } from 'path'
import {
  CACHE_PATHS,
  LEGACY_CACHE_PATHS,
  getMessagesPath,
  loadLogList,
} from '@utils/log'

function writeJson(filePath: string, value: unknown) {
  mkdirSync(dirname(filePath), { recursive: true })
  writeFileSync(filePath, JSON.stringify(value, null, 2), 'utf8')
}

describe('log paths (messages)', () => {
  const originalLogRoot = process.env.KODE_LOG_ROOT
  const originalLegacyCacheRoot = process.env.KODE_LEGACY_CACHE_ROOT

  let newRoot: string
  let legacyRoot: string

  beforeEach(() => {
    newRoot = mkdtempSync(join(tmpdir(), 'kode-log-new-'))
    legacyRoot = mkdtempSync(join(tmpdir(), 'kode-log-legacy-'))

    process.env.KODE_LOG_ROOT = newRoot
    process.env.KODE_LEGACY_CACHE_ROOT = legacyRoot
  })

  afterEach(() => {
    if (originalLogRoot === undefined) {
      delete process.env.KODE_LOG_ROOT
    } else {
      process.env.KODE_LOG_ROOT = originalLogRoot
    }

    if (originalLegacyCacheRoot === undefined) {
      delete process.env.KODE_LEGACY_CACHE_ROOT
    } else {
      process.env.KODE_LEGACY_CACHE_ROOT = originalLegacyCacheRoot
    }

    rmSync(newRoot, { recursive: true, force: true })
    rmSync(legacyRoot, { recursive: true, force: true })
  })

  test('getMessagesPath uses the new log root (KODE_LOG_ROOT)', () => {
    const expectedMessagesDir = join(
      newRoot,
      process.cwd().replace(/[^a-zA-Z0-9]/g, '-'),
      'messages',
    )

    const path = getMessagesPath('2025-01-27T01-31-35-104Z', 0, 0)
    expect(path.startsWith(expectedMessagesDir)).toBe(true)
  })

  test('loadLogList discovers logs from legacy cache root', async () => {
    const legacyMessagesDir = LEGACY_CACHE_PATHS.messages()
    const filename = '2025-01-27T01-31-35-104Z-2.json'
    const legacyPath = join(legacyMessagesDir, filename)

    writeJson(legacyPath, [
      {
        type: 'user',
        message: { content: 'hello' },
        timestamp: '2025-01-27T01:31:35.104Z',
      },
      {
        type: 'assistant',
        message: { content: 'hi' },
        timestamp: '2025-01-27T01:31:36.104Z',
      },
    ])

    const logs = await loadLogList(CACHE_PATHS.messages())
    const found = logs.find(log => log.fullPath.endsWith(filename))
    expect(found).toBeTruthy()

    const candidateDirs = [CACHE_PATHS.messages(), legacyMessagesDir]
    expect(candidateDirs.some(dir => found!.fullPath.startsWith(dir))).toBe(
      true,
    )
  })
})
