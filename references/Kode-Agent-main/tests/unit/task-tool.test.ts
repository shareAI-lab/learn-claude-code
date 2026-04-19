import { describe, expect, test } from 'bun:test'
import { TaskTool } from '@tools/agent/TaskTool/TaskTool'
import { getBackgroundAgentTask } from '@utils/session/backgroundTasks'

describe('TaskTool', () => {
  test('inputSchema ignores unknown keys (Reference CLI parity)', () => {
    const result = TaskTool.inputSchema.safeParse({
      description: 'Explore project structure',
      prompt: 'Explore the repo',
      subagent_type: 'general-purpose',
      thoroughness: 'very thorough',
    })

    expect(result.success).toBe(true)
    if (result.success) {
      expect('thoroughness' in result.data).toBe(false)
    }
  })

  test('validateInput: resume missing transcript rejects with reference wording', async () => {
    const result = await TaskTool.validateInput?.({
      description: 'resume task',
      prompt: 'do thing',
      subagent_type: 'general-purpose',
      resume: 'missing-agent-id',
    } as any)

    expect(result).toEqual({
      result: false,
      message: 'No transcript found for agent ID: missing-agent-id',
      meta: { resume: 'missing-agent-id' },
    })
  })

  test('run_in_background returns agentId', async () => {
    async function* stubQuery() {
      yield {
        type: 'assistant',
        costUSD: 0,
        durationMs: 0,
        uuid: 'a1',
        message: {
          id: 'm1',
          model: 'test',
          role: 'assistant',
          stop_reason: 'stop_sequence',
          stop_sequence: '',
          type: 'message',
          usage: {
            input_tokens: 1,
            output_tokens: 1,
            cache_creation_input_tokens: 0,
            cache_read_input_tokens: 0,
          },
          content: [{ type: 'text', text: 'ok', citations: [] }],
        },
      } as any
    }

    const gen = TaskTool.call(
      {
        description: 'bg',
        prompt: 'bg prompt',
        subagent_type: 'general-purpose',
        run_in_background: true,
      } as any,
      {
        abortController: new AbortController(),
        readFileTimestamps: {},
        options: {
          safeMode: false,
          forkNumber: 0,
          messageLogName: 'task-tool-test',
          verbose: false,
          model: 'main',
          mcpClients: [],
        },
        __testQuery: stubQuery,
      } as any,
    )

    const first = await gen.next()
    expect(first.done).toBe(false)
    if (first.done || !first.value) {
      throw new Error('Expected TaskTool to yield a result')
    }
    expect(first.value.type).toBe('result')
    expect(first.value.data.status).toBe('async_launched')
    expect(typeof first.value.data.agentId).toBe('string')
    expect(first.value.data.agentId.length).toBeGreaterThan(0)

    const task = getBackgroundAgentTask(first.value.data.agentId)
    expect(task?.type).toBe('async_agent')
    await task?.done
  })

  test('completed output includes tool use count, duration, and tokens', async () => {
    async function* stubQuery() {
      yield {
        type: 'assistant',
        costUSD: 0,
        durationMs: 0,
        uuid: 'a1',
        message: {
          id: 'm1',
          model: 'test',
          role: 'assistant',
          stop_reason: 'stop_sequence',
          stop_sequence: '',
          type: 'message',
          usage: {
            input_tokens: 10,
            output_tokens: 20,
            cache_creation_input_tokens: 3,
            cache_read_input_tokens: 2,
          },
          content: [
            { type: 'tool_use', id: 't1', name: 'Bash', input: {} },
            { type: 'tool_use', id: 't2', name: 'Read', input: {} },
            { type: 'text', text: 'hello', citations: [] },
          ],
        },
      } as any
    }

    const gen = TaskTool.call(
      {
        description: 'fg',
        prompt: 'fg prompt',
        subagent_type: 'general-purpose',
      } as any,
      {
        abortController: new AbortController(),
        readFileTimestamps: {},
        options: {
          safeMode: false,
          forkNumber: 0,
          messageLogName: 'task-tool-test',
          verbose: false,
          model: 'main',
          mcpClients: [],
        },
        __testQuery: stubQuery,
      } as any,
    )

    let result: any = null
    for await (const chunk of gen as any) {
      if (chunk.type === 'result') {
        result = chunk
      }
    }

    expect(result?.data?.status).toBe('completed')
    expect(result.data.prompt).toBe('fg prompt')
    expect(result.data.totalToolUseCount).toBe(2)
    expect(result.data.totalTokens).toBe(35)
    expect(result.data.totalDurationMs).toBeGreaterThanOrEqual(0)
    expect(result.data.usage).toEqual({
      input_tokens: 10,
      output_tokens: 20,
      cache_creation_input_tokens: 3,
      cache_read_input_tokens: 2,
    })
    expect(result.data.content).toEqual([
      { type: 'text', text: 'hello', citations: [] },
    ])
  })
})
