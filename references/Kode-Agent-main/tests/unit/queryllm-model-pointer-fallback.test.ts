import { describe, expect, test } from 'bun:test'
import { queryLLM } from '@services/llm'

describe('queryLLM model pointer fallback (Reference CLI parity)', () => {
  test('falls back when resolveModelWithInfo fails (no throw)', async () => {
    const fallbackModelName = 'fallback-model'

    const fakeModelManager = {
      resolveModelWithInfo() {
        return {
          success: false,
          profile: null,
          error:
            "Model pointer 'quick' points to invalid model 'bad-model'. Use /model to reconfigure.",
        }
      },
      resolveModel() {
        return {
          modelName: fallbackModelName,
          provider: 'openai',
          name: 'Fallback',
          isActive: true,
        }
      },
    }

    let resolvedModelParam: string | undefined

    async function stubQueryLLMWithPromptCaching(
      _messages: any,
      _systemPrompt: any,
      _maxThinkingTokens: any,
      _tools: any,
      _signal: any,
      options: any,
    ) {
      resolvedModelParam = options.model
      return {
        type: 'assistant',
        uuid: 'a1',
        costUSD: 0,
        durationMs: 0,
        message: {
          id: 'm1',
          type: 'message',
          role: 'assistant',
          model: options.model,
          stop_reason: 'end_turn',
          stop_sequence: null,
          usage: {
            input_tokens: 0,
            output_tokens: 0,
            cache_creation_input_tokens: 0,
            cache_read_input_tokens: 0,
          },
          content: [{ type: 'text', text: 'ok', citations: [] }],
        },
      }
    }

    const message = await queryLLM(
      [
        {
          type: 'user',
          uuid: 'u1',
          message: { role: 'user', content: 'hi' },
        },
      ] as any,
      ['system'],
      0,
      [],
      new AbortController().signal,
      {
        safeMode: false,
        model: 'quick',
        prependCLISysprompt: false,
        __testModelManager: fakeModelManager,
        __testQueryLLMWithPromptCaching: stubQueryLLMWithPromptCaching,
      } as any,
    )

    expect(resolvedModelParam).toBe(fallbackModelName)
    expect(message.message.model).toBe(fallbackModelName)
  })
})
