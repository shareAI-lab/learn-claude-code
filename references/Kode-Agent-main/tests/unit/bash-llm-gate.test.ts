import { describe, expect, mock, test } from 'bun:test'
import {
  formatBashLlmGateBlockMessage,
  runBashLlmSafetyGate,
} from '@tools/BashTool/llmSafetyGate'

describe('Bash LLM intent gate', () => {
  test('runs for user bash mode (no bypass)', async () => {
    let calls = 0
    const result = await runBashLlmSafetyGate({
      command: 'rm -rf /tmp/kode-test',
      userPrompt: 'Delete a temp folder',
      description: '',
      platform: process.platform,
      commandSource: 'user_bash_mode',
      safeMode: false,
      runInBackground: false,
      willSandbox: true,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () => {
        calls++
        return 'ALLOW'
      },
    })
    expect(result.decision).toBe('allow')
    expect(calls).toBe(1)
  })

  test('parses ALLOW verdict', async () => {
    const result = await runBashLlmSafetyGate({
      command: 'sudo ls',
      userPrompt: 'List files',
      description: '',
      platform: process.platform,
      commandSource: 'agent_call',
      safeMode: false,
      runInBackground: false,
      willSandbox: true,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () => `  ALLOW  \n(extra ignored)`,
    })
    expect(result.decision).toBe('allow')
  })

  test('parses BLOCK verdict with reason', async () => {
    const result = await runBashLlmSafetyGate({
      command: 'rm -rf /',
      userPrompt: 'Delete everything',
      description: '',
      platform: process.platform,
      commandSource: 'agent_call',
      safeMode: false,
      runInBackground: false,
      willSandbox: true,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () => `BLOCK: destructive`,
    })
    expect(result.decision).toBe('block')
    if (result.decision === 'block') {
      expect(result.verdict.summary).toBe('destructive')
    }
  })

  test('parses XML verdict output', async () => {
    const result = await runBashLlmSafetyGate({
      command: 'sudo ls',
      userPrompt: 'List files',
      description: '',
      platform: process.platform,
      commandSource: 'agent_call',
      safeMode: false,
      runInBackground: false,
      willSandbox: true,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () =>
        `<decision>allow</decision>\n<reason>ok</reason>\n(ignored)`,
    })
    expect(result.decision).toBe('allow')
  })

  test('fails closed when model output is invalid', async () => {
    let calls = 0
    const result = await runBashLlmSafetyGate({
      command: 'sudo ls',
      userPrompt: 'List files',
      description: '',
      platform: process.platform,
      commandSource: 'agent_call',
      safeMode: false,
      runInBackground: false,
      willSandbox: true,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () => {
        calls++
        return 'Here is my analysis:\n1) ...\n2) ...'
      },
    })

    expect(result.decision).toBe('error')
    expect(calls).toBe(3)
  })

  test('formats non-Zod errors in error path (Error instance)', async () => {
    const result = await runBashLlmSafetyGate({
      command: 'sudo ls',
      userPrompt: 'List files',
      description: '',
      platform: process.platform,
      commandSource: 'agent_call',
      safeMode: false,
      runInBackground: false,
      willSandbox: false,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () => {
        throw new Error('boom')
      },
    })
    expect(result.decision).toBe('error')
    if (result.decision === 'error') {
      expect(result.error).toBe('boom')
    }
  })

  test('formats non-Zod errors in error path (non-Error value)', async () => {
    const result = await runBashLlmSafetyGate({
      command: 'sudo ls',
      userPrompt: 'List files',
      description: '',
      platform: process.platform,
      commandSource: 'agent_call',
      safeMode: false,
      runInBackground: false,
      willSandbox: false,
      sandboxRequired: false,
      cwd: process.cwd(),
      originalCwd: process.cwd(),
      query: async () => {
        throw 123
      },
    })
    expect(result.decision).toBe('error')
    if (result.decision === 'error') {
      expect(result.error).toBe('123')
    }
  })

  test('uses defaultGateQuery (mocked) when no query is provided', async () => {
    try {
      mock.module('@services/llm', () => {
        return {
          queryLLM: async () => {
            return {
              message: {
                content: [
                  { type: 'not_text', text: 'ignored' },
                  {
                    type: 'text',
                    text: 'ALLOW',
                  },
                ],
              },
            }
          },
          API_ERROR_MESSAGE_PREFIX: 'API_ERROR: ',
        }
      })

      const result = await runBashLlmSafetyGate({
        command: 'sudo ls',
        userPrompt: 'List files',
        description: '',
        platform: process.platform,
        commandSource: 'agent_call',
        safeMode: false,
        runInBackground: false,
        willSandbox: true,
        sandboxRequired: false,
        cwd: process.cwd(),
        originalCwd: process.cwd(),
      })
      expect(result.decision).toBe('allow')
    } finally {
      mock.restore()
    }
  })

  test('defaultGateQuery surfaces API error messages as gate errors', async () => {
    try {
      mock.module('@services/llm', () => {
        return {
          queryLLM: async () => {
            return {
              isApiErrorMessage: true,
              message: {
                content: [{ type: 'text', text: 'API_ERROR: Invalid API key' }],
              },
            }
          },
          API_ERROR_MESSAGE_PREFIX: 'API_ERROR: ',
        }
      })

      const result = await runBashLlmSafetyGate({
        command: 'sudo ls',
        userPrompt: 'List files',
        description: '',
        platform: process.platform,
        commandSource: 'agent_call',
        safeMode: false,
        runInBackground: false,
        willSandbox: false,
        sandboxRequired: false,
        cwd: process.cwd(),
        originalCwd: process.cwd(),
      })
      expect(result.decision).toBe('error')
      if (result.decision === 'error') {
        expect(result.error).toContain('LLM gate model error:')
      }
    } finally {
      mock.restore()
    }
  })

  test('formats block message with corrected command', () => {
    const msg = formatBashLlmGateBlockMessage({
      action: 'block',
      summary: 'Dangerous',
    })
    expect(msg).toContain('Blocked by LLM intent gate: Dangerous')
  })

  test('formats block message without corrected command', () => {
    const msg = formatBashLlmGateBlockMessage({
      action: 'block',
      summary: 'Dangerous',
    })
    expect(msg).toContain('Blocked by LLM intent gate: Dangerous')
  })
})
