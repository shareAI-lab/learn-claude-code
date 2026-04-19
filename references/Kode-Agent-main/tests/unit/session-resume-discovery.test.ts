import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdirSync, mkdtempSync, rmSync, utimesSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { dirname, join } from 'path'
import { getSessionLogFilePath } from '@utils/protocol/kodeAgentSessionLog'
import {
  listKodeAgentSessions,
  resolveResumeSessionIdentifier,
} from '@utils/protocol/kodeAgentSessionResume'

function writeSessionJsonl(args: {
  cwd: string
  sessionId: string
  slug: string
  customTitle?: string
  tag?: string
  summary?: string
}) {
  const { cwd, sessionId, slug, customTitle, tag, summary } = args
  const path = getSessionLogFilePath({ cwd, sessionId })
  mkdirSync(dirname(path), { recursive: true })

  const now = new Date().toISOString()
  const lines: any[] = [
    { type: 'assistant', sessionId, uuid: 'a1', slug, cwd, timestamp: now },
    ...(summary ? [{ type: 'summary', summary, leafUuid: 'a1' }] : []),
    ...(customTitle ? [{ type: 'custom-title', sessionId, customTitle }] : []),
    ...(tag ? [{ type: 'tag', sessionId, tag }] : []),
  ]

  writeFileSync(
    path,
    lines.map(l => JSON.stringify(l)).join('\n') + '\n',
    'utf8',
  )
  return path
}

describe('resume session discovery', () => {
  const originalConfigDir = process.env.KODE_CONFIG_DIR

  let configDir: string
  let projectA: string
  let projectB: string

  beforeEach(() => {
    configDir = mkdtempSync(join(tmpdir(), 'kode-resume-config-'))
    projectA = mkdtempSync(join(tmpdir(), 'kode-resume-project-a-'))
    projectB = mkdtempSync(join(tmpdir(), 'kode-resume-project-b-'))
    process.env.KODE_CONFIG_DIR = configDir
  })

  afterEach(() => {
    if (originalConfigDir === undefined) {
      delete process.env.KODE_CONFIG_DIR
    } else {
      process.env.KODE_CONFIG_DIR = originalConfigDir
    }
    rmSync(configDir, { recursive: true, force: true })
    rmSync(projectA, { recursive: true, force: true })
    rmSync(projectB, { recursive: true, force: true })
  })

  test('listKodeAgentSessions returns sorted sessions with metadata', () => {
    const s1 = '11111111-1111-1111-1111-111111111111'
    const s2 = '22222222-2222-2222-2222-222222222222'

    const p1 = writeSessionJsonl({
      cwd: projectA,
      sessionId: s1,
      slug: 'alpha-run-cat',
      customTitle: 'Session One',
      tag: 'pr',
      summary: 'sum1',
    })
    const p2 = writeSessionJsonl({
      cwd: projectA,
      sessionId: s2,
      slug: 'beta-run-dog',
      customTitle: 'Session Two',
      tag: 'main',
      summary: 'sum2',
    })

    const now = Date.now() / 1000
    utimesSync(p1, now - 10, now - 10)
    utimesSync(p2, now, now)

    const sessions = listKodeAgentSessions({ cwd: projectA })
    expect(sessions.map(s => s.sessionId)).toEqual([s2, s1])
    expect(sessions[0]?.slug).toBe('beta-run-dog')
    expect(sessions[0]?.customTitle).toBe('Session Two')
    expect(sessions[0]?.tag).toBe('main')
    expect(sessions[0]?.summary).toBe('sum2')
  })

  test('resolveResumeSessionIdentifier supports slug and custom title', () => {
    const s1 = '33333333-3333-3333-3333-333333333333'
    writeSessionJsonl({
      cwd: projectA,
      sessionId: s1,
      slug: 'gentle-build-otter',
      customTitle: 'My Session',
    })

    expect(
      resolveResumeSessionIdentifier({
        cwd: projectA,
        identifier: 'gentle-build-otter',
      }),
    ).toEqual({
      kind: 'ok',
      sessionId: s1,
    })
    expect(
      resolveResumeSessionIdentifier({
        cwd: projectA,
        identifier: 'My Session',
      }),
    ).toEqual({
      kind: 'ok',
      sessionId: s1,
    })
  })

  test('resolveResumeSessionIdentifier detects ambiguous session names', () => {
    const s1 = '44444444-4444-4444-4444-444444444444'
    const s2 = '55555555-5555-5555-5555-555555555555'
    writeSessionJsonl({ cwd: projectA, sessionId: s1, slug: 'same-slug' })
    writeSessionJsonl({ cwd: projectA, sessionId: s2, slug: 'same-slug' })

    const result = resolveResumeSessionIdentifier({
      cwd: projectA,
      identifier: 'same-slug',
    })
    expect(result.kind).toBe('ambiguous')
    if (result.kind === 'ambiguous') {
      expect(result.matchingSessionIds.sort()).toEqual([s1, s2].sort())
    }
  })

  test('resolveResumeSessionIdentifier returns different_directory when session exists elsewhere', () => {
    const other = '66666666-6666-6666-6666-666666666666'
    writeSessionJsonl({
      cwd: projectB,
      sessionId: other,
      slug: 'elsewhere-session',
    })

    const result = resolveResumeSessionIdentifier({
      cwd: projectA,
      identifier: other,
    })
    expect(result.kind).toBe('different_directory')
    if (result.kind === 'different_directory') {
      expect(result.otherCwd).toBe(projectB)
    }
  })
})
