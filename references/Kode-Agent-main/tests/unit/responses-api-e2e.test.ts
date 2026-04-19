import { test, expect, describe } from 'bun:test'
import { ModelAdapterFactory } from '@services/modelAdapterFactory'
import { ModelProfile } from '@utils/config'
import { testModels, getResponsesAPIModels } from '../testAdapters'
import { processResponsesStream } from '@services/adapters/responsesStreaming'
import { ReadableStream } from 'node:stream/web'


describe('Responses API Tests', () => {
  describe('Responses API-specific functionality', () => {
    const testModel = getResponsesAPIModels(testModels)[0] || testModels[0]

    test('handles Responses API request parameters correctly', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [{ role: 'user', content: 'test' }],
        systemPrompt: ['test system'],
        tools: [],
        maxTokens: 100,
        stream: true,
        temperature: 0.7,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request).toHaveProperty('include')
      expect(request).toHaveProperty('max_output_tokens')
      expect(request).toHaveProperty('input')
      expect(request.stream).toBe(true)

      expect(request).not.toHaveProperty('messages')
      expect(request).not.toHaveProperty('max_tokens')
      expect(request).not.toHaveProperty('max_completion_tokens')
    })

    test('parses Responses API response format correctly', async () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const mockResponseData = {
        id: 'resp-test-123',
        object: 'response',
        created: Date.now(),
        model: testModel.modelName,
        output: [
          {
            type: 'message',
            role: 'assistant',
            content: [
              {
                type: 'text',
                text: 'Mock response for Responses API',
              },
            ],
          },
        ],
        usage: {
          input_tokens: 15,
          output_tokens: 25,
          total_tokens: 40,
        },
      }

      const unifiedResponse = await adapter.parseResponse(mockResponseData)

      expect(unifiedResponse).toBeDefined()
      expect(unifiedResponse.id).toBe('resp-test-123')
      expect(Array.isArray(unifiedResponse.content)).toBe(true)
      expect(unifiedResponse.content.length).toBe(1)
      expect(unifiedResponse.content[0]).toHaveProperty('type', 'text')
      expect(unifiedResponse.content[0]).toHaveProperty(
        'text',
        'Mock response for Responses API',
      )
      expect(unifiedResponse.toolCalls).toBeDefined()
      expect(Array.isArray(unifiedResponse.toolCalls)).toBe(true)
      expect(unifiedResponse.toolCalls.length).toBe(0)
    })

    test('includes reasoning and verbosity parameters when provided', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [{ role: 'user', content: 'Explain this code' }],
        systemPrompt: ['You are an expert'],
        maxTokens: 200,
        reasoningEffort: 'high' as const,
        verbosity: 'high' as const,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request.reasoning).toBeDefined()
      expect(request.reasoning.effort).toBe('high')
      expect(request.text).toBeDefined()
      expect(request.text.verbosity).toBe('high')
    })

    test('converts tool results to function_call_output format', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [
          { role: 'user', content: 'What is this file?' },
          {
            role: 'tool',
            tool_call_id: 'tool_123',
            content: 'This is a TypeScript file',
          },
          { role: 'user', content: 'Please read it' },
        ],
        systemPrompt: ['You are helpful'],
        maxTokens: 100,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request.input).toBeDefined()
      expect(Array.isArray(request.input)).toBe(true)

      const hasFunctionCallOutput = request.input.some(
        (item: any) => item.type === 'function_call_output',
      )
      expect(hasFunctionCallOutput).toBe(true)
    })
  })

  describe('Responses API unique behaviors', () => {
    const testModel = getResponsesAPIModels(testModels)[0] || testModels[0]

    test('joins multiple system prompts with double newlines', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [{ role: 'user', content: 'Hello' }],
        systemPrompt: ['You are a coding assistant', 'Always write clean code'],
        maxTokens: 50,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request.instructions).toBe(
        'You are a coding assistant\n\nAlways write clean code',
      )
    })

    test('respects stream flag for buffered requests', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [{ role: 'user', content: 'Hello' }],
        systemPrompt: ['You are helpful'],
        maxTokens: 100,
        stream: false,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request.stream).toBe(false)
    })

    test('streaming usage events expose unified token format', async () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)
      const encoder = new TextEncoder()
      const streamChunks = [
        'data: {"type":"response.output_text.delta","delta":"Hello"}\n',
        'data: {"type":"response.completed","usage":{"input_tokens":12,"output_tokens":8,"total_tokens":20,"output_tokens_details":{"reasoning_tokens":3}}}\n',
        'data: [DONE]\n',
      ]

      const stream = new ReadableStream({
        start(controller) {
          for (const chunk of streamChunks) {
            controller.enqueue(encoder.encode(chunk))
          }
          controller.close()
        },
      })

      const events: any[] = []
      for await (const event of (adapter as any).parseStreamingResponse({
        body: stream,
        id: 'resp-stream-test',
      })) {
        events.push(event)
      }

      const usageEvent = events.find(event => event.type === 'usage')
      expect(usageEvent).toBeDefined()
      expect(usageEvent.usage).toMatchObject({
        input: 12,
        output: 8,
        total: 20,
        reasoning: 3,
      })

      async function* replayEvents(evts: any[]) {
        for (const evt of evts) {
          yield evt
        }
      }

      const { assistantMessage, rawResponse } = await processResponsesStream(
        replayEvents(events),
        Date.now(),
        'resp-stream-processed',
      )

      expect(assistantMessage.message.usage).toMatchObject({
        input_tokens: 12,
        output_tokens: 8,
        totalTokens: 20,
      })
      expect(rawResponse.id).toBe('resp-stream-test')
    })
  })

  describe('Reasoning Support Tests', () => {
    const testModel = getResponsesAPIModels(testModels)[0] || testModels[0]

    test('includes reasoning and verbosity parameters when provided', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [{ role: 'user', content: 'Solve this complex problem' }],
        systemPrompt: ['You are a helpful assistant'],
        tools: [],
        maxTokens: 100,
        stream: true,
        reasoningEffort: 'high' as const,
        verbosity: 'high' as const,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request).toHaveProperty('reasoning')
      expect(request.reasoning).toBeDefined()
      expect(request.reasoning.effort).toBe('high')

      expect(request).toHaveProperty('include')
      expect(request.include).toContain('reasoning.encrypted_content')

      expect(request).toHaveProperty('text')
      expect(request.text.verbosity).toBe('high')
    })

    test('processes real GPT-5 reasoning stream with reasoning items and text deltas', async () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const reasoningStreamData = [
        'data: {"type":"response.output_item.added","output_index":0,"item":{"id":"rs_123","type":"reasoning","summary":[]}}\n\n',
        'data: {"type":"response.output_item.done","output_index":0,"item":{"id":"rs_123","type":"reasoning","summary":[]}}\n\n',
        'data: {"type":"response.output_item.added","output_index":1,"item":{"id":"msg_123","type":"message","status":"in_progress","content":[],"role":"assistant"}}\n\n',
        'data: {"type":"response.content_part.added","item_id":"msg_123","output_index":1,"content_index":0,"part":{"type":"output_text","text":""}}\n\n',
        'data: {"type":"response.output_text.delta","item_id":"msg_123","output_index":1,"content_index":0,"delta":"Let me think step by step"}\n\n',
        'data: {"type":"response.output_text.delta","item_id":"msg_123","output_index":1,"content_index":0,"delta":"\\n\\nFirst, I need to analyze the problem"}\n\n',
        'data: {"type":"response.output_text.delta","item_id":"msg_123","output_index":1,"content_index":0,"delta":"\\n\\nThe solution is:"}\n\n',
        'data: {"type":"response.output_text.delta","item_id":"msg_123","output_index":1,"content_index":0,"delta":" $0.05"}\n\n',
        'data: {"type":"response.completed"}\n\n',
        'data: [DONE]\n\n',
      ].join('')

      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(reasoningStreamData))
          controller.close()
        },
      })

      const response = new Response(stream as any)
      const events = []

      for await (const event of adapter.parseStreamingResponse(response)) {
        events.push(event)
      }

      const textDeltas = events.filter(e => e.type === 'text_delta')
      expect(textDeltas.length).toBeGreaterThan(0)

      const fullContent = textDeltas.map(e => e.delta).join('')
      expect(fullContent).toContain('Let me think step by step')
      expect(fullContent).toContain('First, I need to analyze the problem')
      expect(fullContent).toContain('The solution is:')
      expect(fullContent).toContain('$0.05')

      expect(fullContent).toMatch(
        /Let me think step by step\n\nFirst, I need to analyze the problem\n\nThe solution is: \$0\.05/,
      )
    })

    test('processes non-streaming response with real GPT-5 reasoning structure', async () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const mockResponse = {
        id: 'resp-test-reasoning',
        output_text:
          '$0.05\n\nReason: Let the ball cost x. Then the bat costs x + 1.00. So x + (x + 1.00) = 1.10 ⇒ 2x = 0.10 ⇒ x = 0.05. The intuitive $0.10 would make the total $1.20, not $1.10.',
        usage: {
          input_tokens: 5062,
          output_tokens: 340,
          total_tokens: 5402,
          output_tokens_details: {
            reasoning_tokens: 256,
          },
        },
      }

      const result = await adapter.parseResponse(mockResponse)

      expect(result.content).toBeDefined()
      const contentText = Array.isArray(result.content)
        ? result.content.map(c => c.text).join('')
        : result.content

      expect(contentText).toContain('$0.05')
      expect(contentText).toContain('Reason: Let the ball cost x')

      expect(result.usage.reasoningTokens).toBe(256)
    })

    test('handles response without reasoning content gracefully', async () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const mockResponse = {
        id: 'resp-no-reasoning',
        output_text: 'Simple answer without reasoning.',
        usage: {
          input_tokens: 10,
          output_tokens: 5,
          total_tokens: 15,
        },
      }

      const result = await adapter.parseResponse(mockResponse)

      expect(result.content).toBeDefined()
      const contentText = Array.isArray(result.content)
        ? result.content.map(c => c.text).join('')
        : result.content

      expect(contentText).toBe('Simple answer without reasoning.')

      expect(result.usage.reasoningTokens).toBeUndefined()
    })

    test('handles reasoning effort parameter validation', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const effortLevels = ['minimal', 'low', 'medium', 'high'] as const

      effortLevels.forEach(effort => {
        const request = adapter.createRequest({
          messages: [{ role: 'user', content: 'test' }],
          systemPrompt: [],
          tools: [],
          maxTokens: 100,
          reasoningEffort: effort,
        })

        expect(request.reasoning.effort).toBe(effort)
        expect(request.include).toContain('reasoning.encrypted_content')
      })
    })
  })
})
