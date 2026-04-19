import { describe, expect, test } from 'bun:test'
import { createAssistantMessage, createUserMessage } from '@utils/messages'
import {
  kodeMessageToSdkMessage,
  makeSdkInitMessage,
  makeSdkResultMessage,
} from '@utils/protocol/kodeAgentStreamJson'

describe('stream-json helpers', () => {
  test('init message includes session_id/cwd/tools', () => {
    const msg = makeSdkInitMessage({
      sessionId: '00000000-0000-0000-0000-000000000000',
      cwd: '/tmp/project',
      tools: ['Bash', 'Read'],
    })
    expect(msg.type).toBe('system')
    expect((msg as any).subtype).toBe('init')
    expect((msg as any).session_id).toBe('00000000-0000-0000-0000-000000000000')
    expect((msg as any).cwd).toBe('/tmp/project')
    expect((msg as any).tools).toEqual(['Bash', 'Read'])
    expect('slash_commands' in (msg as any)).toBe(false)
  })

  test('init message includes slash_commands only when provided', () => {
    const withSlash = makeSdkInitMessage({
      sessionId: '00000000-0000-0000-0000-000000000000',
      cwd: '/tmp/project',
      tools: ['Bash'],
      slashCommands: ['/help', '/compact'],
    })
    expect((withSlash as any).slash_commands).toEqual(['/help', '/compact'])
  })

  test('maps user/assistant messages and normalizes tool_use block types', () => {
    const sessionId = '11111111-1111-1111-1111-111111111111'

    const user = createUserMessage('hello')
    const sdkUser = kodeMessageToSdkMessage(user as any, sessionId)
    expect(sdkUser?.type).toBe('user')
    expect((sdkUser as any).session_id).toBe(sessionId)

    const assistant = createAssistantMessage('hi')
    ;(assistant as any).message.content = [
      {
        type: 'server_tool_use',
        id: 'toolu_1',
        name: 'Grep',
        input: { pattern: 'x' },
      },
    ]
    const sdkAssistant = kodeMessageToSdkMessage(assistant as any, sessionId)
    expect(sdkAssistant?.type).toBe('assistant')
    expect((sdkAssistant as any).message.content[0].type).toBe('tool_use')
  })

  test('result message matches SDK shape', () => {
    const msg = makeSdkResultMessage({
      sessionId: '22222222-2222-2222-2222-222222222222',
      result: 'ok',
      numTurns: 1,
      totalCostUsd: 0.01,
      durationMs: 123,
      durationApiMs: 0,
      isError: false,
    })
    expect(msg.type).toBe('result')
    expect((msg as any).subtype).toBe('success')
    expect((msg as any).session_id).toBe('22222222-2222-2222-2222-222222222222')
    expect((msg as any).result).toBe('ok')
  })
})
