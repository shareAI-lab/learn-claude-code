import { test, expect, describe } from 'bun:test'
import { ModelAdapterFactory } from '@services/modelAdapterFactory'
import { getModelCapabilities } from '@constants/modelCapabilities'
import { testModels, getChatCompletionsModels } from '../testAdapters'


describe('Chat Completions API Tests', () => {
  describe('Chat Completions API-specific functionality', () => {
    const testModel = getChatCompletionsModels(testModels)[0] || testModels[0]

    test('handles Chat Completions request parameters correctly', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)
      const capabilities = getModelCapabilities(testModel.modelName)

      const unifiedParams = {
        messages: [
          { role: 'user', content: 'Write a simple JavaScript function' },
        ],
        systemPrompt: ['You are a helpful coding assistant.'],
        tools: [],
        maxTokens: 100,
        stream: capabilities.streaming.supported,
        temperature: 0.7,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request).toHaveProperty('model', testModel.modelName)
      expect(request).toHaveProperty('messages')
      expect(request.messages).toBeInstanceOf(Array)
      expect(request.messages.some((msg: any) => msg.role === 'user')).toBe(
        true,
      )
      expect(request.messages.some((msg: any) => msg.role === 'system')).toBe(
        true,
      )

      const hasMaxTokens =
        request.hasOwnProperty('max_tokens') ||
        request.hasOwnProperty('max_completion_tokens')
      expect(hasMaxTokens).toBe(true)

      expect(request).not.toHaveProperty('include')
      expect(request).not.toHaveProperty('max_output_tokens')
      expect(request).not.toHaveProperty('reasoning')
    })

    test('parses Chat Completions response format correctly', async () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const mockResponseData = {
        id: 'chatcmpl-test-123',
        object: 'chat.completion',
        created: Date.now(),
        model: testModel.modelName,
        choices: [
          {
            index: 0,
            message: {
              role: 'assistant',
              content: 'function hello() { return "Hello World"; }',
            },
            finish_reason: 'stop',
          },
        ],
        usage: {
          prompt_tokens: 25,
          completion_tokens: 15,
          total_tokens: 40,
        },
      }

      const unifiedResponse = await adapter.parseResponse(mockResponseData)

      expect(unifiedResponse).toBeDefined()
      expect(unifiedResponse.id).toBe('chatcmpl-test-123')
      expect(unifiedResponse.content).toBe(
        'function hello() { return "Hello World"; }',
      )
      expect(unifiedResponse.toolCalls).toBeDefined()
      expect(Array.isArray(unifiedResponse.toolCalls)).toBe(true)
      expect(unifiedResponse.toolCalls.length).toBe(0)
    })

    test('handles Chat Completions tool results correctly', () => {
      const adapter = ModelAdapterFactory.createAdapter(testModel)

      const unifiedParams = {
        messages: [
          { role: 'user', content: 'What is this file?' },
          {
            role: 'tool',
            tool_call_id: 'tool_123',
            content: 'This is a TypeScript file',
          },
          { role: 'assistant', content: 'I need to check the file first' },
          { role: 'user', content: 'Please read it' },
        ],
        systemPrompt: ['You are helpful'],
        maxTokens: 100,
      }

      const request = adapter.createRequest(unifiedParams)

      expect(request.messages).toBeDefined()
      expect(Array.isArray(request.messages)).toBe(true)
      expect(request.messages.length).toBeGreaterThan(0)

      const hasToolMessage = request.messages.some(
        (msg: any) => msg.role === 'tool',
      )
      const hasUserMessage = request.messages.some(
        (msg: any) => msg.role === 'user',
      )
      const hasAssistantMessage = request.messages.some(
        (msg: any) => msg.role === 'assistant',
      )

      expect(hasToolMessage).toBe(true)
      expect(hasUserMessage).toBe(true)
      expect(hasAssistantMessage).toBe(true)
    })
  })
})
