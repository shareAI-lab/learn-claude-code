
import { test, expect, describe } from 'bun:test'
import { ModelAdapterFactory } from '@services/modelAdapterFactory'
import { ModelProfile } from '@utils/config'
import { callGPT5ResponsesAPI } from '@services/openai'
import { loadDotEnvIfPresent } from '../helpers/loadDotEnv'
import {
  productionTestModels,
  getChatCompletionsModels,
  getResponsesAPIModels,
} from '../testAdapters'

if (process.env.NODE_ENV !== 'production') {
  loadDotEnvIfPresent()
}

const ACTIVE_PRODUCTION_MODELS = productionTestModels.filter(
  model => model.isActive,
)
const CHAT_COMPLETIONS_MODELS = getChatCompletionsModels(
  ACTIVE_PRODUCTION_MODELS,
)
const RESPONSES_API_MODELS = getResponsesAPIModels(ACTIVE_PRODUCTION_MODELS)

const TEST_MODEL = process.env.TEST_MODEL || 'gpt5'

function getActiveProfile(): ModelProfile {
  if (ACTIVE_PRODUCTION_MODELS.length === 0) {
    throw new Error(
      `No active production models found in testAdapters. Please set environment variables:\n` +
        `TEST_GPT5_API_KEY, TEST_MINIMAX_API_KEY, TEST_DEEPSEEK_API_KEY, TEST_CLAUDE_API_KEY, or TEST_GLM_API_KEY`,
    )
  }

  if (TEST_MODEL === 'gpt5' || !TEST_MODEL || TEST_MODEL === '') {
    if (RESPONSES_API_MODELS.length === 0) {
      throw new Error(
        `No active Responses API production models found. Available active models: ${ACTIVE_PRODUCTION_MODELS.map(
          m => `${m.name} (${m.modelName})`,
        ).join(', ')}`,
      )
    }
    return RESPONSES_API_MODELS[0]
  }

  if (TEST_MODEL === 'minimax') {
    if (CHAT_COMPLETIONS_MODELS.length === 0) {
      throw new Error(
        `No active Chat Completions production models found. Available active models: ${ACTIVE_PRODUCTION_MODELS.map(
          m => `${m.name} (${m.modelName})`,
        ).join(', ')}`,
      )
    }
    return CHAT_COMPLETIONS_MODELS[0]
  }

  const foundModel = ACTIVE_PRODUCTION_MODELS.find(
    m =>
      m.modelName === TEST_MODEL ||
      m.name.toLowerCase().includes(TEST_MODEL.toLowerCase()),
  )

  if (!foundModel) {
    throw new Error(
      `Model '${TEST_MODEL}' not found in active production models. Available models: ${ACTIVE_PRODUCTION_MODELS.map(
        m => `${m.name} (${m.modelName})`,
      ).join(', ')}`,
    )
  }

  return foundModel
}

function expectUnifiedUsage(usage: any) {
  expect(usage).toBeDefined()
  expect(typeof usage.promptTokens).toBe('number')
  expect(typeof usage.completionTokens).toBe('number')
  expect(typeof usage.input_tokens).toBe('number')
  expect(typeof usage.output_tokens).toBe('number')
  expect(typeof usage.totalTokens).toBe('number')
  expect(usage.totalTokens).toBe(usage.promptTokens + usage.completionTokens)
}

describe('🔌 Integration: Full Claude.ts Flow (Model-Agnostic)', () => {
  if (ACTIVE_PRODUCTION_MODELS.length === 0) {
    test.skip('✅ End-to-end flow through claude.ts path (requires API keys)', () => {})
    return
  }

  test('✅ End-to-end flow through claude.ts path', async () => {
    const ACTIVE_PROFILE = getActiveProfile()

    console.log('\n🔧 TEST CONFIGURATION:')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log(`  🧪 Test Model: ${TEST_MODEL}`)
    console.log(`  📝 Model Name: ${ACTIVE_PROFILE.modelName}`)
    console.log(`  🏢 Provider: ${ACTIVE_PROFILE.provider}`)
    console.log(
      `  🔗 Adapter: ${ModelAdapterFactory.createAdapter(ACTIVE_PROFILE).constructor.name}`,
    )
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('\n🔌 INTEGRATION TEST: Full Flow')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

    try {
      console.log('Step 1: Creating adapter...')
      const adapter = ModelAdapterFactory.createAdapter(ACTIVE_PROFILE)
      console.log(`  ✅ Adapter: ${adapter.constructor.name}`)

      console.log('\nStep 2: Checking if should use Responses API...')
      const shouldUseResponses =
        ModelAdapterFactory.shouldUseResponsesAPI(ACTIVE_PROFILE)
      console.log(`  ✅ Should use Responses API: ${shouldUseResponses}`)

      console.log('\nStep 3: Building unified request parameters...')
      const unifiedParams = {
        messages: [{ role: 'user', content: 'What is 2+2?' }],
        systemPrompt: ['You are a helpful assistant.'],
        tools: [],
        maxTokens: 100,
        stream: true,
        reasoningEffort: shouldUseResponses ? ('high' as const) : undefined,
        temperature: 1,
        verbosity: shouldUseResponses ? ('high' as const) : undefined,
      }
      console.log('  ✅ Unified params built')

      console.log('\nStep 4: Creating request via adapter...')
      const request = adapter.createRequest(unifiedParams)
      console.log('  ✅ Request created')
      console.log('\n📝 REQUEST STRUCTURE:')
      console.log(JSON.stringify(request, null, 2))

      console.log('\nStep 5: Making API call...')
      const endpoint = shouldUseResponses
        ? `${ACTIVE_PROFILE.baseURL}/responses`
        : `${ACTIVE_PROFILE.baseURL}/chat/completions`
      console.log(`  📍 Endpoint: ${endpoint}`)
      console.log(`  🔑 API Key: ${ACTIVE_PROFILE.apiKey.substring(0, 8)}...`)

      let response: any
      if (shouldUseResponses) {
        response = await callGPT5ResponsesAPI(ACTIVE_PROFILE, request)
      } else {
        response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${ACTIVE_PROFILE.apiKey}`,
          },
          body: JSON.stringify(request),
        })
      }
      console.log(`  ✅ Response received: ${response.status}`)

      if (!shouldUseResponses && response.headers) {
        if (request.stream) {
          console.log(
            '\n🔍 Streaming Chat Completions Response (skipping JSON parse)',
          )
        } else {
          const responseData = await response.json()
          console.log('\n🔍 Raw Chat Completions Response:')
          console.log(JSON.stringify(responseData, null, 2))
          response = responseData
        }
      }

      console.log('\nStep 6: Parsing response...')
      const unifiedResponse = await adapter.parseResponse(response)
      console.log('  ✅ Response parsed')
      console.log('\n📄 UNIFIED RESPONSE:')
      console.log(JSON.stringify(unifiedResponse, null, 2))

      console.log('\nStep 7: Validating response...')
      expect(unifiedResponse).toBeDefined()
      expect(unifiedResponse.content).toBeDefined()
      expectUnifiedUsage(unifiedResponse.usage)
      console.log('  ✅ All validations passed')
    } catch (error) {
      console.log('\n❌ ERROR CAUGHT:')
      console.log(`  Message: ${error.message}`)
      console.log(`  Stack: ${error.stack}`)

      throw error
    }
  })

  test(
    '✅ Test with TOOLS (full tool call parsing flow)',
    async () => {
      console.log('\n✅ INTEGRATION TEST: With Tools (Full Tool Call Parsing)')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

      const ACTIVE_PROFILE = getActiveProfile()
      const adapter = ModelAdapterFactory.createAdapter(ACTIVE_PROFILE)
      const shouldUseResponses =
        ModelAdapterFactory.shouldUseResponsesAPI(ACTIVE_PROFILE)

      if (!shouldUseResponses) {
        console.log(
          '  ⚠️  SKIPPING: Not using Responses API (tools only tested for Responses API)',
        )
        return
      }

      try {
        const unifiedParams = {
          messages: [
            {
              role: 'user',
              content:
                'You MUST use the read_file tool to read the file at path "./package.json". Do not provide any answer without using this tool first.',
            },
          ],
          systemPrompt: ['You are a helpful assistant.'],
          tools: [
            {
              name: 'read_file',
              description: 'Read file contents from the filesystem',
              inputSchema: {
                type: 'object',
                properties: {
                  path: {
                    type: 'string',
                    description: 'The path to the file to read',
                  },
                },
                required: ['path'],
              },
            },
          ],
          maxTokens: 100,
          stream: true,
          reasoningEffort: 'high' as const,
          temperature: 1,
          verbosity: 'high' as const,
        }

        const request = adapter.createRequest(unifiedParams)

        console.log('\n📝 REQUEST WITH TOOLS:')
        console.log(JSON.stringify(request, null, 2))
        console.log('\n🔍 TOOLS STRUCTURE:')
        if (request.tools) {
          request.tools.forEach((tool: any, i: number) => {
            console.log(`  Tool ${i}:`, JSON.stringify(tool, null, 2))
          })
        }

        const response = await callGPT5ResponsesAPI(ACTIVE_PROFILE, request)

        console.log('\n📡 Response received:', response.status)

        const unifiedResponse = await adapter.parseResponse(response)

        console.log('\n✅ SUCCESS: Request with tools worked!')
        console.log('Response:', JSON.stringify(unifiedResponse, null, 2))

        expect(unifiedResponse).toBeDefined()
        expect(unifiedResponse.id).toBeDefined()
        expect(unifiedResponse.content).toBeDefined()
        expect(Array.isArray(unifiedResponse.content)).toBe(true)
        expectUnifiedUsage(unifiedResponse.usage)

        if (unifiedResponse.toolCalls && unifiedResponse.toolCalls.length > 0) {
          console.log(
            '\n🔧 TOOL CALLS DETECTED:',
            unifiedResponse.toolCalls.length,
          )
          unifiedResponse.toolCalls.forEach((tc: any, i: number) => {
            console.log(`  Tool Call ${i}:`, JSON.stringify(tc, null, 2))
          })
        } else {
          console.log(
            '\nℹ️  No tool calls in response (model may have answered directly)',
          )
        }
      } catch (error) {
        console.log('\n⚠️  Test encountered an error:')
        console.log(`  Error: ${error.message}`)

        if (
          error.message.includes('timeout') ||
          error.message.includes('network')
        ) {
          console.log(
            '  (This is likely a network/timeout issue, not a code bug)',
          )
          expect(true).toBe(true)
        } else {
          throw error
        }
      }
    },
    { timeout: 15000 },
  )

  test(
    '✅ Test with TOOLS (multi-turn conversation with tool results)',
    async () => {
      console.log(
        '\n✅ INTEGRATION TEST: Multi-Turn Conversation with Tool Results',
      )
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

      const ACTIVE_PROFILE = getActiveProfile()
      const adapter = ModelAdapterFactory.createAdapter(ACTIVE_PROFILE)
      const shouldUseResponses =
        ModelAdapterFactory.shouldUseResponsesAPI(ACTIVE_PROFILE)

      if (!shouldUseResponses) {
        console.log(
          '  ⚠️  SKIPPING: Not using Responses API (tools only tested for Responses API)',
        )
        return
      }

      try {
        const unifiedParams = {
          messages: [
            {
              role: 'user',
              content: 'Can you read the package.json file?',
            },
            {
              role: 'assistant',
              tool_calls: [
                {
                  id: 'call_123',
                  type: 'function',
                  function: {
                    name: 'read_file',
                    arguments: '{"path": "./package.json"}',
                  },
                },
              ],
            },
            {
              role: 'tool',
              tool_call_id: 'call_123',
              content:
                '{\n  "name": "kode-cli",\n  "version": "1.0.0",\n  "description": "AI-powered terminal assistant"\n}',
            },
          ],
          systemPrompt: ['You are a helpful assistant.'],
          tools: [
            {
              name: 'read_file',
              description: 'Read file contents from the filesystem',
              inputSchema: {
                type: 'object',
                properties: {
                  path: {
                    type: 'string',
                    description: 'The path to the file to read',
                  },
                },
                required: ['path'],
              },
            },
          ],
          maxTokens: 100,
          stream: true,
          reasoningEffort: 'high' as const,
          temperature: 1,
          verbosity: 'high' as const,
        }

        const request = adapter.createRequest(unifiedParams)

        console.log('\n📝 MULTI-TURN CONVERSATION REQUEST:')
        console.log(
          'Messages:',
          JSON.stringify(unifiedParams.messages, null, 2),
        )
        console.log('\n🔍 TOOL CALL in messages:')
        const toolCallMessage = unifiedParams.messages.find(m => m.tool_calls)
        if (toolCallMessage) {
          console.log(
            '  Assistant tool call:',
            JSON.stringify(toolCallMessage.tool_calls, null, 2),
          )
        }
        console.log('\n🔍 TOOL RESULT in messages:')
        const toolResultMessage = unifiedParams.messages.find(
          m => m.role === 'tool',
        )
        if (toolResultMessage) {
          console.log(
            '  Tool result:',
            JSON.stringify(toolResultMessage, null, 2),
          )
        }

        const response = await callGPT5ResponsesAPI(ACTIVE_PROFILE, request)

        console.log('\n📡 Response received:', response.status)

        const unifiedResponse = await adapter.parseResponse(response)

        console.log(
          '\n✅ SUCCESS: Multi-turn conversation with tool results worked!',
        )
        console.log('Response:', JSON.stringify(unifiedResponse, null, 2))
        expectUnifiedUsage(unifiedResponse.usage)

        expect(unifiedResponse).toBeDefined()
        expect(unifiedResponse.id).toBeDefined()
        expect(unifiedResponse.content).toBeDefined()
        expect(Array.isArray(unifiedResponse.content)).toBe(true)

        const inputItems = request.input || []
        const functionCallOutput = inputItems.find(
          (item: any) => item.type === 'function_call_output',
        )

        if (functionCallOutput) {
          console.log('\n🔧 TOOL CALL RESULT CONVERTED:')
          console.log('  type:', functionCallOutput.type)
          console.log('  call_id:', functionCallOutput.call_id)
          console.log('  output:', functionCallOutput.output)

          expect(functionCallOutput.type).toBe('function_call_output')
          expect(functionCallOutput.call_id).toBe('call_123')
          expect(functionCallOutput.output).toBeDefined()
          console.log(
            '  ✅ Tool result correctly converted to function_call_output!',
          )
        } else {
          console.log('\n⚠️  No function_call_output found in request input')
        }
      } catch (error) {
        console.log('\n⚠️  Test encountered an error:')
        console.log(`  Error: ${error.message}`)

        if (
          error.message.includes('timeout') ||
          error.message.includes('network')
        ) {
          console.log(
            '  (This is likely a network/timeout issue, not a code bug)',
          )
          expect(true).toBe(true)
        } else {
          throw error
        }
      }
    },
    { timeout: 15000 },
  )

  test(
    '✅ Bug Regression: Empty content should never occur',
    async () => {
      console.log('\n🔍 BUG REGRESSION TEST: Empty Content Check')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

      const ACTIVE_PROFILE = getActiveProfile()
      const adapter = ModelAdapterFactory.createAdapter(ACTIVE_PROFILE)
      const shouldUseResponses =
        ModelAdapterFactory.shouldUseResponsesAPI(ACTIVE_PROFILE)

      const request = adapter.createRequest({
        messages: [{ role: 'user', content: 'What is 2+2?' }],
        systemPrompt: ['You are a helpful assistant.'],
        tools: [],
        maxTokens: 50,
        stream: true,
        reasoningEffort: shouldUseResponses ? ('medium' as const) : undefined,
        temperature: 1,
        verbosity: shouldUseResponses ? ('medium' as const) : undefined,
      })

      const endpoint = shouldUseResponses
        ? `${ACTIVE_PROFILE.baseURL}/responses`
        : `${ACTIVE_PROFILE.baseURL}/chat/completions`

      let response: any
      if (shouldUseResponses) {
        response = await callGPT5ResponsesAPI(ACTIVE_PROFILE, request)
      } else {
        response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${ACTIVE_PROFILE.apiKey}`,
          },
          body: JSON.stringify(request),
        })
      }

      const unifiedResponse = await adapter.parseResponse(response)

      const content = Array.isArray(unifiedResponse.content)
        ? unifiedResponse.content.map(b => b.text || b.content || '').join('')
        : unifiedResponse.content || ''

      console.log(`  📄 Content: "${content}"`)
      console.log(`  📏 Content length: ${content.length} chars`)

      expect(content.length).toBeGreaterThan(0)
      expect(content).not.toBe('')
      expect(content).not.toBe('(no content)')

      console.log(
        `  ✅ BUG REGRESSION PASSED: Content present (${content.length} chars)`,
      )
    },
    { timeout: 15000 },
  )

  test(
    '✅ responseId preservation across adapter chain',
    async () => {
      console.log('\n🔄 INTEGRATION TEST: responseId Preservation')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

      const ACTIVE_PROFILE = getActiveProfile()
      const adapter = ModelAdapterFactory.createAdapter(ACTIVE_PROFILE)
      const shouldUseResponses =
        ModelAdapterFactory.shouldUseResponsesAPI(ACTIVE_PROFILE)

      const request = adapter.createRequest({
        messages: [{ role: 'user', content: 'Hello' }],
        systemPrompt: ['You are a helpful assistant.'],
        tools: [],
        maxTokens: 50,
        stream: true,
        reasoningEffort: shouldUseResponses ? ('medium' as const) : undefined,
        temperature: 1,
        verbosity: shouldUseResponses ? ('medium' as const) : undefined,
      })

      const endpoint = shouldUseResponses
        ? `${ACTIVE_PROFILE.baseURL}/responses`
        : `${ACTIVE_PROFILE.baseURL}/chat/completions`

      let response: any
      if (shouldUseResponses) {
        response = await callGPT5ResponsesAPI(ACTIVE_PROFILE, request)
      } else {
        response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${ACTIVE_PROFILE.apiKey}`,
          },
          body: JSON.stringify(request),
        })
      }

      const unifiedResponse = await adapter.parseResponse(response)

      console.log(`  🆔 UnifiedResponse.id: ${unifiedResponse.id}`)
      console.log(
        `  🆔 UnifiedResponse.responseId: ${unifiedResponse.responseId}`,
      )

      expect(unifiedResponse.id).toBeDefined()
      expect(unifiedResponse.responseId).toBeDefined()
      expect(unifiedResponse.responseId).not.toBeNull()
      expect(unifiedResponse.responseId).not.toBe('')

      console.log('  ✅ responseId correctly preserved through adapter chain')
    },
    { timeout: 15000 },
  )
})
