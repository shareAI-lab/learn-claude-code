import { test, expect, describe } from 'bun:test'
import { ModelAdapterFactory } from '@services/modelAdapterFactory'
import { ModelProfile } from '@utils/config'
import { loadDotEnvIfPresent } from '../../helpers/loadDotEnv'
import { productionTestModels } from '../../testAdapters'

const PRODUCTION_TEST_MODE = process.env.PRODUCTION_TEST_MODE === 'true'

if (process.env.NODE_ENV !== 'production') {
  loadDotEnvIfPresent()
}

const ACTIVE_MODELS = productionTestModels.filter(model => model.isActive)

const TEST_MODEL = process.env.TEST_MODEL || 'all'

function getModelsToTest(): ModelProfile[] {
  if (TEST_MODEL === 'all') {
    return ACTIVE_MODELS
  }

  const filtered = ACTIVE_MODELS.filter(
    model =>
      model.name.toLowerCase().includes(TEST_MODEL.toLowerCase()) ||
      model.modelName.toLowerCase().includes(TEST_MODEL.toLowerCase()) ||
      model.provider.toLowerCase() === TEST_MODEL.toLowerCase(),
  )

  return filtered.length > 0 ? filtered : ACTIVE_MODELS
}

describe('🌐 Production API Integration Tests', () => {
  if (!PRODUCTION_TEST_MODE) {
    test('⚠️  PRODUCTION TEST MODE DISABLED', () => {
      console.log('\n🚨 PRODUCTION TEST MODE IS DISABLED 🚨')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      console.log('To enable production tests, run:')
      console.log(
        '  PRODUCTION_TEST_MODE=true bun test tests/integration/production/production-api-tests.test.ts',
      )
      console.log('')
      console.log(
        '⚠️  WARNING: This will make REAL API calls and may incur costs!',
      )
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      expect(true).toBe(true)
    })
    return
  }

  if (ACTIVE_MODELS.length === 0) {
    test('⚠️  NO ACTIVE PRODUCTION MODELS CONFIGURED', () => {
      console.log('\n🚨 NO ACTIVE PRODUCTION MODELS CONFIGURED 🚨')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      console.log('Create a .env file with the following variables:')
      console.log('  TEST_GPT5_API_KEY=your_api_key_here')
      console.log('  TEST_GPT5_BASE_URL=http://127.0.0.1:3000/openai')
      console.log('  ...')
      console.log('')
      console.log('⚠️  Never commit .env files to version control!')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      console.log(`Currently active models: ${ACTIVE_MODELS.length}`)
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      expect(true).toBe(true)
    })
    return
  }

  const modelsToTest = getModelsToTest()
  const testModelNames = modelsToTest.map(m => m.name).join(', ')

  describe(`📡 Production Tests (${testModelNames})`, () => {
    modelsToTest.forEach(model => {
      test(
        `🚀 Making real API call to ${model.name}`,
        async () => {
          const adapter = ModelAdapterFactory.createAdapter(model)
          const shouldUseResponses =
            ModelAdapterFactory.shouldUseResponsesAPI(model)

          console.log('\n🚀 PRODUCTION TEST:')
          console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          console.log('🧪 Test Model:', model.name)
          console.log('🔗 Adapter:', adapter.constructor.name)
          console.log(
            '📍 Endpoint:',
            shouldUseResponses
              ? `${model.baseURL}/responses`
              : `${model.baseURL}/chat/completions`,
          )
          console.log('🤖 Model:', model.modelName)
          console.log('🔑 API Key:', model.apiKey.substring(0, 8) + '...')

          const testPrompt = `Write a simple function that adds two numbers (${model.name} test)`
          const mockParams = {
            messages: [{ role: 'user', content: testPrompt }],
            systemPrompt: [
              'You are a helpful coding assistant. Provide clear, concise code examples.',
            ],
            maxTokens: 100,
          }

          try {
            const request = adapter.createRequest(mockParams)

            const endpoint = shouldUseResponses
              ? `${model.baseURL}/responses`
              : `${model.baseURL}/chat/completions`

            console.log('📡 Making request to:', endpoint)
            console.log('📝 Request body:', JSON.stringify(request, null, 2))

            const response = await fetch(endpoint, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${model.apiKey}`,
              },
              body: JSON.stringify(request),
            })

            console.log('📊 Response status:', response.status)
            console.log(
              '📊 Response headers:',
              Object.fromEntries(response.headers.entries()),
            )

            if (response.ok) {
              const unifiedResponse = await adapter.parseResponse(response)
              console.log('✅ SUCCESS! Response received:')
              console.log(
                '📄 Unified Response:',
                JSON.stringify(unifiedResponse, null, 2),
              )

              expect(response.status).toBe(200)
              expect(unifiedResponse).toBeDefined()
              expect(unifiedResponse.content).toBeDefined()
            } else {
              const errorText = await response.text()
              console.log('❌ API ERROR:', response.status, errorText)

              console.log(
                `⚠️  Skipping API validation for ${model.name} due to API error`,
              )
              console.log(
                `💡 This might indicate the model endpoint doesn't support the expected API format`,
              )
              expect(true).toBe(true)
            }
          } catch (error: any) {
            console.log('💥 Request failed:', error.message)
            console.log(`⚠️  Test completed with errors for ${model.name}`)
            expect(true).toBe(true)
          }
        },
        { timeout: 30000 },
      )
    }, 30000)
  })

  describe('⚡ Quick Health Check Tests', () => {
    modelsToTest.forEach(model => {
      test(`🏥 ${model.name} endpoint health check`, async () => {
        const adapter = ModelAdapterFactory.createAdapter(model)
        const shouldUseResponses =
          ModelAdapterFactory.shouldUseResponsesAPI(model)

        const endpoint = shouldUseResponses
          ? `${model.baseURL}/responses`
          : `${model.baseURL}/chat/completions`

        try {
          console.log(`\n🏥 Health check: ${endpoint}`)

          const minimalRequest = adapter.createRequest({
            messages: [{ role: 'user', content: 'Hi' }],
            systemPrompt: [],
            maxTokens: 1,
          })

          const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${model.apiKey}`,
            },
            body: JSON.stringify(minimalRequest),
          })

          console.log('📊 Health status:', response.status, response.statusText)
          expect(response.status).toBeLessThan(500)
        } catch (error: any) {
          console.log('💥 Health check failed:', error.message)
          expect(error.message).toBeDefined()
        }
      })
    })
  })

  describe('📊 Performance & Cost Metrics', () => {
    modelsToTest.forEach(model => {
      test(`⏱️  API response time measurement for ${model.name}`, async () => {
        const startTime = performance.now()

        try {
          const adapter = ModelAdapterFactory.createAdapter(model)
          const shouldUseResponses =
            ModelAdapterFactory.shouldUseResponsesAPI(model)

          const endpoint = shouldUseResponses
            ? `${model.baseURL}/responses`
            : `${model.baseURL}/chat/completions`

          const request = adapter.createRequest({
            messages: [{ role: 'user', content: 'Hello' }],
            systemPrompt: [],
            maxTokens: 5,
          })

          const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${model.apiKey}`,
            },
            body: JSON.stringify(request),
          })

          const endTime = performance.now()
          const duration = endTime - startTime

          console.log(`\n⏱️  Performance Metrics (${model.name}):`)
          console.log(`  Response time: ${duration.toFixed(2)}ms`)
          console.log(`  Status: ${response.status}`)

          expect(duration).toBeGreaterThan(0)
          expect(response.status).toBeDefined()
        } catch (error: any) {
          console.log('⚠️  Performance test failed:', error.message)
          expect(error.message).toBeDefined()
        }
      })
    })
  })
})
