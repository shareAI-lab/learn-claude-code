import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { createAssistantMessage, createUserMessage } from '@utils/messages'
import { setCwd } from '@utils/state'
import {
  getKodeAgentSessionId,
  resetKodeAgentSessionIdForTests,
  setKodeAgentSessionId,
} from '@utils/protocol/kodeAgentSessionId'
import {
  appendSessionJsonlFromMessage,
  getSessionLogFilePath,
  resetSessionJsonlStateForTests,
  sanitizeProjectNameForSessionStore,
} from '@utils/protocol/kodeAgentSessionLog'

describe('JSONL session persistence (projects/*.jsonl)', () => {
  const originalConfigDir = process.env.KODE_CONFIG_DIR
  const runnerCwd = process.cwd()

  let configDir: string
  let projectDir: string

  beforeEach(async () => {
    resetSessionJsonlStateForTests()
    setKodeAgentSessionId('704b907b-2b0f-478d-a7cb-b9fecf921913')
    configDir = mkdtempSync(join(tmpdir(), 'kode-session-jsonl-config-'))
    projectDir = mkdtempSync(join(tmpdir(), 'kode-session-jsonl-project-'))
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

  test('sanitizeProjectNameForSessionStore matches reference bc() behavior', () => {
    expect(sanitizeProjectNameForSessionStore('/Users/me/my repo')).toBe(
      '-Users-me-my-repo',
    )
    expect(sanitizeProjectNameForSessionStore('C:\\Users\\me\\repo')).toBe(
      'C--Users-me-repo',
    )
  })

  test('writes file-history-snapshot then user/assistant records with parentUuid chaining', async () => {
    const user = createUserMessage('hello')
    const assistant = createAssistantMessage('hi')

    appendSessionJsonlFromMessage({ message: user, toolUseContext: {} })
    appendSessionJsonlFromMessage({ message: assistant, toolUseContext: {} })

    const logPath = getSessionLogFilePath({
      cwd: projectDir,
      sessionId: getKodeAgentSessionId(),
    })
    const lines = readFileSync(logPath, 'utf8')
      .split('\n')
      .filter(Boolean)
      .map(l => JSON.parse(l))

    expect(lines.length).toBe(3)

    expect(lines[0].type).toBe('file-history-snapshot')
    expect(lines[0].messageId).toBe(user.uuid)

    expect(lines[1].type).toBe('user')
    expect(lines[1].uuid).toBe(user.uuid)
    expect(lines[1].parentUuid).toBe(null)
    expect(lines[1].sessionId).toBe(getKodeAgentSessionId())
    expect(lines[1].agentId).toBe('main')
    expect(lines[1].isSidechain).toBe(false)
    expect(typeof lines[1].slug).toBe('string')
    expect(lines[1].slug.length).toBeGreaterThan(0)
    expect(lines[1].logicalParentUuid).toBeUndefined()
    expect(lines[1].gitBranch).toBeUndefined()
    expect(lines[1].message.role).toBe('user')

    expect(lines[2].type).toBe('assistant')
    expect(lines[2].uuid).toBe(assistant.uuid)
    expect(lines[2].parentUuid).toBe(user.uuid)
    expect(lines[2].sessionId).toBe(getKodeAgentSessionId())
    expect(lines[2].agentId).toBe('main')
    expect(lines[2].isSidechain).toBe(false)
    expect(lines[2].slug).toBe(lines[1].slug)
    expect(lines[2].message.role).toBe('assistant')
  })

  test('persists toolUseResult as tool output data (not wrapper)', () => {
    const toolResultMessage = createUserMessage(
      [
        {
          type: 'tool_result',
          tool_use_id: 'toolu_test',
          is_error: false,
          content: 'ok',
        },
      ],
      {
        data: { filenames: ['a.ts'], numFiles: 1 },
        resultForAssistant: [{ type: 'text', text: 'ok' }],
      },
    )

    appendSessionJsonlFromMessage({
      message: toolResultMessage,
      toolUseContext: {},
    })

    const logPath = getSessionLogFilePath({
      cwd: projectDir,
      sessionId: getKodeAgentSessionId(),
    })
    const lines = readFileSync(logPath, 'utf8')
      .split('\n')
      .filter(Boolean)
      .map(l => JSON.parse(l))

    const userLine = lines.find(
      l => l.type === 'user' && l.uuid === toolResultMessage.uuid,
    )
    expect(userLine).toBeTruthy()
    expect(userLine.toolUseResult).toEqual({ filenames: ['a.ts'], numFiles: 1 })
  })
})
