
import { getModelFeatures } from './openai'
import { debug as debugLogger } from '@utils/log/debugLogger'

export interface ConnectionTestResult {
  success: boolean
  message: string
  endpoint?: string
  details?: string
  apiUsed?: 'responses' | 'chat_completions'
  responseTime?: number
}

export interface GPT5TestConfig {
  model: string
  apiKey: string
  baseURL?: string
  maxTokens?: number
  provider?: string
}

export async function testGPT5Connection(
  config: GPT5TestConfig,
): Promise<ConnectionTestResult> {
  const startTime = Date.now()

  if (!config.model || !config.apiKey) {
    return {
      success: false,
      message: 'Invalid configuration',
      details: 'Model name and API key are required',
    }
  }

  const isGPT5 = config.model.toLowerCase().includes('gpt-5')
  const modelFeatures = getModelFeatures(config.model)
  const baseURL = config.baseURL || 'https://api.openai.com/v1'
  const isOfficialOpenAI =
    !config.baseURL || config.baseURL.includes('api.openai.com')

  debugLogger.api('GPT5_CONNECTION_TEST_START', {
    model: config.model,
    baseURL,
    isOfficialOpenAI,
    supportsResponsesAPI: modelFeatures.supportsResponsesAPI,
  })

  if (isGPT5 && modelFeatures.supportsResponsesAPI && isOfficialOpenAI) {
    debugLogger.api('GPT5_CONNECTION_TEST_TRY_RESPONSES', { model: config.model })
    const responsesResult = await testResponsesAPI(config, baseURL, startTime)

    if (responsesResult.success) {
      debugLogger.api('GPT5_CONNECTION_TEST_RESPONSES_OK', { model: config.model })
      return responsesResult
    } else {
      debugLogger.warn('GPT5_CONNECTION_TEST_RESPONSES_FAILED', {
        model: config.model,
        details: responsesResult.details,
      })
    }
  }

  debugLogger.api('GPT5_CONNECTION_TEST_FALLBACK_CHAT_COMPLETIONS', { model: config.model })
  return await testChatCompletionsAPI(config, baseURL, startTime)
}

async function testResponsesAPI(
  config: GPT5TestConfig,
  baseURL: string,
  startTime: number,
): Promise<ConnectionTestResult> {
  const testURL = `${baseURL.replace(/\/+$/, '')}/responses`

  const testPayload = {
    model: config.model,
    input: [
      {
        role: 'user',
        content:
          'Please respond with exactly "YES" (in capital letters) to confirm this connection is working.',
      },
    ],
    max_completion_tokens: Math.max(config.maxTokens || 8192, 8192),
    temperature: 1,
    reasoning: {
      effort: 'low',
    },
  }

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${config.apiKey}`,
  }

  debugLogger.api('GPT5_CONNECTION_TEST_RESPONSES_REQUEST', {
    model: config.model,
    url: testURL,
  })

  try {
    const response = await fetch(testURL, {
      method: 'POST',
      headers,
      body: JSON.stringify(testPayload),
    })

    const responseTime = Date.now() - startTime

    if (response.ok) {
      const data = await response.json()
      debugLogger.api('GPT5_CONNECTION_TEST_RESPONSES_RESPONSE', {
        model: config.model,
        status: response.status,
      })

      let responseContent = ''
      if (data.output_text) {
        responseContent = data.output_text
      } else if (data.output && Array.isArray(data.output)) {
        const messageOutput = data.output.find(item => item.type === 'message')
        if (messageOutput && messageOutput.content) {
          const textContent = messageOutput.content.find(
            c => c.type === 'output_text',
          )
          responseContent = textContent?.text || ''
        }
      }

      const containsYes = responseContent.toLowerCase().includes('yes')

      if (containsYes) {
        return {
          success: true,
          message: '✅ GPT-5 Responses API connection successful',
          endpoint: '/responses',
          details: `Model responded correctly: "${responseContent.trim()}"`,
          apiUsed: 'responses',
          responseTime,
        }
      } else {
        return {
          success: false,
          message: '⚠️ Responses API connected but unexpected response',
          endpoint: '/responses',
          details: `Expected "YES" but got: "${responseContent.trim() || '(empty response)'}"`,
          apiUsed: 'responses',
          responseTime,
        }
      }
    } else {
      const errorData = await response.json().catch(() => null)
      const errorMessage =
        errorData?.error?.message || errorData?.message || response.statusText

      debugLogger.warn('GPT5_CONNECTION_TEST_RESPONSES_ERROR', {
        model: config.model,
        status: response.status,
        error: errorMessage,
      })

      return {
        success: false,
        message: `❌ Responses API failed (${response.status})`,
        endpoint: '/responses',
        details: `Error: ${errorMessage}`,
        apiUsed: 'responses',
        responseTime: Date.now() - startTime,
      }
    }
  } catch (error) {
    debugLogger.warn('GPT5_CONNECTION_TEST_RESPONSES_NETWORK_ERROR', {
      model: config.model,
      error: error instanceof Error ? error.message : String(error),
    })

    return {
      success: false,
      message: '❌ Responses API connection failed',
      endpoint: '/responses',
      details: error instanceof Error ? error.message : String(error),
      apiUsed: 'responses',
      responseTime: Date.now() - startTime,
    }
  }
}

async function testChatCompletionsAPI(
  config: GPT5TestConfig,
  baseURL: string,
  startTime: number,
): Promise<ConnectionTestResult> {
  const testURL = `${baseURL.replace(/\/+$/, '')}/chat/completions`

  const isGPT5 = config.model.toLowerCase().includes('gpt-5')

  const testPayload: any = {
    model: config.model,
    messages: [
      {
        role: 'user',
        content:
          'Please respond with exactly "YES" (in capital letters) to confirm this connection is working.',
      },
    ],
    temperature: isGPT5 ? 1 : 0,
    stream: false,
  }

  if (isGPT5) {
    testPayload.max_completion_tokens = Math.max(config.maxTokens || 8192, 8192)
    delete testPayload.max_tokens
    debugLogger.api('GPT5_CONNECTION_TEST_MAX_COMPLETION_TOKENS', {
      model: config.model,
      max_completion_tokens: testPayload.max_completion_tokens,
    })
  } else {
    testPayload.max_tokens = Math.max(config.maxTokens || 8192, 8192)
  }

  const headers = {
    'Content-Type': 'application/json',
  }

  if (config.provider === 'azure') {
    headers['api-key'] = config.apiKey
  } else {
    headers['Authorization'] = `Bearer ${config.apiKey}`
  }

  debugLogger.api('GPT5_CONNECTION_TEST_CHAT_COMPLETIONS_REQUEST', {
    model: config.model,
    url: testURL,
  })

  try {
    const response = await fetch(testURL, {
      method: 'POST',
      headers,
      body: JSON.stringify(testPayload),
    })

    const responseTime = Date.now() - startTime

    if (response.ok) {
      const data = await response.json()
      debugLogger.api('GPT5_CONNECTION_TEST_CHAT_COMPLETIONS_RESPONSE', {
        model: config.model,
        status: response.status,
      })

      const responseContent = data.choices?.[0]?.message?.content || ''
      const containsYes = responseContent.toLowerCase().includes('yes')

      if (containsYes) {
        return {
          success: true,
          message: `✅ ${isGPT5 ? 'GPT-5' : 'Model'} Chat Completions connection successful`,
          endpoint: '/chat/completions',
          details: `Model responded correctly: "${responseContent.trim()}"`,
          apiUsed: 'chat_completions',
          responseTime,
        }
      } else {
        return {
          success: false,
          message: '⚠️ Chat Completions connected but unexpected response',
          endpoint: '/chat/completions',
          details: `Expected "YES" but got: "${responseContent.trim() || '(empty response)'}"`,
          apiUsed: 'chat_completions',
          responseTime,
        }
      }
    } else {
      const errorData = await response.json().catch(() => null)
      const errorMessage =
        errorData?.error?.message || errorData?.message || response.statusText

      debugLogger.warn('GPT5_CONNECTION_TEST_CHAT_COMPLETIONS_ERROR', {
        model: config.model,
        status: response.status,
        error: errorMessage,
      })

      let details = `Error: ${errorMessage}`
      if (
        response.status === 400 &&
        errorMessage.includes('max_tokens') &&
        isGPT5
      ) {
        details +=
          '\n\n🔧 GPT-5 Fix Applied: This error suggests a parameter compatibility issue. Please check if the provider supports GPT-5 with max_completion_tokens.'
      }

      return {
        success: false,
        message: `❌ Chat Completions failed (${response.status})`,
        endpoint: '/chat/completions',
        details: details,
        apiUsed: 'chat_completions',
        responseTime: Date.now() - startTime,
      }
    }
  } catch (error) {
    debugLogger.warn('GPT5_CONNECTION_TEST_CHAT_COMPLETIONS_NETWORK_ERROR', {
      model: config.model,
      error: error instanceof Error ? error.message : String(error),
    })

    return {
      success: false,
      message: '❌ Chat Completions connection failed',
      endpoint: '/chat/completions',
      details: error instanceof Error ? error.message : String(error),
      apiUsed: 'chat_completions',
      responseTime: Date.now() - startTime,
    }
  }
}

export function validateGPT5Config(config: GPT5TestConfig): {
  valid: boolean
  errors: string[]
} {
  debugLogger.state('GPT5_VALIDATE_CONFIG_CALLED', {
    model: config.model,
    hasApiKey: !!config.apiKey,
    baseURL: config.baseURL,
    provider: config.provider,
  })

  const errors: string[] = []

  if (!config.model) {
    errors.push('Model name is required')
  }

  if (!config.apiKey) {
    errors.push('API key is required')
  }

  const isGPT5 = config.model?.toLowerCase().includes('gpt-5')
  if (isGPT5) {
    debugLogger.state('GPT5_VALIDATE_CONFIG', {
      model: config.model,
      maxTokens: config.maxTokens,
    })

    if (config.maxTokens && config.maxTokens < 1000) {
      errors.push('GPT-5 models typically require at least 1000 max tokens')
    }

    debugLogger.state('GPT5_VALIDATE_CONFIG_NO_PROVIDER_RESTRICTIONS', {
      model: config.model,
    })
  }

  debugLogger.state('GPT5_VALIDATE_CONFIG_RESULT', {
    valid: errors.length === 0,
    errors,
  })

  return {
    valid: errors.length === 0,
    errors,
  }
}
