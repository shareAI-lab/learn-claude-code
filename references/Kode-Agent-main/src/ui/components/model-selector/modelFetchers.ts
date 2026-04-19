import { fetchCustomModels } from '@services/openai'
import { debug as debugLogger } from '@utils/log/debugLogger'

import type { ModelInfo } from './types'

type SetModelLoadError = (message: string) => void

async function fetchAnthropicModels(baseURL: string, apiKey: string) {
  try {
    const response = await fetch(`${baseURL}/v1/models`, {
      method: 'GET',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
    })

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error(
          'Invalid API key. Please check your API key and try again.',
        )
      } else if (response.status === 403) {
        throw new Error('API key does not have permission to access models.')
      } else if (response.status === 404) {
        throw new Error(
          'API endpoint not found. This provider may not support model listing.',
        )
      } else if (response.status === 429) {
        throw new Error(
          'Too many requests. Please wait a moment and try again.',
        )
      } else if (response.status >= 500) {
        throw new Error(
          'API service is temporarily unavailable. Please try again later.',
        )
      } else {
        throw new Error(`Unable to connect to API (${response.status}).`)
      }
    }

    const data = await response.json()

    let models = []
    if (data && data.data && Array.isArray(data.data)) {
      models = data.data
    } else if (Array.isArray(data)) {
      models = data
    } else if (data && data.models && Array.isArray(data.models)) {
      models = data.models
    } else {
      throw new Error('API returned unexpected response format.')
    }

    return models
  } catch (error) {
    if (
      error instanceof Error &&
      (error.message.includes('API key') ||
        error.message.includes('API endpoint') ||
        error.message.includes('API service') ||
        error.message.includes('response format'))
    ) {
      throw error
    }

    if (error instanceof Error && error.message.includes('fetch')) {
      throw new Error(
        'Unable to connect to the API. Please check the base URL and your internet connection.',
      )
    }

    throw new Error(
      'Failed to fetch models from API. Please check your configuration and try again.',
    )
  }
}

async function fetchAnthropicCompatibleModelsWithFallback({
  baseURL,
  provider,
  apiKey,
  apiKeyUrl,
  setModelLoadError,
}: {
  baseURL: string
  provider: string
  apiKey: string
  apiKeyUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  let lastError: Error | null = null

  try {
    const models = await fetchAnthropicModels(baseURL, apiKey)
    return models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: provider,
      max_tokens: model.max_tokens || 8192,
      supports_vision: model.supports_vision || true,
      supports_function_calling: model.supports_function_calling || true,
      supports_reasoning_effort: false,
    }))
  } catch (error) {
    lastError = error as Error
    debugLogger.warn('MODEL_FETCH_NATIVE_API_FAILED', {
      provider,
      error: error instanceof Error ? error.message : String(error),
    })
  }

  try {
    const models = await fetchCustomModels(baseURL, apiKey)
    return models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: provider,
      max_tokens: model.max_tokens || 8192,
      supports_vision: model.supports_vision || false,
      supports_function_calling: model.supports_function_calling || true,
      supports_reasoning_effort: false,
    }))
  } catch (error) {
    lastError = error as Error
    debugLogger.warn('MODEL_FETCH_OPENAI_API_FAILED', {
      provider,
      error: error instanceof Error ? error.message : String(error),
    })
  }

  let errorMessage = `Failed to fetch ${provider} models using both native and OpenAI-compatible API formats`
  if (lastError instanceof Error) {
    errorMessage = lastError.message
  }

  if (errorMessage.includes('API key')) {
    errorMessage += apiKeyUrl
      ? `\n\n💡 Tip: Get your API key from ${apiKeyUrl}`
      : '\n\n💡 Tip: Check that your API key is set and valid for this provider'
  } else if (errorMessage.includes('permission')) {
    errorMessage += `\n\n💡 Tip: Make sure your API key has access to the ${provider} API`
  } else if (errorMessage.includes('connection')) {
    errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
  }

  setModelLoadError(errorMessage)
  throw new Error(errorMessage)
}

export async function fetchAnthropicCompatibleProviderModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  const defaultBaseURL = 'https://api.anthropic.com'
  const apiKeyUrl = ''
  const actualProvider = 'anthropic'
  const baseURL = providerBaseUrl || defaultBaseURL
  return await fetchAnthropicCompatibleModelsWithFallback({
    baseURL,
    provider: actualProvider,
    apiKey,
    apiKeyUrl,
    setModelLoadError,
  })
}

export async function fetchKimiModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL = providerBaseUrl || 'https://api.moonshot.cn/v1'
    const models = await fetchCustomModels(baseURL, apiKey)

    const kimiModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'kimi',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return kimiModels
  } catch (error) {
    let errorMessage = 'Failed to fetch Kimi models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://platform.moonshot.cn/console/api-keys'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the Kimi API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchDeepSeekModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL = providerBaseUrl || 'https://api.deepseek.com'
    const models = await fetchCustomModels(baseURL, apiKey)

    const deepseekModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'deepseek',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return deepseekModels
  } catch (error) {
    let errorMessage = 'Failed to fetch DeepSeek models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://platform.deepseek.com/api_keys'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the DeepSeek API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchSiliconFlowModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL = providerBaseUrl || 'https://api.siliconflow.cn/v1'
    const models = await fetchCustomModels(baseURL, apiKey)

    const siliconflowModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'siliconflow',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return siliconflowModels
  } catch (error) {
    let errorMessage = 'Failed to fetch SiliconFlow models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://cloud.siliconflow.cn/i/oJWsm6io'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the SiliconFlow API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchQwenModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL =
      providerBaseUrl || 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    const models = await fetchCustomModels(baseURL, apiKey)

    const qwenModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'qwen',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return qwenModels
  } catch (error) {
    let errorMessage = 'Failed to fetch Qwen models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://bailian.console.aliyun.com/?tab=model#/api-key'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the Qwen API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchGLMModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL = providerBaseUrl || 'https://open.bigmodel.cn/api/paas/v4'
    const models = await fetchCustomModels(baseURL, apiKey)

    const glmModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'glm',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return glmModels
  } catch (error) {
    let errorMessage = 'Failed to fetch GLM models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://open.bigmodel.cn (API Keys section)'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the GLM API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchMinimaxModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL = providerBaseUrl || 'https://api.minimaxi.com/v1'
    const models = await fetchCustomModels(baseURL, apiKey)

    const minimaxModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'minimax',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return minimaxModels
  } catch (error) {
    let errorMessage = 'Failed to fetch MiniMax models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://www.minimax.io/platform/user-center/basic-information'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the MiniMax API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchBaiduQianfanModels({
  apiKey,
  providerBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  providerBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const baseURL = providerBaseUrl || 'https://qianfan.baidubce.com/v2'
    const models = await fetchCustomModels(baseURL, apiKey)

    const baiduModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'baidu-qianfan',
      max_tokens: model.max_tokens || 8192,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return baiduModels
  } catch (error) {
    let errorMessage = 'Failed to fetch Baidu Qianfan models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Get your API key from https://console.bce.baidu.com/iam/#/iam/accesslist'
    } else if (errorMessage.includes('permission')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure your API key has access to the Baidu Qianfan API'
    } else if (errorMessage.includes('connection')) {
      errorMessage += '\n\n💡 Tip: Check your internet connection and try again'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchCustomOpenAIModels({
  apiKey,
  customBaseUrl,
  setModelLoadError,
}: {
  apiKey: string
  customBaseUrl: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
  try {
    const models = await fetchCustomModels(customBaseUrl, apiKey)

    const customModels = models.map((model: any) => ({
      model:
        model.modelName || model.id || model.name || model.model || 'unknown',
      provider: 'custom-openai',
      max_tokens: model.max_tokens || 4096,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning_effort: false,
    }))

    return customModels
  } catch (error) {
    let errorMessage = 'Failed to fetch custom API models'

    if (error instanceof Error) {
      errorMessage = error.message
    }

    if (errorMessage.includes('API key')) {
      errorMessage +=
        '\n\n💡 Tip: Check that your API key is valid for this endpoint'
    } else if (errorMessage.includes('endpoint not found')) {
      errorMessage +=
        '\n\n💡 Tip: Make sure the base URL ends with /v1 and supports OpenAI-compatible API'
    } else if (errorMessage.includes('connect')) {
      errorMessage +=
        '\n\n💡 Tip: Verify the base URL is correct and accessible'
    } else if (errorMessage.includes('response format')) {
      errorMessage += '\n\n💡 Tip: This API may not be fully OpenAI-compatible'
    }

    setModelLoadError(errorMessage)
    throw error
  }
}

export async function fetchGeminiModels({
  apiKey,
  setModelLoadError,
}: {
  apiKey: string
  setModelLoadError: SetModelLoadError
}): Promise<ModelInfo[]> {
	  try {
	    const response = await fetch(
	      `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`,
	    )

	    if (!response.ok) {
	      const errorData = await response.json()
	      throw new Error(
        errorData.error?.message || `API error: ${response.status}`,
      )
    }

    const { models } = await response.json()

    const geminiModels = models
      .filter((model: any) =>
        model.supportedGenerationMethods.includes('generateContent'),
      )
      .map((model: any) => ({
        model: model.name.replace('models/', ''),
        provider: 'gemini',
        max_tokens: model.outputTokenLimit,
        supports_vision:
          model.supportedGenerationMethods.includes('generateContent'),
        supports_function_calling:
          model.supportedGenerationMethods.includes('generateContent'),
      }))

    return geminiModels
  } catch (error) {
    setModelLoadError(error instanceof Error ? error.message : 'Unknown error')
    throw error
  }
}
