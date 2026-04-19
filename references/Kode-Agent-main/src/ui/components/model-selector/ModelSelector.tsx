import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Box, Newline, Text, useInput, useStdout } from 'ink'
import OpenAI from 'openai'
import figures from 'figures'

import models, { providers } from '@constants/models'
import { PRODUCT_NAME } from '@constants/product'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { verifyApiKey } from '@services/llmLazy'
import {
  testGPT5Connection,
  validateGPT5Config,
} from '@services/gpt5ConnectionTest'
import {
  getGlobalConfig,
  ModelPointerType,
  ProviderType,
  saveGlobalConfig,
  setAllPointersToModel,
  setModelPointer,
} from '@utils/config'
import { getModelManager } from '@utils/model'
import { getTheme } from '@utils/theme'
import { debug as debugLogger } from '@utils/log/debugLogger'

import { CardNavigator, useCardNavigation } from '../CardNavigator'
import { Select } from '../custom-select/select'
import { ScreenContainer } from './ScreenContainer'
import {
  CONTEXT_LENGTH_OPTIONS,
  DEFAULT_CONTEXT_LENGTH,
  DEFAULT_MAX_TOKENS,
  MAX_TOKENS_OPTIONS,
  REASONING_EFFORT_OPTIONS,
  ReasoningEffortOption,
} from './options'
import { printModelConfig } from './printModelConfig'
import type { ModelInfo } from './types'
import { useEscapeNavigation } from './useEscapeNavigation'
import * as modelFetchers from './modelFetchers'
import TextInput from '../TextInput'
import { ModelSelectionScreen } from './ModelSelectionScreen'

type WindowedOptionsProps = {
  options: Array<{ value: string; label: string }>
  focusedIndex: number
  maxVisible: number
  theme: ReturnType<typeof getTheme>
}

const WindowedOptions = React.memo(function WindowedOptions({
  options,
  focusedIndex,
  maxVisible,
  theme,
}: WindowedOptionsProps) {
  if (options.length === 0) {
    return <Text color={theme.secondaryText}>No options available.</Text>
  }

  const visibleCount = Math.max(1, Math.min(maxVisible, options.length))
  const half = Math.floor(visibleCount / 2)
  const start = Math.max(
    0,
    Math.min(focusedIndex - half, Math.max(0, options.length - visibleCount)),
  )
  const end = Math.min(options.length, start + visibleCount)
  const showUp = start > 0
  const showDown = end < options.length

  return (
    <Box flexDirection="column" gap={0}>
      {showUp && (
        <Text color={theme.secondaryText}>{figures.arrowUp} More</Text>
      )}
      {options.slice(start, end).map((opt, idx) => {
        const absoluteIndex = start + idx
        const isFocused = absoluteIndex === focusedIndex
        return (
          <Box key={opt.value} flexDirection="row">
            <Text color={isFocused ? theme.kode : theme.secondaryText}>
              {isFocused ? figures.pointer : ' '}
            </Text>
            <Text
              color={isFocused ? theme.text : theme.secondaryText}
              bold={isFocused}
            >
              {' '}
              {opt.label}
            </Text>
          </Box>
        )
      })}
      {showDown && (
        <Text color={theme.secondaryText}>{figures.arrowDown} More</Text>
      )}
    </Box>
  )
})

type Props = {
  onDone: () => void
  abortController?: AbortController
  targetPointer?: ModelPointerType
  isOnboarding?: boolean
  onCancel?: () => void
  skipModelType?: boolean
}

export function ModelSelector({
  onDone: onDoneProp,
  abortController,
  targetPointer,
  isOnboarding = false,
  onCancel,
  skipModelType = false,
}: Props): React.ReactNode {
  const config = getGlobalConfig()
  const theme = getTheme()
  const { stdout } = useStdout()
  const terminalRows = stdout?.rows ?? 24
  const compactLayout = terminalRows <= 22
  const tightLayout = terminalRows <= 18
  const containerPaddingY = tightLayout ? 0 : compactLayout ? 0 : 1
  const containerGap = tightLayout ? 0 : 1
  const onDone = () => {
    printModelConfig()
    onDoneProp()
  }
  const exitState = useExitOnCtrlCD(() => process.exit(0))

  const getInitialScreen = (): string => {
    return 'provider'
  }

  const [screenStack, setScreenStack] = useState<
    Array<
      | 'provider'
      | 'partnerProviders'
      | 'partnerCodingPlans'
      | 'apiKey'
      | 'resourceName'
      | 'baseUrl'
      | 'model'
      | 'modelInput'
      | 'modelParams'
      | 'contextLength'
      | 'connectionTest'
      | 'confirmation'
    >
  >([getInitialScreen()])

  const currentScreen = screenStack[screenStack.length - 1]

  const navigateTo = (
    screen:
      | 'provider'
      | 'partnerProviders'
      | 'partnerCodingPlans'
      | 'apiKey'
      | 'resourceName'
      | 'baseUrl'
      | 'model'
      | 'modelInput'
      | 'modelParams'
      | 'contextLength'
      | 'connectionTest'
      | 'confirmation',
  ) => {
    setScreenStack(prev => [...prev, screen])
  }

  const goBack = () => {
    if (screenStack.length > 1) {
      setScreenStack(prev => prev.slice(0, -1))
    } else {
      onDone()
    }
  }

  const [selectedProvider, setSelectedProvider] = useState<ProviderType>(
    config.primaryProvider ?? 'anthropic',
  )

  const [selectedModel, setSelectedModel] = useState<string>('')
  const [apiKey, setApiKey] = useState<string>('')

  const [maxTokens, setMaxTokens] = useState<string>(
    config.maxTokens?.toString() || DEFAULT_MAX_TOKENS.toString(),
  )
  const [maxTokensMode, setMaxTokensMode] = useState<'preset' | 'custom'>(
    'preset',
  )
  const [selectedMaxTokensPreset, setSelectedMaxTokensPreset] =
    useState<number>(config.maxTokens || DEFAULT_MAX_TOKENS)
  const [reasoningEffort, setReasoningEffort] =
    useState<ReasoningEffortOption>('medium')
  const [supportsReasoningEffort, setSupportsReasoningEffort] =
    useState<boolean>(false)

  const [contextLength, setContextLength] = useState<number>(
    DEFAULT_CONTEXT_LENGTH,
  )

  const [activeFieldIndex, setActiveFieldIndex] = useState(0)
  const [maxTokensCursorOffset, setMaxTokensCursorOffset] = useState<number>(0)

  const [apiKeyCleanedNotification, setApiKeyCleanedNotification] =
    useState<boolean>(false)

  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [isLoadingModels, setIsLoadingModels] = useState(false)
  const [modelLoadError, setModelLoadError] = useState<string | null>(null)
  const [modelSearchQuery, setModelSearchQuery] = useState<string>('')
  const [modelSearchCursorOffset, setModelSearchCursorOffset] =
    useState<number>(0)
  const [cursorOffset, setCursorOffset] = useState<number>(0)
  const [apiKeyEdited, setApiKeyEdited] = useState<boolean>(false)
  const [providerFocusIndex, setProviderFocusIndex] = useState(0)
  const [partnerProviderFocusIndex, setPartnerProviderFocusIndex] = useState(0)
  const [codingPlanFocusIndex, setCodingPlanFocusIndex] = useState(0)

  const [fetchRetryCount, setFetchRetryCount] = useState<number>(0)
  const [isRetrying, setIsRetrying] = useState<boolean>(false)

  const [isTestingConnection, setIsTestingConnection] = useState<boolean>(false)
  const [connectionTestResult, setConnectionTestResult] = useState<{
    success: boolean
    message: string
    endpoint?: string
    details?: string
  } | null>(null)

  const [validationError, setValidationError] = useState<string | null>(null)

  const [resourceName, setResourceName] = useState<string>('')
  const [resourceNameCursorOffset, setResourceNameCursorOffset] =
    useState<number>(0)
  const [customModelName, setCustomModelName] = useState<string>('')
  const [customModelNameCursorOffset, setCustomModelNameCursorOffset] =
    useState<number>(0)

  const [ollamaBaseUrl, setOllamaBaseUrl] = useState<string>(
    'http://localhost:11434/v1',
  )
  const [ollamaBaseUrlCursorOffset, setOllamaBaseUrlCursorOffset] =
    useState<number>(0)

  const [customBaseUrl, setCustomBaseUrl] = useState<string>('')
  const [customBaseUrlCursorOffset, setCustomBaseUrlCursorOffset] =
    useState<number>(0)

  const [providerBaseUrl, setProviderBaseUrl] = useState<string>('')
  const [providerBaseUrlCursorOffset, setProviderBaseUrlCursorOffset] =
    useState<number>(0)

  const reasoningEffortOptions = REASONING_EFFORT_OPTIONS

  const mainMenuOptions = [
    { value: 'custom-openai', label: 'Custom OpenAI-Compatible API' },
    { value: 'custom-anthropic', label: 'Custom Messages API (v1/messages)' },
    { value: 'partnerProviders', label: 'Partner Providers →' },
    { value: 'partnerCodingPlans', label: 'Partner Coding Plans →' },
    {
      value: 'ollama',
      label: getProviderLabel('ollama', models.ollama?.length || 0),
    },
  ]

  const rankedProviders = [
    'openai',
    'anthropic',
    'gemini',
    'glm',
    'kimi',
    'minimax',
    'qwen',
    'deepseek',
    'openrouter',
    'burncloud',
    'siliconflow',
    'baidu-qianfan',
    'mistral',
    'xai',
    'groq',
    'azure',
  ]

  const partnerProviders = rankedProviders.filter(
    provider =>
      providers[provider] &&
      !provider.includes('coding') &&
      provider !== 'custom-openai' &&
      provider !== 'ollama',
  )

  const codingPlanProviders = Object.keys(providers).filter(provider =>
    provider.includes('coding'),
  )

  const partnerProviderOptions = partnerProviders.map(provider => {
    const modelCount = models[provider]?.length || 0
    const label = getProviderLabel(provider, modelCount)
    return {
      label,
      value: provider,
    }
  })

  const codingPlanOptions = codingPlanProviders.map(provider => {
    const modelCount = models[provider]?.length || 0
    const label = getProviderLabel(provider, modelCount)
    return {
      label,
      value: provider,
    }
  })

  useEffect(() => {
    if (!apiKeyEdited && selectedProvider) {
      if (process.env[selectedProvider.toUpperCase() + '_API_KEY']) {
        setApiKey(
          process.env[selectedProvider.toUpperCase() + '_API_KEY'] as string,
        )
      } else {
        setApiKey('')
      }
    }
  }, [selectedProvider, apiKey, apiKeyEdited])

  useEffect(() => {
    if (
      currentScreen === 'contextLength' &&
      !CONTEXT_LENGTH_OPTIONS.find(opt => opt.value === contextLength)
    ) {
      setContextLength(DEFAULT_CONTEXT_LENGTH)
    }
  }, [currentScreen, contextLength])

  const providerReservedLines = 8 + containerPaddingY * 2 + containerGap * 2
  const partnerReservedLines = 10 + containerPaddingY * 2 + containerGap * 3
  const codingReservedLines = partnerReservedLines
  const clampIndex = (index: number, length: number) =>
    length === 0 ? 0 : Math.max(0, Math.min(index, length - 1))

  useEffect(() => {
    setProviderFocusIndex(prev => clampIndex(prev, mainMenuOptions.length))
  }, [mainMenuOptions.length])

  useEffect(() => {
    setPartnerProviderFocusIndex(prev =>
      clampIndex(prev, partnerProviderOptions.length),
    )
  }, [partnerProviderOptions.length])

  useEffect(() => {
    setCodingPlanFocusIndex(prev => clampIndex(prev, codingPlanOptions.length))
  }, [codingPlanOptions.length])

  function getProviderLabel(provider: string, modelCount: number): string {
    if (providers[provider]) {
      return `${providers[provider].name} ${providers[provider].status === 'wip' ? '(WIP)' : ''}`
    }
    return `${provider}`
  }

  function handleProviderSelection(provider: string) {
    if (provider === 'partnerProviders') {
      setPartnerProviderFocusIndex(0)
      navigateTo('partnerProviders')
      return
    } else if (provider === 'partnerCodingPlans') {
      setCodingPlanFocusIndex(0)
      navigateTo('partnerCodingPlans')
      return
    } else if (provider === 'custom-anthropic') {
      setSelectedProvider('anthropic' as ProviderType)
      setProviderBaseUrl('')
      navigateTo('baseUrl')
      return
    }

    const providerType = provider as ProviderType
    setSelectedProvider(providerType)

    if (provider === 'custom') {
      saveConfiguration(providerType, selectedModel || '')
      onDone()
    } else if (provider === 'custom-openai' || provider === 'ollama') {
      const defaultBaseUrl = providers[providerType]?.baseURL || ''
      setProviderBaseUrl(defaultBaseUrl)
      navigateTo('baseUrl')
    } else {
      const defaultBaseUrl = providers[providerType]?.baseURL || ''
      setProviderBaseUrl(defaultBaseUrl)
      navigateTo('apiKey')
    }
  }

  function getSafeVisibleOptionCount(
    requestedCount: number,
    optionLength: number,
    reservedLines: number = 10,
  ): number {
    const rows = terminalRows
    const available = Math.max(1, rows - reservedLines)
    return Math.max(1, Math.min(requestedCount, optionLength, available))
  }

  async function fetchOllamaModels() {
    try {
      const response = await fetch(`${ollamaBaseUrl}/models`)

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}: ${response.statusText}`)
      }

      const responseData = await response.json()

      let models = []

      if (responseData.data && Array.isArray(responseData.data)) {
        models = responseData.data
      }
      else if (Array.isArray(responseData.models)) {
        models = responseData.models
      }
      else if (Array.isArray(responseData)) {
        models = responseData
      } else {
        throw new Error(
          'Invalid response from Ollama API: missing models array',
        )
      }

      const ollamaModels = models.map((model: any) => ({
        model:
          model.id ??
          model.name ??
          model.modelName ??
          (typeof model === 'string' ? model : ''),
        provider: 'ollama',
        max_tokens: DEFAULT_MAX_TOKENS,
        supports_vision: false,
        supports_function_calling: true,
        supports_reasoning_effort: false,
      }))

      const validModels = ollamaModels.filter(model => model.model)

      const normalizeOllamaRoot = (url: string): string => {
        try {
          const u = new URL(url)
          let pathname = u.pathname.replace(/\/+$|^$/, '')
          if (pathname.endsWith('/v1')) {
            pathname = pathname.slice(0, -3)
          }
          u.pathname = pathname
          return u.toString().replace(/\/+$/, '')
        } catch {
          return url.replace(/\/v1\/?$/, '')
        }
      }

      const extractContextTokens = (data: any): number | null => {
        if (!data || typeof data !== 'object') return null

        if (data.model_info && typeof data.model_info === 'object') {
          const modelInfo = data.model_info
          for (const key of Object.keys(modelInfo)) {
            if (
              key.endsWith('.context_length') ||
              key.endsWith('_context_length')
            ) {
              const val = modelInfo[key]
              if (typeof val === 'number' && isFinite(val) && val > 0) {
                return val
              }
            }
          }
        }

        const candidates = [
          (data as any)?.parameters?.num_ctx,
          (data as any)?.model_info?.num_ctx,
          (data as any)?.config?.num_ctx,
          (data as any)?.details?.context_length,
          (data as any)?.context_length,
          (data as any)?.num_ctx,
          (data as any)?.max_tokens,
          (data as any)?.max_new_tokens,
        ].filter((v: any) => typeof v === 'number' && isFinite(v) && v > 0)
        if (candidates.length > 0) {
          return Math.max(...candidates)
        }

        if (typeof (data as any)?.parameters === 'string') {
          const m = (data as any).parameters.match(/num_ctx\s*[:=]\s*(\d+)/i)
          if (m) {
            const n = parseInt(m[1], 10)
            if (Number.isFinite(n) && n > 0) return n
          }
        }
        return null
      }

      const ollamaRoot = normalizeOllamaRoot(ollamaBaseUrl)
      const enrichedModels = await Promise.all(
        validModels.map(async (m: any) => {
          try {
            const showResp = await fetch(`${ollamaRoot}/api/show`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: m.model }),
            })
            if (showResp.ok) {
              const showData = await showResp.json()
              const ctx = extractContextTokens(showData)
              if (typeof ctx === 'number' && isFinite(ctx) && ctx > 0) {
                return { ...m, context_length: ctx }
              }
            }
            return m
          } catch {
            return m
          }
        }),
      )

      setAvailableModels(enrichedModels)

      if (enrichedModels.length > 0) {
        navigateTo('model')
      } else {
        setModelLoadError('No models found in your Ollama installation')
      }

      return enrichedModels
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error)

      if (errorMessage.includes('fetch')) {
        setModelLoadError(
          `Could not connect to Ollama server at ${ollamaBaseUrl}. Make sure Ollama is running and the URL is correct.`,
        )
      } else {
        setModelLoadError(`Error loading Ollama models: ${errorMessage}`)
      }

      debugLogger.warn('OLLAMA_FETCH_ERROR', {
        error: error instanceof Error ? error.message : String(error),
      })
      return []
    }
  }

  async function fetchModelsWithRetry() {
    const MAX_RETRIES = 2
    let lastError: Error | null = null

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      setFetchRetryCount(attempt)
      setIsRetrying(attempt > 1)

      if (attempt > 1) {
        setModelLoadError(
          `Attempt ${attempt}/${MAX_RETRIES}: Retrying model discovery...`,
        )
        await new Promise(resolve => setTimeout(resolve, 1000))
      }

      try {
        const models = await fetchModels()
        setFetchRetryCount(0)
        setIsRetrying(false)
        setModelLoadError(null)
        return models
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error))
        debugLogger.warn('MODEL_FETCH_RETRY_FAILED', {
          attempt,
          maxRetries: MAX_RETRIES,
          error: lastError.message,
          provider: selectedProvider,
        })

        if (attempt === MAX_RETRIES) {
          break
        }
      }
    }

    setIsRetrying(false)
    const errorMessage = lastError?.message || 'Unknown error'

    const supportsManualInput = [
      'anthropic',
      'kimi',
      'deepseek',
      'siliconflow',
      'qwen',
      'glm',
      'minimax',
      'baidu-qianfan',
      'custom-openai',
    ].includes(selectedProvider)

    setModelLoadError(
      `Failed to validate API key after ${MAX_RETRIES} attempts: ${errorMessage}\n\nPlease check your API key and try again, or press Tab to manually enter model name.`,
    )

    throw new Error(`API key validation failed: ${errorMessage}`)
  }

  async function fetchModels() {
    setIsLoadingModels(true)
    setModelLoadError(null)

    try {
      if (selectedProvider === 'anthropic') {
        const anthropicModels =
          await modelFetchers.fetchAnthropicCompatibleProviderModels({
            apiKey,
            providerBaseUrl,
            setModelLoadError,
          })
        setAvailableModels(anthropicModels)
        navigateTo('model')
        return anthropicModels
      }

      if (selectedProvider === 'custom-openai') {
        const customModels = await modelFetchers.fetchCustomOpenAIModels({
          apiKey,
          customBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(customModels)
        navigateTo('model')
        return customModels
      }

      if (selectedProvider === 'gemini') {
        const geminiModels = await modelFetchers.fetchGeminiModels({
          apiKey,
          setModelLoadError,
        })
        setAvailableModels(geminiModels)
        navigateTo('model')
        return geminiModels
      }

      if (selectedProvider === 'kimi') {
        const kimiModels = await modelFetchers.fetchKimiModels({
          apiKey,
          providerBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(kimiModels)
        navigateTo('model')
        return kimiModels
      }

      if (selectedProvider === 'deepseek') {
        const deepseekModels = await modelFetchers.fetchDeepSeekModels({
          apiKey,
          providerBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(deepseekModels)
        navigateTo('model')
        return deepseekModels
      }

      if (selectedProvider === 'siliconflow') {
        const siliconflowModels = await modelFetchers.fetchSiliconFlowModels({
          apiKey,
          providerBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(siliconflowModels)
        navigateTo('model')
        return siliconflowModels
      }

      if (selectedProvider === 'qwen') {
        const qwenModels = await modelFetchers.fetchQwenModels({
          apiKey,
          providerBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(qwenModels)
        navigateTo('model')
        return qwenModels
      }

      if (selectedProvider === 'glm') {
        const glmModels = await modelFetchers.fetchGLMModels({
          apiKey,
          providerBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(glmModels)
        navigateTo('model')
        return glmModels
      }

      if (selectedProvider === 'baidu-qianfan') {
        const baiduModels = await modelFetchers.fetchBaiduQianfanModels({
          apiKey,
          providerBaseUrl,
          setModelLoadError,
        })
        setAvailableModels(baiduModels)
        navigateTo('model')
        return baiduModels
      }

      if (selectedProvider === 'azure') {
        navigateTo('modelInput')
        return []
      }

      let baseURL = providerBaseUrl || providers[selectedProvider]?.baseURL

      if (selectedProvider === 'custom-openai') {
        baseURL = customBaseUrl
      }

      const openai = new OpenAI({
        apiKey: apiKey || 'dummy-key-for-ollama',
        baseURL: baseURL,
        dangerouslyAllowBrowser: true,
      })

      const response = await openai.models.list()

      const fetchedModels = []
      for (const model of response.data) {
        const modelName =
          (model as any).modelName ||
          (model as any).id ||
          (model as any).name ||
          (model as any).model ||
          'unknown'
        const modelInfo = models[selectedProvider as keyof typeof models]?.find(
          m => m.model === modelName,
        )
        fetchedModels.push({
          model: modelName,
          provider: selectedProvider,
          max_tokens: modelInfo?.max_output_tokens,
          supports_vision: modelInfo?.supports_vision || false,
          supports_function_calling:
            modelInfo?.supports_function_calling || false,
          supports_reasoning_effort:
            modelInfo?.supports_reasoning_effort || false,
        })
      }

      setAvailableModels(fetchedModels)

      navigateTo('model')

      return fetchedModels
    } catch (error) {
      debugLogger.warn('MODEL_FETCH_ERROR', {
        provider: selectedProvider,
        error: error instanceof Error ? error.message : String(error),
      })
      throw error
    } finally {
      setIsLoadingModels(false)
    }
  }

  async function handleApiKeySubmit(key: string) {
    const cleanedKey = key.replace(/[\r\n]/g, '').trim()
    setApiKey(cleanedKey)

    setModelLoadError(null)

    if (selectedProvider === 'azure') {
      navigateTo('resourceName')
      return
    }

    try {
      setIsLoadingModels(true)
      const models = await fetchModelsWithRetry()

      if (models && models.length > 0) {
      } else if (models && models.length === 0) {
        navigateTo('modelInput')
      }
    } catch (error) {
      debugLogger.warn('API_KEY_VALIDATION_FAILED', {
        provider: selectedProvider,
        error: error instanceof Error ? error.message : String(error),
      })
    } finally {
      setIsLoadingModels(false)
    }
  }

  function handleResourceNameSubmit(name: string) {
    setResourceName(name)
    navigateTo('modelInput')
  }

  function handleOllamaBaseUrlSubmit(url: string) {
    setOllamaBaseUrl(url)
    setIsLoadingModels(true)
    setModelLoadError(null)

    fetchOllamaModels().finally(() => {
      setIsLoadingModels(false)
    })
  }

  function handleCustomBaseUrlSubmit(url: string) {
    const cleanUrl = url.replace(/\/+$/, '')
    setCustomBaseUrl(cleanUrl)
    navigateTo('apiKey')
  }

  function handleProviderBaseUrlSubmit(url: string) {
    const cleanUrl = url.replace(/\/+$/, '')
    setProviderBaseUrl(cleanUrl)

    if (selectedProvider === 'ollama') {
      setOllamaBaseUrl(cleanUrl)
      setIsLoadingModels(true)
      setModelLoadError(null)

      fetchOllamaModels().finally(() => {
        setIsLoadingModels(false)
      })
    } else {
      navigateTo('apiKey')
    }
  }

  function handleCustomModelSubmit(model: string) {
    setCustomModelName(model)
    setSelectedModel(model)

    setSupportsReasoningEffort(false)
    setReasoningEffort(null)

    setMaxTokensMode('preset')
    setSelectedMaxTokensPreset(DEFAULT_MAX_TOKENS)
    setMaxTokens(DEFAULT_MAX_TOKENS.toString())
    setMaxTokensCursorOffset(DEFAULT_MAX_TOKENS.toString().length)

    navigateTo('modelParams')
    setActiveFieldIndex(0)
  }

  function handleModelSelection(model: string) {
    setSelectedModel(model)

    const modelInfo = availableModels.find(m => m.model === model)
    setSupportsReasoningEffort(modelInfo?.supports_reasoning_effort || false)

    if (!modelInfo?.supports_reasoning_effort) {
      setReasoningEffort(null)
    }

    if (modelInfo?.context_length) {
      setContextLength(modelInfo.context_length)
    } else {
      setContextLength(DEFAULT_CONTEXT_LENGTH)
    }

    if (modelInfo?.max_tokens) {
      const modelMaxTokens = modelInfo.max_tokens
      const matchingPreset = MAX_TOKENS_OPTIONS.find(
        option => option.value === modelMaxTokens,
      )

      if (matchingPreset) {
        setMaxTokensMode('preset')
        setSelectedMaxTokensPreset(modelMaxTokens)
        setMaxTokens(modelMaxTokens.toString())
      } else {
        setMaxTokensMode('custom')
        setMaxTokens(modelMaxTokens.toString())
      }
      setMaxTokensCursorOffset(modelMaxTokens.toString().length)
    } else {
      setMaxTokensMode('preset')
      setSelectedMaxTokensPreset(DEFAULT_MAX_TOKENS)
      setMaxTokens(DEFAULT_MAX_TOKENS.toString())
      setMaxTokensCursorOffset(DEFAULT_MAX_TOKENS.toString().length)
    }

    navigateTo('modelParams')
    setActiveFieldIndex(0)
  }

  const handleModelParamsSubmit = () => {
    if (!CONTEXT_LENGTH_OPTIONS.find(opt => opt.value === contextLength)) {
      setContextLength(DEFAULT_CONTEXT_LENGTH)
    }
    navigateTo('contextLength')
  }

  async function testConnection(): Promise<{
    success: boolean
    message: string
    endpoint?: string
    details?: string
  }> {
    setIsTestingConnection(true)
    setConnectionTestResult(null)

    try {
      let testBaseURL =
        providerBaseUrl || providers[selectedProvider]?.baseURL || ''

      if (selectedProvider === 'azure') {
        testBaseURL = `https://${resourceName}.openai.azure.com/openai/deployments/${selectedModel}`
      } else if (selectedProvider === 'custom-openai') {
        testBaseURL = customBaseUrl
      }

      const isOpenAICompatible = [
        'minimax',
        'kimi',
        'deepseek',
        'siliconflow',
        'qwen',
        'glm',
        'baidu-qianfan',
        'openai',
        'mistral',
        'xai',
        'groq',
        'custom-openai',
      ].includes(selectedProvider)

      if (isOpenAICompatible) {
        const isGPT5 = selectedModel?.toLowerCase().includes('gpt-5')

        if (isGPT5) {
          debugLogger.api('GPT5_CONNECTION_TEST_USING_SPECIALIZED', {
            model: selectedModel,
            provider: selectedProvider,
          })

          const configValidation = validateGPT5Config({
            model: selectedModel,
            apiKey: apiKey,
            baseURL: testBaseURL,
            maxTokens: parseInt(maxTokens) || 8192,
            provider: selectedProvider,
          })

          if (!configValidation.valid) {
            return {
              success: false,
              message: '❌ GPT-5 configuration validation failed',
              details: configValidation.errors.join('\n'),
            }
          }

          const gpt5Result = await testGPT5Connection({
            model: selectedModel,
            apiKey: apiKey,
            baseURL: testBaseURL,
            maxTokens: parseInt(maxTokens) || 8192,
            provider: selectedProvider,
          })

          return gpt5Result
        }

        const endpointsToTry = []

        if (selectedProvider === 'minimax') {
          endpointsToTry.push(
            {
              path: '/text/chatcompletion_v2',
              name: 'MiniMax v2 (recommended)',
            },
            { path: '/chat/completions', name: 'Standard OpenAI' },
          )
        } else {
          endpointsToTry.push({
            path: '/chat/completions',
            name: 'Standard OpenAI',
          })
        }

        let lastError = null
        for (const endpoint of endpointsToTry) {
          try {
            const testResult = await testChatEndpoint(
              testBaseURL,
              endpoint.path,
              endpoint.name,
            )

            if (testResult.success) {
              return testResult
            }
            lastError = testResult
          } catch (error) {
            lastError = {
              success: false,
              message: `Failed to test ${endpoint.name}`,
              endpoint: endpoint.path,
              details: error instanceof Error ? error.message : String(error),
            }
          }
        }

        return (
          lastError || {
            success: false,
            message: 'All endpoints failed',
            details: 'No endpoints could be reached',
          }
        )
      } else {
        return await testProviderSpecificEndpoint(testBaseURL)
      }
    } catch (error) {
      return {
        success: false,
        message: 'Connection test failed',
        details: error instanceof Error ? error.message : String(error),
      }
    } finally {
      setIsTestingConnection(false)
    }
  }

  async function testChatEndpoint(
    baseURL: string,
    endpointPath: string,
    endpointName: string,
  ): Promise<{
    success: boolean
    message: string
    endpoint?: string
    details?: string
  }> {
    const testURL = `${baseURL.replace(/\/+$/, '')}${endpointPath}`

    const testPayload: any = {
      model: selectedModel,
      messages: [
        {
          role: 'user',
          content:
            'Please respond with exactly "YES" (in capital letters) to confirm this connection is working.',
        },
      ],
      max_tokens: Math.max(parseInt(maxTokens) || 8192, 8192),
      temperature: 0,
      stream: false,
    }

    if (selectedModel && selectedModel.toLowerCase().includes('gpt-5')) {
      debugLogger.api('GPT5_PARAMETER_FIX_APPLY', { model: selectedModel })

      if (testPayload.max_tokens) {
        testPayload.max_completion_tokens = testPayload.max_tokens
        delete testPayload.max_tokens
        debugLogger.api('GPT5_PARAMETER_FIX_MAX_TOKENS', {
          model: selectedModel,
          max_completion_tokens: testPayload.max_completion_tokens,
        })
      }

      if (
        testPayload.temperature !== undefined &&
        testPayload.temperature !== 1
      ) {
        debugLogger.api('GPT5_PARAMETER_FIX_TEMPERATURE', {
          model: selectedModel,
          from: testPayload.temperature,
          to: 1,
        })
        testPayload.temperature = 1
      }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (selectedProvider === 'azure') {
      headers['api-key'] = apiKey
    } else {
      headers['Authorization'] = `Bearer ${apiKey}`
    }

    try {
      const response = await fetch(testURL, {
        method: 'POST',
        headers,
        body: JSON.stringify(testPayload),
      })

      if (response.ok) {
        const data = await response.json()
        debugLogger.api('CONNECTION_TEST_RESPONSE', {
          provider: selectedProvider,
          endpoint: endpointPath,
          ok: true,
        })

        let responseContent = ''

        if (data.choices && data.choices.length > 0) {
          responseContent = data.choices[0]?.message?.content || ''
        } else if (data.reply) {
          responseContent = data.reply
        } else if (data.output) {
          responseContent = data.output?.text || data.output || ''
        }

        debugLogger.api('CONNECTION_TEST_RESPONSE_PARSED', {
          provider: selectedProvider,
          endpoint: endpointPath,
          contentLength: responseContent.length,
        })

        const containsYes = responseContent.toLowerCase().includes('yes')

        if (containsYes) {
          return {
            success: true,
            message: `✅ Connection test passed with ${endpointName}`,
            endpoint: endpointPath,
            details: `Model responded correctly: "${responseContent.trim()}"`,
          }
        } else {
          return {
            success: false,
            message: `⚠️ ${endpointName} connected but model response unexpected`,
            endpoint: endpointPath,
            details: `Expected "YES" but got: "${responseContent.trim() || '(empty response)'}"`,
          }
        }
      } else {
        const errorData = await response.json().catch(() => null)
        const errorMessage =
          errorData?.error?.message || errorData?.message || response.statusText

        return {
          success: false,
          message: `❌ ${endpointName} failed (${response.status})`,
          endpoint: endpointPath,
          details: `Error: ${errorMessage}`,
        }
      }
    } catch (error) {
      return {
        success: false,
        message: `❌ ${endpointName} connection failed`,
        endpoint: endpointPath,
        details: error instanceof Error ? error.message : String(error),
      }
    }
  }

  async function testResponsesEndpoint(
    baseURL: string,
    endpointPath: string,
    endpointName: string,
  ): Promise<{
    success: boolean
    message: string
    endpoint?: string
    details?: string
  }> {
    const testURL = `${baseURL.replace(/\/+$/, '')}${endpointPath}`

    const testPayload: any = {
      model: selectedModel,
      input: [
        {
          role: 'user',
          content:
            'Please respond with exactly "YES" (in capital letters) to confirm this connection is working.',
        },
      ],
      max_completion_tokens: Math.max(parseInt(maxTokens) || 8192, 8192),
      temperature: 1,
      reasoning: {
        effort: 'low',
      },
    }

    debugLogger.api('GPT5_RESPONSES_API_TEST_START', {
      model: selectedModel,
      url: testURL,
    })

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    }

    try {
      const response = await fetch(testURL, {
        method: 'POST',
        headers,
        body: JSON.stringify(testPayload),
      })

      if (response.ok) {
        const data = await response.json()
        debugLogger.api('GPT5_RESPONSES_API_TEST_RESPONSE', {
          model: selectedModel,
          ok: true,
        })

        let responseContent = ''

        if (data.output_text) {
          responseContent = data.output_text
        } else if (data.output) {
          responseContent =
            typeof data.output === 'string'
              ? data.output
              : data.output.text || ''
        }

        debugLogger.api('GPT5_RESPONSES_API_TEST_RESPONSE_PARSED', {
          model: selectedModel,
          contentLength: responseContent.length,
        })

        const containsYes = responseContent.toLowerCase().includes('yes')

        if (containsYes) {
          return {
            success: true,
            message: `✅ Connection test passed with ${endpointName}`,
            endpoint: endpointPath,
            details: `GPT-5 responded correctly via Responses API: "${responseContent.trim()}"`,
          }
        } else {
          return {
            success: false,
            message: `⚠️ ${endpointName} connected but model response unexpected`,
            endpoint: endpointPath,
            details: `Expected "YES" but got: "${responseContent.trim() || '(empty response)'}"`,
          }
        }
      } else {
        const errorData = await response.json().catch(() => null)
        const errorMessage =
          errorData?.error?.message || errorData?.message || response.statusText

        debugLogger.warn('GPT5_RESPONSES_API_TEST_ERROR', {
          model: selectedModel,
          status: response.status,
          error:
            errorData?.error?.message || errorData?.message || response.statusText,
        })

        let details = `Responses API Error: ${errorMessage}`
        if (response.status === 400 && errorMessage.includes('max_tokens')) {
          details +=
            '\n🔧 Note: This appears to be a parameter compatibility issue. The fallback to Chat Completions should handle this.'
        } else if (response.status === 404) {
          details +=
            '\n🔧 Note: Responses API endpoint may not be available for this model or provider.'
        } else if (response.status === 401) {
          details += '\n🔧 Note: API key authentication failed.'
        }

        return {
          success: false,
          message: `❌ ${endpointName} failed (${response.status})`,
          endpoint: endpointPath,
          details: details,
        }
      }
    } catch (error) {
      return {
        success: false,
        message: `❌ ${endpointName} connection failed`,
        endpoint: endpointPath,
        details: error instanceof Error ? error.message : String(error),
      }
    }
  }

  async function testProviderSpecificEndpoint(baseURL: string): Promise<{
    success: boolean
    message: string
    endpoint?: string
    details?: string
  }> {
    if (selectedProvider === 'anthropic' || selectedProvider === 'bigdream') {
      try {
        debugLogger.api('PROVIDER_CONNECTION_TEST_NATIVE_SDK', {
          provider: selectedProvider,
        })

        let testBaseURL: string | undefined = undefined
        if (selectedProvider === 'bigdream') {
          testBaseURL = baseURL || 'https://api-key.info'
        } else if (selectedProvider === 'anthropic') {
          testBaseURL =
            baseURL && baseURL !== 'https://api.anthropic.com'
              ? baseURL
              : undefined
        }

        const isValid = await verifyApiKey(
          apiKey,
          testBaseURL,
          selectedProvider,
        )

        if (isValid) {
          return {
            success: true,
            message: `✅ ${selectedProvider} connection test passed`,
            endpoint: '/messages',
            details: 'API key verified using native SDK',
          }
        } else {
          return {
            success: false,
            message: `❌ ${selectedProvider} API key verification failed`,
            endpoint: '/messages',
            details:
              'Invalid API key. Please check your API key and try again.',
          }
        }
      } catch (error) {
        debugLogger.warn('PROVIDER_CONNECTION_TEST_NATIVE_SDK_ERROR', {
          provider: selectedProvider,
          error: error instanceof Error ? error.message : String(error),
        })
        return {
          success: false,
          message: `❌ ${selectedProvider} connection failed`,
          endpoint: '/messages',
          details: error instanceof Error ? error.message : String(error),
        }
      }
    }

    return {
      success: true,
      message: `✅ Configuration saved for ${selectedProvider}`,
      details: 'Provider-specific testing not implemented yet',
    }
  }

  async function handleConnectionTest() {
    const result = await testConnection()
    setConnectionTestResult(result)

    if (result.success) {
      setTimeout(() => {
        navigateTo('confirmation')
      }, 2000)
    }
  }

  const handleContextLengthSubmit = () => {
    navigateTo('connectionTest')
  }

  async function saveConfiguration(
    provider: ProviderType,
    model: string,
  ): Promise<string | null> {
    let baseURL = providerBaseUrl || providers[provider]?.baseURL || ''
    let actualProvider = provider

    if (provider === 'anthropic') {
      actualProvider = 'anthropic'
      baseURL = baseURL || 'https://api.anthropic.com'
    }

    if (provider === 'azure') {
      baseURL = `https://${resourceName}.openai.azure.com/openai/deployments/${model}`
    }
    else if (provider === 'custom-openai') {
      baseURL = customBaseUrl
    }

    try {
      const modelManager = getModelManager()

      const displayModel = model || 'default'
      const modelDisplayName =
        `${providers[actualProvider]?.name || actualProvider} ${displayModel}`.trim()

      const modelConfig = {
        name: modelDisplayName,
        provider: actualProvider,
        modelName: model || actualProvider,
        baseURL: baseURL,
        apiKey: apiKey || '',
        maxTokens: parseInt(maxTokens) || DEFAULT_MAX_TOKENS,
        contextLength: contextLength || DEFAULT_CONTEXT_LENGTH,
        reasoningEffort,
      }

      return await modelManager.addModel(modelConfig)
    } catch (error) {
      setValidationError(
        error instanceof Error ? error.message : 'Failed to add model',
      )
      return null
    }
  }

  async function handleConfirmation() {
    setValidationError(null)

    const modelId = await saveConfiguration(selectedProvider, selectedModel)

    if (!modelId) {
      return
    }

    setModelPointer('main', modelId)

    if (isOnboarding) {
      setAllPointersToModel(modelId)
    } else if (targetPointer && targetPointer !== 'main') {
      setModelPointer(targetPointer, modelId)
    }

    onDone()
  }

  const handleBack = () => {
    if (
      currentScreen === 'partnerProviders' ||
      currentScreen === 'partnerCodingPlans'
    ) {
      setProviderFocusIndex(0)
      setScreenStack(['provider'])
      return
    }

    if (currentScreen === 'provider') {
      if (onCancel) {
        onCancel()
      } else {
        onDone()
      }
      return
    }

    if (currentScreen === 'apiKey' && screenStack.length >= 2) {
      const previousScreen = screenStack[screenStack.length - 2]
      if (
        previousScreen === 'partnerProviders' ||
        previousScreen === 'partnerCodingPlans'
      ) {
        setScreenStack(prev => prev.slice(0, -1))
        return
      }
    }

    if (screenStack.length > 1) {
      setScreenStack(prev => prev.slice(0, -1))
    } else {
      setProviderFocusIndex(0)
      setScreenStack(['provider'])
    }
  }

  useEscapeNavigation(handleBack, abortController)

  function handleCursorOffsetChange(offset: number) {
    setCursorOffset(offset)
  }

  function formatApiKeyDisplay(key: string): string {
    if (!key) return ''
    if (key.length <= 10) return '*'.repeat(key.length)

    const prefix = key.slice(0, 4)
    const suffix = key.slice(-4)
    const middleLength = Math.max(0, key.length - 8)
    const middle = '*'.repeat(Math.min(middleLength, 30))

    return `${prefix}${middle}${suffix}`
  }

  function handleApiKeyChange(value: string) {
    setApiKeyEdited(true)
    const cleanedValue = value.replace(/[\r\n]/g, '').trim()

    if (value !== cleanedValue && value.length > 0) {
      setApiKeyCleanedNotification(true)
      setTimeout(() => setApiKeyCleanedNotification(false), 3000)
    }

    setApiKey(cleanedValue)
    setCursorOffset(cleanedValue.length)
  }

  function handleModelSearchChange(value: string) {
    setModelSearchQuery(value)
    setModelSearchCursorOffset(value.length)
  }

  function handleModelSearchCursorOffsetChange(offset: number) {
    setModelSearchCursorOffset(offset)
  }

  useInput((input, key) => {
    if (currentScreen === 'provider') {
      if (key.upArrow) {
        setProviderFocusIndex(prev =>
          mainMenuOptions.length === 0
            ? 0
            : (prev - 1 + mainMenuOptions.length) % mainMenuOptions.length,
        )
        return
      }
      if (key.downArrow) {
        setProviderFocusIndex(prev =>
          mainMenuOptions.length === 0
            ? 0
            : (prev + 1) % mainMenuOptions.length,
        )
        return
      }
      if (key.return) {
        const opt = mainMenuOptions[providerFocusIndex]
        if (opt) {
          handleProviderSelection(opt.value)
        }
        return
      }
    }

    if (currentScreen === 'partnerProviders') {
      if (key.upArrow) {
        setPartnerProviderFocusIndex(prev =>
          partnerProviderOptions.length === 0
            ? 0
            : (prev - 1 + partnerProviderOptions.length) %
              partnerProviderOptions.length,
        )
        return
      }
      if (key.downArrow) {
        setPartnerProviderFocusIndex(prev =>
          partnerProviderOptions.length === 0
            ? 0
            : (prev + 1) % partnerProviderOptions.length,
        )
        return
      }
      if (key.return) {
        const opt = partnerProviderOptions[partnerProviderFocusIndex]
        if (opt) {
          handleProviderSelection(opt.value)
        }
        return
      }
    }

    if (currentScreen === 'partnerCodingPlans') {
      if (key.upArrow) {
        setCodingPlanFocusIndex(prev =>
          codingPlanOptions.length === 0
            ? 0
            : (prev - 1 + codingPlanOptions.length) % codingPlanOptions.length,
        )
        return
      }
      if (key.downArrow) {
        setCodingPlanFocusIndex(prev =>
          codingPlanOptions.length === 0
            ? 0
            : (prev + 1) % codingPlanOptions.length,
        )
        return
      }
      if (key.return) {
        const opt = codingPlanOptions[codingPlanFocusIndex]
        if (opt) {
          handleProviderSelection(opt.value)
        }
        return
      }
    }

    if (currentScreen === 'apiKey' && key.return) {
      if (apiKey) {
        handleApiKeySubmit(apiKey)
      }
      return
    }

    if (currentScreen === 'apiKey' && key.tab) {
      if (
        selectedProvider === 'anthropic' ||
        selectedProvider === 'kimi' ||
        selectedProvider === 'deepseek' ||
        selectedProvider === 'qwen' ||
        selectedProvider === 'glm' ||
        selectedProvider === 'glm-coding' ||
        selectedProvider === 'minimax' ||
        selectedProvider === 'minimax-coding' ||
        selectedProvider === 'baidu-qianfan' ||
        selectedProvider === 'siliconflow' ||
        selectedProvider === 'custom-openai'
      ) {
        navigateTo('modelInput')
        return
      }

      fetchModelsWithRetry().catch(error => {
        debugLogger.warn('MODEL_FETCH_FINAL_ERROR', {
          provider: selectedProvider,
          error: error instanceof Error ? error.message : String(error),
        })
      })
      return
    }

    if (currentScreen === 'resourceName' && key.return) {
      if (resourceName) {
        handleResourceNameSubmit(resourceName)
      }
      return
    }

    if (currentScreen === 'baseUrl' && key.return) {
      if (selectedProvider === 'custom-openai') {
        handleCustomBaseUrlSubmit(customBaseUrl)
      } else {
        handleProviderBaseUrlSubmit(providerBaseUrl)
      }
      return
    }

    if (currentScreen === 'modelInput' && key.return) {
      if (customModelName) {
        handleCustomModelSubmit(customModelName)
      }
      return
    }

    if (currentScreen === 'confirmation' && key.return) {
      handleConfirmation().catch(error => {
        debugLogger.warn('CONFIRMATION_ERROR', {
          error: error instanceof Error ? error.message : String(error),
        })
        setValidationError(
          error instanceof Error ? error.message : 'Unexpected error occurred',
        )
      })
      return
    }

    if (currentScreen === 'connectionTest') {
      if (key.return) {
        if (!isTestingConnection && !connectionTestResult) {
          handleConnectionTest()
        } else if (connectionTestResult && connectionTestResult.success) {
          navigateTo('confirmation')
        } else if (connectionTestResult && !connectionTestResult.success) {
          handleConnectionTest()
        }
        return
      }
    }

    if (currentScreen === 'contextLength') {
      if (key.return) {
        handleContextLengthSubmit()
        return
      }

      if (key.upArrow) {
        const currentIndex = CONTEXT_LENGTH_OPTIONS.findIndex(
          opt => opt.value === contextLength,
        )
        const newIndex =
          currentIndex > 0
            ? currentIndex - 1
            : currentIndex === -1
              ? CONTEXT_LENGTH_OPTIONS.findIndex(
                  opt => opt.value === DEFAULT_CONTEXT_LENGTH,
                ) || 0
              : CONTEXT_LENGTH_OPTIONS.length - 1
        setContextLength(CONTEXT_LENGTH_OPTIONS[newIndex].value)
        return
      }

      if (key.downArrow) {
        const currentIndex = CONTEXT_LENGTH_OPTIONS.findIndex(
          opt => opt.value === contextLength,
        )
        const newIndex =
          currentIndex === -1
            ? CONTEXT_LENGTH_OPTIONS.findIndex(
                opt => opt.value === DEFAULT_CONTEXT_LENGTH,
              ) || 0
            : (currentIndex + 1) % CONTEXT_LENGTH_OPTIONS.length
        setContextLength(CONTEXT_LENGTH_OPTIONS[newIndex].value)
        return
      }
    }

    if (
      currentScreen === 'apiKey' &&
      ((key.ctrl && input === 'v') || (key.meta && input === 'v'))
    ) {
      setModelLoadError(
        "Please use your terminal's paste functionality or type the API key manually",
      )
      return
    }

    if (currentScreen === 'modelParams' && key.tab) {
      const formFields = getFormFieldsForModelParams()
      setActiveFieldIndex(current => (current + 1) % formFields.length)
      return
    }

    if (currentScreen === 'modelParams' && key.return) {
      const formFields = getFormFieldsForModelParams()
      const currentField = formFields[activeFieldIndex]

      if (
        currentField.name === 'submit' ||
        activeFieldIndex === formFields.length - 1
      ) {
        handleModelParamsSubmit()
      } else if (currentField.component === 'select') {
        setActiveFieldIndex(current =>
          Math.min(current + 1, formFields.length - 1),
        )
      }
      return
    }
  })

  function getFormFieldsForModelParams() {
    return [
      {
        name: 'maxTokens',
        label: 'Maximum Tokens',
        description: 'Select the maximum number of tokens to generate.',
        value: parseInt(maxTokens),
        component: 'select',
        options: MAX_TOKENS_OPTIONS.map(option => ({
          label: option.label,
          value: option.value.toString(),
        })),
        defaultValue: maxTokens,
      },
      ...(supportsReasoningEffort
        ? [
            {
              name: 'reasoningEffort',
              label: 'Reasoning Effort',
              description: 'Controls reasoning depth for complex problems.',
              value: reasoningEffort,
              component: 'select',
            },
          ]
        : []),
      {
        name: 'submit',
        label: 'Continue →',
        component: 'button',
      },
    ]
  }

  if (currentScreen === 'apiKey') {
    const modelTypeText = 'this model profile'

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            API Key Setup{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>
              Enter your {getProviderLabel(selectedProvider, 0).split(' (')[0]}{' '}
              API key for {modelTypeText}:
            </Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                This key will be stored locally and used to access the{' '}
                {selectedProvider} API.
                <Newline />
                Your key is never sent to our servers.
                <Newline />
                <Newline />
                {selectedProvider === 'kimi' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://platform.moonshot.cn/console/api-keys
                    </Text>
                  </>
                )}
                {selectedProvider === 'deepseek' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://platform.deepseek.com/api_keys
                    </Text>
                  </>
                )}
                {selectedProvider === 'siliconflow' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://cloud.siliconflow.cn/i/oJWsm6io
                    </Text>
                  </>
                )}
                {selectedProvider === 'qwen' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://bailian.console.aliyun.com/?tab=model#/api-key
                    </Text>
                  </>
                )}
                {selectedProvider === 'glm' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://open.bigmodel.cn (API Keys section)
                    </Text>
                  </>
                )}
                {selectedProvider === 'glm-coding' && (
                  <>
                    💡 This is for GLM Coding Plan API.{' '}
                    <Text color={theme.suggestion}>
                      Use the same API key as regular GLM
                    </Text>
                    <Newline />
                    <Text dimColor>
                      Note: This uses a special endpoint for coding tasks.
                    </Text>
                  </>
                )}
                {selectedProvider === 'minimax' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://www.minimax.io/platform/user-center/basic-information
                    </Text>
                  </>
                )}
                {selectedProvider === 'minimax-coding' && (
                  <>
                    💡 Get your Coding Plan API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://platform.minimaxi.com/user-center/payment/coding-plan
                    </Text>
                    <Newline />
                    <Text dimColor>
                      Note: This requires a MiniMax Coding Plan subscription.
                    </Text>
                  </>
                )}
                {selectedProvider === 'baidu-qianfan' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://console.bce.baidu.com/iam/#/iam/accesslist
                    </Text>
                  </>
                )}
                {selectedProvider === 'anthropic' && (
                  <>💡 Get your API key from your provider dashboard.</>
                )}
                {selectedProvider === 'openai' && (
                  <>
                    💡 Get your API key from:{' '}
                    <Text color={theme.suggestion}>
                      https://platform.openai.com/api-keys
                    </Text>
                  </>
                )}
              </Text>
            </Box>

            <Box flexDirection="column">
              <Box>
                <TextInput
                  placeholder="Paste your API key here..."
                  value={apiKey}
                  onChange={handleApiKeyChange}
                  onSubmit={handleApiKeySubmit}
                  onPaste={handleApiKeyChange}
                  mask="*"
                  columns={80}
                  cursorOffset={cursorOffset}
                  onChangeCursorOffset={handleCursorOffsetChange}
                  showCursor={true}
                />
              </Box>

              {apiKey && (
                <Box marginTop={1}>
                  <Text color={theme.secondaryText}>
                    Key: {formatApiKeyDisplay(apiKey)} ({apiKey.length} chars)
                  </Text>
                </Box>
              )}
            </Box>

            {apiKeyCleanedNotification && (
              <Box marginTop={1}>
                <Text color={theme.success}>
                  ✓ API key cleaned: removed line breaks and trimmed whitespace
                </Text>
              </Box>
            )}

            <Box marginTop={1}>
              <Text>
                <Text color={theme.suggestion} dimColor={!apiKey}>
                  [Submit API Key]
                </Text>
                <Text> - Press Enter to validate and continue</Text>
              </Text>
            </Box>

            {isLoadingModels && (
              <Box marginTop={1}>
                <Text color={theme.suggestion}>
                  Validating API key and fetching models...
                </Text>
                {providerBaseUrl && (
                  <Text dimColor>Endpoint: {providerBaseUrl}/v1/models</Text>
                )}
              </Box>
            )}

            {modelLoadError && (
              <Box marginTop={1} flexDirection="column">
                <Text color="red">❌ API Key Validation Failed</Text>
                <Text color="red">{modelLoadError}</Text>
                {providerBaseUrl && (
                  <Box marginTop={1}>
                    <Text dimColor>
                      Attempted endpoint: {providerBaseUrl}/v1/models
                    </Text>
                  </Box>
                )}
                <Box marginTop={1}>
                  <Text color={theme.warning}>
                    Please check your API key and try again.
                  </Text>
                </Box>
              </Box>
            )}
            <Box marginTop={1}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Enter</Text> to continue,{' '}
                <Text color={theme.suggestion}>Tab</Text> to{' '}
                {selectedProvider === 'anthropic' ||
                selectedProvider === 'kimi' ||
                selectedProvider === 'deepseek' ||
                selectedProvider === 'qwen' ||
                selectedProvider === 'glm' ||
                selectedProvider === 'glm-coding' ||
                selectedProvider === 'minimax' ||
                selectedProvider === 'minimax-coding' ||
                selectedProvider === 'baidu-qianfan' ||
                selectedProvider === 'siliconflow' ||
                selectedProvider === 'custom-openai'
                  ? 'skip to manual model input'
                  : 'skip using a key'}
                , or <Text color={theme.suggestion}>Esc</Text> to go back
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'model') {
    const modelTypeText = 'this model profile'

    return (
      <ModelSelectionScreen
        theme={theme}
        exitState={exitState}
        providerLabel={getProviderLabel(
          selectedProvider,
          availableModels.length,
        ).split(' (')[0]!}
        modelTypeText={modelTypeText}
        availableModels={availableModels}
        modelSearchQuery={modelSearchQuery}
        onModelSearchChange={handleModelSearchChange}
        modelSearchCursorOffset={modelSearchCursorOffset}
        onModelSearchCursorOffsetChange={handleModelSearchCursorOffsetChange}
        onModelSelect={handleModelSelection}
      />
    )
  }

  if (currentScreen === 'modelParams') {
    const formFields = getFormFieldsForModelParams()

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            Model Parameters{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>Configure parameters for {selectedModel}:</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                Use <Text color={theme.suggestion}>Tab</Text> to navigate
                between fields. Press{' '}
                <Text color={theme.suggestion}>Enter</Text> to submit.
              </Text>
            </Box>

            <Box flexDirection="column">
              {formFields.map((field, index) => (
                <Box flexDirection="column" marginY={1} key={field.name}>
                  {field.component !== 'button' ? (
                    <>
                      <Text
                        bold
                        color={
                          activeFieldIndex === index ? theme.success : undefined
                        }
                      >
                        {field.label}
                      </Text>
                      {field.description && (
                        <Text color={theme.secondaryText}>
                          {field.description}
                        </Text>
                      )}
                    </>
                  ) : (
                    <Text
                      bold
                      color={
                        activeFieldIndex === index ? theme.success : undefined
                      }
                    >
                      {field.label}
                    </Text>
                  )}
                  <Box marginY={1}>
                    {activeFieldIndex === index ? (
                      field.component === 'select' ? (
                        field.name === 'maxTokens' ? (
                          <Select
                            options={field.options || []}
                            onChange={value => {
                              const numValue = parseInt(value)
                              setMaxTokens(numValue.toString())
                              setSelectedMaxTokensPreset(numValue)
                              setMaxTokensCursorOffset(
                                numValue.toString().length,
                              )
                              setTimeout(() => {
                                setActiveFieldIndex(index + 1)
                              }, 100)
                            }}
                            defaultValue={field.defaultValue}
                            visibleOptionCount={10}
                          />
                        ) : (
                          <Select
                            options={reasoningEffortOptions}
                            onChange={value => {
                              setReasoningEffort(value as ReasoningEffortOption)
                              setTimeout(() => {
                                setActiveFieldIndex(index + 1)
                              }, 100)
                            }}
                            defaultValue={reasoningEffort}
                            visibleOptionCount={8}
                          />
                        )
                      ) : null
                    ) : field.name === 'maxTokens' ? (
                      <Text color={theme.secondaryText}>
                        Current:{' '}
                        <Text color={theme.suggestion}>
                          {MAX_TOKENS_OPTIONS.find(
                            opt => opt.value === parseInt(maxTokens),
                          )?.label || `${maxTokens} tokens`}
                        </Text>
                      </Text>
                    ) : field.name === 'reasoningEffort' ? (
                      <Text color={theme.secondaryText}>
                        Current:{' '}
                        <Text color={theme.suggestion}>{reasoningEffort}</Text>
                      </Text>
                    ) : null}
                  </Box>
                </Box>
              ))}

              <Box marginTop={1}>
                <Text dimColor>
                  Press <Text color={theme.suggestion}>Tab</Text> to navigate,{' '}
                  <Text color={theme.suggestion}>Enter</Text> to continue, or{' '}
                  <Text color={theme.suggestion}>Esc</Text> to go back
                </Text>
              </Box>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'resourceName') {
    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            Azure Resource Setup{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>Enter your Azure OpenAI resource name:</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                This is the name of your Azure OpenAI resource (without the full
                domain).
                <Newline />
                For example, if your endpoint is
                "https://myresource.openai.azure.com", enter "myresource".
              </Text>
            </Box>

            <Box>
              <TextInput
                placeholder="myazureresource"
                value={resourceName}
                onChange={setResourceName}
                onSubmit={handleResourceNameSubmit}
                columns={100}
                cursorOffset={resourceNameCursorOffset}
                onChangeCursorOffset={setResourceNameCursorOffset}
                showCursor={true}
              />
            </Box>

            <Box marginTop={1}>
              <Text>
                <Text color={theme.suggestion} dimColor={!resourceName}>
                  [Submit Resource Name]
                </Text>
                <Text> - Press Enter or click to continue</Text>
              </Text>
            </Box>

            <Box marginTop={1}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Enter</Text> to continue or{' '}
                <Text color={theme.suggestion}>Esc</Text> to go back
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'baseUrl') {
    const isCustomOpenAI = selectedProvider === 'custom-openai'

    if (isCustomOpenAI) {
      return (
        <Box flexDirection="column" gap={1}>
          <Box
            flexDirection="column"
            gap={1}
            borderStyle="round"
            borderColor={theme.secondaryBorder}
            paddingX={2}
            paddingY={1}
          >
            <Text bold>
              Custom API Server Setup{' '}
              {exitState.pending
                ? `(press ${exitState.keyName} again to exit)`
                : ''}
            </Text>
            <Box flexDirection="column" gap={1}>
              <Text bold>Enter your custom API URL:</Text>
              <Box flexDirection="column" width={70}>
                <Text color={theme.secondaryText}>
                  This is the base URL for your OpenAI-compatible API.
                  <Newline />
                  For example: https://api.example.com/v1
                </Text>
              </Box>

              <Box>
                <TextInput
                  placeholder="https://api.example.com/v1"
                  value={customBaseUrl}
                  onChange={setCustomBaseUrl}
                  onSubmit={handleCustomBaseUrlSubmit}
                  columns={100}
                  cursorOffset={customBaseUrlCursorOffset}
                  onChangeCursorOffset={setCustomBaseUrlCursorOffset}
                  showCursor={!isLoadingModels}
                  focus={!isLoadingModels}
                />
              </Box>

              <Box marginTop={1}>
                <Text>
                  <Text
                    color={
                      isLoadingModels ? theme.secondaryText : theme.suggestion
                    }
                  >
                    [Submit Base URL]
                  </Text>
                  <Text> - Press Enter or click to continue</Text>
                </Text>
              </Box>

              <Box marginTop={1}>
                <Text dimColor>
                  Press <Text color={theme.suggestion}>Enter</Text> to continue
                  or <Text color={theme.suggestion}>Esc</Text> to go back
                </Text>
              </Box>
            </Box>
          </Box>
        </Box>
      )
    }

    const providerName = providers[selectedProvider]?.name || selectedProvider
    const defaultUrl = providers[selectedProvider]?.baseURL || ''

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            {providerName} API Configuration{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>Configure the API endpoint for {providerName}:</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                {selectedProvider === 'ollama' ? (
                  <>
                    This is the URL of your Ollama server.
                    <Newline />
                    Default is http://localhost:11434/v1 for local Ollama
                    installations.
                  </>
                ) : (
                  <>
                    This is the base URL for the {providerName} API.
                    <Newline />
                    You can modify this URL or press Enter to use the default.
                  </>
                )}
              </Text>
            </Box>

            <Box>
              <TextInput
                placeholder={defaultUrl}
                value={providerBaseUrl}
                onChange={setProviderBaseUrl}
                onSubmit={handleProviderBaseUrlSubmit}
                columns={100}
                cursorOffset={providerBaseUrlCursorOffset}
                onChangeCursorOffset={setProviderBaseUrlCursorOffset}
                showCursor={!isLoadingModels}
                focus={!isLoadingModels}
              />
            </Box>

            <Box marginTop={1}>
              <Text>
                <Text
                  color={
                    isLoadingModels ? theme.secondaryText : theme.suggestion
                  }
                >
                  [Submit Base URL]
                </Text>
                <Text> - Press Enter or click to continue</Text>
              </Text>
            </Box>

            {isLoadingModels && (
              <Box marginTop={1}>
                <Text color={theme.success}>
                  {selectedProvider === 'ollama'
                    ? 'Connecting to Ollama server...'
                    : `Connecting to ${providerName}...`}
                </Text>
              </Box>
            )}

            {modelLoadError && (
              <Box marginTop={1}>
                <Text color="red">Error: {modelLoadError}</Text>
              </Box>
            )}

            <Box marginTop={1}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Enter</Text> to continue or{' '}
                <Text color={theme.suggestion}>Esc</Text> to go back
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'modelInput') {
    const modelTypeText = 'this model profile'

    let screenTitle = 'Manual Model Setup'
    let description = 'Enter the model name manually'
    let placeholder = 'gpt-4'
    let examples = 'For example: "gpt-4", "gpt-3.5-turbo", etc.'

    if (selectedProvider === 'azure') {
      screenTitle = 'Azure Model Setup'
      description = `Enter your Azure OpenAI deployment name for ${modelTypeText}:`
      examples = 'For example: "gpt-4", "gpt-35-turbo", etc.'
      placeholder = 'gpt-4'
    } else if (selectedProvider === 'anthropic') {
      screenTitle = 'Model Setup'
      description = `Enter the model name for ${modelTypeText}:`
      examples =
        'For example: "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", etc.'
      placeholder = 'claude-3-5-sonnet-latest'
    } else if (selectedProvider === 'bigdream') {
      screenTitle = 'BigDream Model Setup'
      description = `Enter the BigDream model name for ${modelTypeText}:`
      examples =
        'For example: "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", etc.'
      placeholder = 'claude-3-5-sonnet-latest'
    } else if (selectedProvider === 'kimi') {
      screenTitle = 'Kimi Model Setup'
      description = `Enter the Kimi model name for ${modelTypeText}:`
      examples = 'For example: "kimi-k2-0711-preview"'
      placeholder = 'kimi-k2-0711-preview'
    } else if (selectedProvider === 'deepseek') {
      screenTitle = 'DeepSeek Model Setup'
      description = `Enter the DeepSeek model name for ${modelTypeText}:`
      examples =
        'For example: "deepseek-chat", "deepseek-coder", "deepseek-reasoner", etc.'
      placeholder = 'deepseek-chat'
    } else if (selectedProvider === 'siliconflow') {
      screenTitle = 'SiliconFlow Model Setup'
      description = `Enter the SiliconFlow model name for ${modelTypeText}:`
      examples =
        'For example: "Qwen/Qwen2.5-72B-Instruct", "meta-llama/Meta-Llama-3.1-8B-Instruct", etc.'
      placeholder = 'Qwen/Qwen2.5-72B-Instruct'
    } else if (selectedProvider === 'qwen') {
      screenTitle = 'Qwen Model Setup'
      description = `Enter the Qwen model name for ${modelTypeText}:`
      examples = 'For example: "qwen-plus", "qwen-turbo", "qwen-max", etc.'
      placeholder = 'qwen-plus'
    } else if (selectedProvider === 'glm') {
      screenTitle = 'GLM Model Setup'
      description = `Enter the GLM model name for ${modelTypeText}:`
      examples = 'For example: "glm-4", "glm-4v", "glm-3-turbo", etc.'
      placeholder = 'glm-4'
    } else if (selectedProvider === 'glm-coding') {
      screenTitle = 'GLM Coding Plan Model Setup'
      description = `Enter the GLM model name for ${modelTypeText}:`
      examples = 'For Coding Plan, typically use: "GLM-4.6" or other GLM models'
      placeholder = 'GLM-4.6'
    } else if (selectedProvider === 'minimax') {
      screenTitle = 'MiniMax Model Setup'
      description = `Enter the MiniMax model name for ${modelTypeText}:`
      examples =
        'For example: "abab6.5s-chat", "abab6.5g-chat", "abab5.5s-chat", etc.'
      placeholder = 'abab6.5s-chat'
    } else if (selectedProvider === 'minimax-coding') {
      screenTitle = 'MiniMax Coding Plan Model Setup'
      description = `Enter the MiniMax model name for ${modelTypeText}:`
      examples = 'For Coding Plan, use: "MiniMax-M2"'
      placeholder = 'MiniMax-M2'
    } else if (selectedProvider === 'baidu-qianfan') {
      screenTitle = 'Baidu Qianfan Model Setup'
      description = `Enter the Baidu Qianfan model name for ${modelTypeText}:`
      examples =
        'For example: "ERNIE-4.0-8K", "ERNIE-3.5-8K", "ERNIE-Speed-128K", etc.'
      placeholder = 'ERNIE-4.0-8K'
    } else if (selectedProvider === 'custom-openai') {
      screenTitle = 'Custom API Model Setup'
      description = `Enter the model name for ${modelTypeText}:`
      examples = 'Enter the exact model name as supported by your API endpoint.'
      placeholder = 'model-name'
    }

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            {screenTitle}{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>{description}</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                {selectedProvider === 'azure'
                  ? 'This is the deployment name you configured in your Azure OpenAI resource.'
                  : selectedProvider === 'anthropic'
                    ? 'This should match a model identifier supported by your API endpoint.'
                    : selectedProvider === 'bigdream'
                      ? 'This should be a valid model identifier supported by BigDream.'
                      : selectedProvider === 'kimi'
                        ? 'This should be a valid Kimi model identifier from Moonshot AI.'
                        : selectedProvider === 'deepseek'
                          ? 'This should be a valid DeepSeek model identifier.'
                          : selectedProvider === 'siliconflow'
                            ? 'This should be a valid SiliconFlow model identifier.'
                            : selectedProvider === 'qwen'
                              ? 'This should be a valid Qwen model identifier from Alibaba Cloud.'
                              : selectedProvider === 'glm'
                                ? 'This should be a valid GLM model identifier from Zhipu AI.'
                                : selectedProvider === 'minimax'
                                  ? 'This should be a valid MiniMax model identifier.'
                                  : selectedProvider === 'baidu-qianfan'
                                    ? 'This should be a valid Baidu Qianfan model identifier.'
                                    : 'This should match the model name supported by your API endpoint.'}
                <Newline />
                {examples}
              </Text>
            </Box>

            <Box>
              <TextInput
                placeholder={placeholder}
                value={customModelName}
                onChange={setCustomModelName}
                onSubmit={handleCustomModelSubmit}
                columns={100}
                cursorOffset={customModelNameCursorOffset}
                onChangeCursorOffset={setCustomModelNameCursorOffset}
                showCursor={true}
              />
            </Box>

            <Box marginTop={1}>
              <Text>
                <Text color={theme.suggestion} dimColor={!customModelName}>
                  [Submit Model Name]
                </Text>
                <Text> - Press Enter or click to continue</Text>
              </Text>
            </Box>

            <Box marginTop={1}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Enter</Text> to continue or{' '}
                <Text color={theme.suggestion}>Esc</Text> to go back
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'contextLength') {
    const selectedOption =
      CONTEXT_LENGTH_OPTIONS.find(opt => opt.value === contextLength) ||
      CONTEXT_LENGTH_OPTIONS[2]

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            Context Length Configuration{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>Choose the context window length for your model:</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                This determines how much conversation history and context the
                model can process at once. Higher values allow for longer
                conversations but may increase costs.
              </Text>
            </Box>

            <Box flexDirection="column" marginY={1}>
              {CONTEXT_LENGTH_OPTIONS.map((option, index) => {
                const isSelected = option.value === contextLength
                return (
                  <Box key={option.value} flexDirection="row">
                    <Text color={isSelected ? 'blue' : undefined}>
                      {isSelected ? '→ ' : '  '}
                      {option.label}
                      {option.value === DEFAULT_CONTEXT_LENGTH
                        ? ' (recommended)'
                        : ''}
                    </Text>
                  </Box>
                )
              })}
            </Box>

            <Box flexDirection="column" marginY={1}>
              <Text dimColor>
                Selected:{' '}
                <Text color={theme.suggestion}>{selectedOption.label}</Text>
              </Text>
            </Box>
          </Box>
        </Box>

        <Box marginLeft={1}>
          <Text dimColor>
            ↑/↓ to select · Enter to continue · Esc to go back
          </Text>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'connectionTest') {
    const providerDisplayName = getProviderLabel(selectedProvider, 0).split(
      ' (',
    )[0]

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            Connection Test{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>Testing connection to {providerDisplayName}...</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                This will verify your configuration by sending a test request to
                the API.
                {selectedProvider === 'minimax' && (
                  <>
                    <Newline />
                    For MiniMax, we'll test both v2 and v1 endpoints to find the
                    best one.
                  </>
                )}
              </Text>
            </Box>

            {!connectionTestResult && !isTestingConnection && (
              <Box marginY={1}>
                <Text>
                  <Text color={theme.suggestion}>Press Enter</Text> to start the
                  connection test
                </Text>
              </Box>
            )}

            {isTestingConnection && (
              <Box marginY={1}>
                <Text color={theme.suggestion}>🔄 Testing connection...</Text>
              </Box>
            )}

            {connectionTestResult && (
              <Box flexDirection="column" marginY={1} paddingX={1}>
                <Text
                  color={connectionTestResult.success ? theme.success : 'red'}
                >
                  {connectionTestResult.message}
                </Text>

                {connectionTestResult.endpoint && (
                  <Text color={theme.secondaryText}>
                    Endpoint: {connectionTestResult.endpoint}
                  </Text>
                )}

                {connectionTestResult.details && (
                  <Text color={theme.secondaryText}>
                    Details: {connectionTestResult.details}
                  </Text>
                )}

                {connectionTestResult.success ? (
                  <Box marginTop={1}>
                    <Text color={theme.success}>
                      ✅ Automatically proceeding to confirmation...
                    </Text>
                  </Box>
                ) : (
                  <Box marginTop={1}>
                    <Text>
                      <Text color={theme.suggestion}>Press Enter</Text> to retry
                      test, or <Text color={theme.suggestion}>Esc</Text> to go
                      back
                    </Text>
                  </Box>
                )}
              </Box>
            )}

            <Box marginTop={1}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Esc</Text> to go back to
                context length
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'confirmation') {

    const providerDisplayName = getProviderLabel(selectedProvider, 0).split(
      ' (',
    )[0]

    const showsApiKey = selectedProvider !== 'ollama'

    return (
      <Box flexDirection="column" gap={1}>
        <Box
          flexDirection="column"
          gap={1}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={1}
        >
          <Text bold>
            Configuration Confirmation{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={1}>
            <Text bold>Confirm your model configuration:</Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                Please review your selections before saving.
              </Text>
            </Box>

            {validationError && (
              <Box flexDirection="column" marginY={1} paddingX={1}>
                <Text color={theme.error} bold>
                  ⚠ Configuration Error:
                </Text>
                <Text color={theme.error}>{validationError}</Text>
              </Box>
            )}

            <Box flexDirection="column" marginY={1} paddingX={1}>
              <Text>
                <Text bold>Provider: </Text>
                <Text color={theme.suggestion}>{providerDisplayName}</Text>
              </Text>

              {selectedProvider === 'azure' && (
                <Text>
                  <Text bold>Resource Name: </Text>
                  <Text color={theme.suggestion}>{resourceName}</Text>
                </Text>
              )}

              {selectedProvider === 'ollama' && (
                <Text>
                  <Text bold>Server URL: </Text>
                  <Text color={theme.suggestion}>{ollamaBaseUrl}</Text>
                </Text>
              )}

              {selectedProvider === 'custom-openai' && (
                <Text>
                  <Text bold>API Base URL: </Text>
                  <Text color={theme.suggestion}>{customBaseUrl}</Text>
                </Text>
              )}

              <Text>
                <Text bold>Model: </Text>
                <Text color={theme.suggestion}>{selectedModel}</Text>
              </Text>

              {apiKey && showsApiKey && (
                <Text>
                  <Text bold>API Key: </Text>
                  <Text color={theme.suggestion}>
                    {formatApiKeyDisplay(apiKey)}
                  </Text>
                </Text>
              )}

              {maxTokens && (
                <Text>
                  <Text bold>Max Tokens: </Text>
                  <Text color={theme.suggestion}>{maxTokens}</Text>
                </Text>
              )}

              <Text>
                <Text bold>Context Length: </Text>
                <Text color={theme.suggestion}>
                  {CONTEXT_LENGTH_OPTIONS.find(
                    opt => opt.value === contextLength,
                  )?.label || `${contextLength.toLocaleString()} tokens`}
                </Text>
              </Text>

              {supportsReasoningEffort && (
                <Text>
                  <Text bold>Reasoning Effort: </Text>
                  <Text color={theme.suggestion}>{reasoningEffort}</Text>
                </Text>
              )}
            </Box>

            <Box marginTop={1}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Esc</Text> to go back to
                model parameters or <Text color={theme.suggestion}>Enter</Text>{' '}
                to save configuration
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'partnerProviders') {
    const footerMarginTop = tightLayout ? 0 : 1
    return (
      <Box flexDirection="column" gap={containerGap}>
        <Box
          flexDirection="column"
          gap={containerGap}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={containerPaddingY}
        >
          <Text bold>
            Partner Providers{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={containerGap}>
            <Text bold>
              Select a partner AI provider for this model profile:
            </Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                {compactLayout
                  ? 'Choose an official partner provider.'
                  : 'Choose from official partner providers to access their models and services.'}
              </Text>
            </Box>

            <WindowedOptions
              options={partnerProviderOptions}
              focusedIndex={partnerProviderFocusIndex}
              maxVisible={getSafeVisibleOptionCount(
                6,
                partnerProviderOptions.length,
                partnerReservedLines,
              )}
              theme={theme}
            />

            <Box marginTop={footerMarginTop}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Esc</Text> to go back to
                main menu
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  if (currentScreen === 'partnerCodingPlans') {
    const footerMarginTop = tightLayout ? 0 : 1
    return (
      <Box flexDirection="column" gap={containerGap}>
        <Box
          flexDirection="column"
          gap={containerGap}
          borderStyle="round"
          borderColor={theme.secondaryBorder}
          paddingX={2}
          paddingY={containerPaddingY}
        >
          <Text bold>
            Partner Coding Plans{' '}
            {exitState.pending
              ? `(press ${exitState.keyName} again to exit)`
              : ''}
          </Text>
          <Box flexDirection="column" gap={containerGap}>
            <Text bold>
              Select a partner coding plan for specialized programming
              assistance:
            </Text>
            <Box flexDirection="column" width={70}>
              <Text color={theme.secondaryText}>
                {compactLayout ? (
                  'Specialized coding models from partners.'
                ) : (
                  <>
                    These are specialized models optimized for coding and
                    development tasks.
                    <Newline />
                    They require specific coding plan subscriptions from the
                    respective providers.
                  </>
                )}
              </Text>
            </Box>

            <WindowedOptions
              options={codingPlanOptions}
              focusedIndex={codingPlanFocusIndex}
              maxVisible={getSafeVisibleOptionCount(
                5,
                codingPlanOptions.length,
                codingReservedLines,
              )}
              theme={theme}
            />

            <Box marginTop={footerMarginTop}>
              <Text dimColor>
                Press <Text color={theme.suggestion}>Esc</Text> to go back to
                main menu
              </Text>
            </Box>
          </Box>
        </Box>
      </Box>
    )
  }

  return (
    <ScreenContainer
      title="Provider Selection"
      exitState={exitState}
      paddingY={containerPaddingY}
      gap={containerGap}
      children={
        <Box flexDirection="column" gap={containerGap}>
          <Text bold>
            Select your preferred AI provider for this model profile:
          </Text>
          <Box flexDirection="column" width={70}>
            <Text color={theme.secondaryText}>
              {compactLayout ? (
                'Choose the provider to use for this profile.'
              ) : (
                <>
                  Choose the provider you want to use for this model profile.
                  <Newline />
                  This will determine which models are available to you.
                </>
              )}
            </Text>
          </Box>

          <WindowedOptions
            options={mainMenuOptions}
            focusedIndex={providerFocusIndex}
            maxVisible={getSafeVisibleOptionCount(
              5,
              mainMenuOptions.length,
              providerReservedLines,
            )}
            theme={theme}
          />

          <Box marginTop={tightLayout ? 0 : 1}>
            <Text dimColor>
              You can change this later by running{' '}
              <Text color={theme.suggestion}>/model</Text> again
            </Text>
          </Box>
        </Box>
      }
    />
  )
}
