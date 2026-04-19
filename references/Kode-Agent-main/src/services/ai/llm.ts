import '@anthropic-ai/sdk/shims/node'
import Anthropic, { APIConnectionError, APIError } from '@anthropic-ai/sdk'
import { StreamingEvent } from './adapters/base'
import { AnthropicBedrock } from '@anthropic-ai/bedrock-sdk'
import { AnthropicVertex } from '@anthropic-ai/vertex-sdk'
import type { BetaUsage } from '@anthropic-ai/sdk/resources/beta/messages/messages.mjs'
import chalk from 'chalk'
import { createHash, randomUUID, UUID } from 'crypto'
import 'dotenv/config'

import { addToTotalCost } from '@costTracker'
import models from '@constants/models'
import type { AssistantMessage, UserMessage } from '@query'
import { Tool, getToolDescription } from '@tool'
import {
  getAnthropicApiKey,
  getGlobalConfig,
  ModelProfile,
} from '@utils/config'
import { logError } from '@utils/log'
import { USER_AGENT } from '@utils/system/http'
import {
  createAssistantAPIErrorMessage,
  normalizeContentFromAPI,
} from '@utils/messages'
import { countTokens } from '@utils/model/tokens'
import { setRequestStatus } from '@utils/session/requestStatus'
import { withVCR } from '@services/vcr'
import {
  debug as debugLogger,
  markPhase,
  getCurrentRequest,
  logLLMInteraction,
  logSystemPromptConstruction,
  logErrorWithDiagnosis,
} from '@utils/log/debugLogger'
import {
  MessageContextManager,
  createRetentionStrategy,
} from '@utils/session/messageContextManager'
import { getModelManager } from '@utils/model'
import { zodToJsonSchema } from 'zod-to-json-schema'
import type { BetaMessageStream } from '@anthropic-ai/sdk/lib/BetaMessageStream.mjs'
import { ModelAdapterFactory } from './modelAdapterFactory'
import { UnifiedRequestParams } from '@kode-types/modelCapabilities'
import { responseStateManager, getConversationId } from './responseStateManager'
import type { ToolUseContext } from '@tool'
import type {
  Message as APIMessage,
  MessageParam,
  TextBlockParam,
} from '@anthropic-ai/sdk/resources/index.mjs'
import { USE_BEDROCK, USE_VERTEX } from '@utils/model'
import { getCLISyspromptPrefix } from '@constants/prompts'
import { getVertexRegionForModel } from '@utils/model'
import OpenAI from 'openai'
import type { ChatCompletionStream } from 'openai/lib/ChatCompletionStream'
import { ContentBlock } from '@anthropic-ai/sdk/resources/messages/messages'
import { nanoid } from 'nanoid'
import {
  getCompletionWithProfile,
  getGPT5CompletionWithProfile,
} from './openai'
import { getReasoningEffort } from '@utils/model/thinking'
import { parseToolUsePartialJsonOrThrow } from '@utils/tooling/toolUsePartialJson'
import { convertAnthropicMessagesToOpenAIMessages as convertAnthropicMessagesToOpenAIMessagesUtil } from '@utils/model/openaiMessageConversion'
import { generateKodeContext, refreshKodeContext } from '@services/kodeContext'
import {
  API_ERROR_MESSAGE_PREFIX,
  CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE,
  INVALID_API_KEY_ERROR_MESSAGE,
  MAIN_QUERY_TEMPERATURE,
  NO_CONTENT_MESSAGE,
  PROMPT_TOO_LONG_ERROR_MESSAGE,
} from './llmConstants'

function isGPT5Model(modelName: string): boolean {
  return modelName.startsWith('gpt-5')
}

function getModelConfigForDebug(model: string): {
  modelName: string
  provider: string
  apiKeyStatus: 'configured' | 'missing' | 'invalid'
  baseURL?: string
  maxTokens?: number
  reasoningEffort?: string
  isStream?: boolean
  temperature?: number
} {
  const config = getGlobalConfig()
  const modelManager = getModelManager()

  const modelProfile = modelManager.getModel('main')

  let apiKeyStatus: 'configured' | 'missing' | 'invalid' = 'missing'
  let baseURL: string | undefined
  let maxTokens: number | undefined
  let reasoningEffort: string | undefined

  if (modelProfile) {
    apiKeyStatus = modelProfile.apiKey ? 'configured' : 'missing'
    baseURL = modelProfile.baseURL
    maxTokens = modelProfile.maxTokens
    reasoningEffort = modelProfile.reasoningEffort
  } else {
    apiKeyStatus = 'missing'
    maxTokens = undefined
    reasoningEffort = undefined
  }

  return {
    modelName: model,
    provider: modelProfile?.provider || config.primaryProvider || 'anthropic',
    apiKeyStatus,
    baseURL,
    maxTokens,
    reasoningEffort,
    isStream: config.stream || false,
    temperature: MAIN_QUERY_TEMPERATURE,
  }
}

export { generateKodeContext, refreshKodeContext }

interface StreamResponse extends APIMessage {
  ttftMs?: number
}

export {
  API_ERROR_MESSAGE_PREFIX,
  PROMPT_TOO_LONG_ERROR_MESSAGE,
  CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE,
  INVALID_API_KEY_ERROR_MESSAGE,
  NO_CONTENT_MESSAGE,
  MAIN_QUERY_TEMPERATURE,
}
const PROMPT_CACHING_ENABLED = !process.env.DISABLE_PROMPT_CACHING

const HAIKU_COST_PER_MILLION_INPUT_TOKENS = 0.8
const HAIKU_COST_PER_MILLION_OUTPUT_TOKENS = 4
const HAIKU_COST_PER_MILLION_PROMPT_CACHE_WRITE_TOKENS = 1
const HAIKU_COST_PER_MILLION_PROMPT_CACHE_READ_TOKENS = 0.08

const SONNET_COST_PER_MILLION_INPUT_TOKENS = 3
const SONNET_COST_PER_MILLION_OUTPUT_TOKENS = 15
const SONNET_COST_PER_MILLION_PROMPT_CACHE_WRITE_TOKENS = 3.75
const SONNET_COST_PER_MILLION_PROMPT_CACHE_READ_TOKENS = 0.3

const MAX_RETRIES = process.env.USER_TYPE === 'SWE_BENCH' ? 100 : 10
const BASE_DELAY_MS = 500

interface RetryOptions {
  maxRetries?: number
  signal?: AbortSignal
}

function abortableDelay(delayMs: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new Error('Request was aborted'))
      return
    }

    const timeoutId = setTimeout(() => {
      resolve()
    }, delayMs)

    if (signal) {
      const abortHandler = () => {
        clearTimeout(timeoutId)
        reject(new Error('Request was aborted'))
      }
      signal.addEventListener('abort', abortHandler, { once: true })
    }
  })
}

function getRetryDelay(
  attempt: number,
  retryAfterHeader?: string | null,
): number {
  if (retryAfterHeader) {
    const seconds = parseInt(retryAfterHeader, 10)
    if (!isNaN(seconds)) {
      return seconds * 1000
    }
  }
  return Math.min(BASE_DELAY_MS * Math.pow(2, attempt - 1), 32000)
}

function shouldRetry(error: APIError): boolean {
  if (error.message?.includes('"type":"overloaded_error"')) {
    return process.env.USER_TYPE === 'SWE_BENCH'
  }

  const shouldRetryHeader = error.headers?.['x-should-retry']

  if (shouldRetryHeader === 'true') return true
  if (shouldRetryHeader === 'false') return false

  if (error instanceof APIConnectionError) {
    return true
  }

  if (!error.status) return false

  if (error.status === 408) return true

  if (error.status === 409) return true

  if (error.status === 429) return true

  if (error.status && error.status >= 500) return true

  return false
}

async function withRetry<T>(
  operation: (attempt: number) => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const maxRetries = options.maxRetries ?? MAX_RETRIES
  let lastError: unknown

  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await operation(attempt)
    } catch (error) {
      lastError = error
      if (
        attempt > maxRetries ||
        !(error instanceof APIError) ||
        !shouldRetry(error)
      ) {
        throw error
      }

      if (options.signal?.aborted) {
        throw new Error('Request cancelled by user')
      }

      const retryAfter = error.headers?.['retry-after'] ?? null
      const delayMs = getRetryDelay(attempt, retryAfter)

      debugLogger.warn('LLM_API_RETRY', {
        name: error.name,
        message: error.message,
        status: error.status,
        attempt,
        maxRetries,
        delayMs,
      })

      try {
        await abortableDelay(delayMs, options.signal)
      } catch (delayError) {
        if (delayError.message === 'Request was aborted') {
          throw new Error('Request cancelled by user')
        }
        throw delayError
      }
    }
  }

  throw lastError
}

export async function fetchAnthropicModels(
  baseURL: string,
  apiKey: string,
): Promise<any[]> {
  try {
    const modelsURL = baseURL
      ? `${baseURL.replace(/\/+$/, '')}/v1/models`
      : 'https://api.anthropic.com/v1/models'

    const response = await fetch(modelsURL, {
      method: 'GET',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'User-Agent': USER_AGENT,
      },
    })

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error(
          'Invalid API key. Please check your Anthropic API key and try again.',
        )
      } else if (response.status === 403) {
        throw new Error(
          'API key does not have permission to access models. Please check your API key permissions.',
        )
      } else if (response.status === 429) {
        throw new Error(
          'Too many requests. Please wait a moment and try again.',
        )
      } else if (response.status >= 500) {
        throw new Error(
          'Anthropic service is temporarily unavailable. Please try again later.',
        )
      } else {
        throw new Error(
          `Unable to connect to Anthropic API (${response.status}). Please check your internet connection and API key.`,
        )
      }
    }

    const data = await response.json()
    return data.data || []
  } catch (error) {
    if (
      (error instanceof Error && error.message.includes('API key')) ||
      (error instanceof Error && error.message.includes('Anthropic'))
    ) {
      throw error
    }

    logError(error)
    debugLogger.warn('ANTHROPIC_MODELS_FETCH_FAILED', {
      error: error instanceof Error ? error.message : String(error),
    })
    throw new Error(
      'Unable to connect to Anthropic API. Please check your internet connection and try again.',
    )
  }
}

export async function verifyApiKey(
  apiKey: string,
  baseURL?: string,
  provider?: string,
): Promise<boolean> {
  if (!apiKey) {
    return false
  }

  if (provider && provider !== 'anthropic') {
    try {
      const headers: Record<string, string> = {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      }

      if (!baseURL) {
        debugLogger.warn('API_VERIFICATION_MISSING_BASE_URL', { provider })
        return false
      }

      const modelsURL = `${baseURL.replace(/\/+$/, '')}/models`

      const response = await fetch(modelsURL, {
        method: 'GET',
        headers,
      })

      return response.ok
    } catch (error) {
      logError(error)
      debugLogger.warn('API_VERIFICATION_FAILED', {
        provider,
        error: error instanceof Error ? error.message : String(error),
      })
      return false
    }
  }

  const clientConfig: any = {
    apiKey,
    dangerouslyAllowBrowser: true,
    maxRetries: 3,
    defaultHeaders: {
      'User-Agent': USER_AGENT,
    },
  }

  if (baseURL && (provider === 'anthropic' || provider === 'minimax-coding')) {
    clientConfig.baseURL = baseURL
  }

  const anthropic = new Anthropic(clientConfig)

  try {
    await withRetry(
      async () => {
        const model = 'claude-sonnet-4-20250514'
        const messages: MessageParam[] = [{ role: 'user', content: 'test' }]
        await anthropic.messages.create({
          model,
          max_tokens: 1000,
          messages,
          temperature: 0,
        })
        return true
      },
      { maxRetries: 2 },
    )
    return true
  } catch (error) {
    logError(error)
    if (
      error instanceof Error &&
      error.message.includes(
        '{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}',
      )
    ) {
      return false
    }
    throw error
  }
}

function convertAnthropicMessagesToOpenAIMessages(
  messages: (UserMessage | AssistantMessage)[],
): (
  | OpenAI.ChatCompletionMessageParam
  | OpenAI.ChatCompletionToolMessageParam
)[] {
  return convertAnthropicMessagesToOpenAIMessagesUtil(messages as any)
}

function messageReducer(
  previous: OpenAI.ChatCompletionMessage,
  item: OpenAI.ChatCompletionChunk,
): OpenAI.ChatCompletionMessage {
  const reduce = (acc: any, delta: OpenAI.ChatCompletionChunk.Choice.Delta) => {
    acc = { ...acc }
    for (const [key, value] of Object.entries(delta)) {
      if (acc[key] === undefined || acc[key] === null) {
        acc[key] = value
        if (Array.isArray(acc[key])) {
          for (const arr of acc[key]) {
            delete arr.index
          }
        }
      } else if (typeof acc[key] === 'string' && typeof value === 'string') {
        acc[key] += value
      } else if (typeof acc[key] === 'number' && typeof value === 'number') {
        acc[key] = value
      } else if (Array.isArray(acc[key]) && Array.isArray(value)) {
        const accArray = acc[key]
        for (let i = 0; i < value.length; i++) {
          const { index, ...chunkTool } = value[i]
          if (index - accArray.length > 1) {
            throw new Error(
              `Error: An array has an empty value when tool_calls are constructed. tool_calls: ${accArray}; tool: ${value}`,
            )
          }
          accArray[index] = reduce(accArray[index], chunkTool)
        }
      } else if (typeof acc[key] === 'object' && typeof value === 'object') {
        acc[key] = reduce(acc[key], value)
      }
    }
    return acc
  }

  const choice = item.choices?.[0]
  if (!choice) {
    return previous
  }
  return reduce(previous, choice.delta) as OpenAI.ChatCompletionMessage
}
async function handleMessageStream(
  stream: ChatCompletionStream,
  signal?: AbortSignal,
): Promise<OpenAI.ChatCompletion> {
  const streamStartTime = Date.now()
  let ttftMs: number | undefined
  let chunkCount = 0
  let errorCount = 0

  debugLogger.api('OPENAI_STREAM_START', {
    streamStartTime: String(streamStartTime),
  })

  let message = {} as OpenAI.ChatCompletionMessage

  let id, model, created, object, usage
  try {
    for await (const chunk of stream) {
      if (signal?.aborted) {
        debugLogger.flow('OPENAI_STREAM_ABORTED', {
          chunkCount,
          timestamp: Date.now(),
        })
        throw new Error('Request was cancelled')
      }

      chunkCount++

      try {
        if (!id) {
          id = chunk.id
          debugLogger.api('OPENAI_STREAM_ID_RECEIVED', {
            id,
            chunkNumber: String(chunkCount),
          })
        }
        if (!model) {
          model = chunk.model
          debugLogger.api('OPENAI_STREAM_MODEL_RECEIVED', {
            model,
            chunkNumber: String(chunkCount),
          })
        }
        if (!created) {
          created = chunk.created
        }
        if (!object) {
          object = chunk.object
        }
        if (!usage) {
          usage = chunk.usage
        }

        message = messageReducer(message, chunk)

        if (chunk?.choices?.[0]?.delta?.content) {
          if (!ttftMs) {
            ttftMs = Date.now() - streamStartTime
            debugLogger.api('OPENAI_STREAM_FIRST_TOKEN', {
              ttftMs: String(ttftMs),
              chunkNumber: String(chunkCount),
            })
          }
        }
      } catch (chunkError) {
        errorCount++
        debugLogger.error('OPENAI_STREAM_CHUNK_ERROR', {
          chunkNumber: String(chunkCount),
          errorMessage:
            chunkError instanceof Error
              ? chunkError.message
              : String(chunkError),
          errorType:
            chunkError instanceof Error
              ? chunkError.constructor.name
              : typeof chunkError,
        })
      }
    }

    debugLogger.api('OPENAI_STREAM_COMPLETE', {
      totalChunks: String(chunkCount),
      errorCount: String(errorCount),
      totalDuration: String(Date.now() - streamStartTime),
      ttftMs: String(ttftMs || 0),
      finalMessageId: id || 'undefined',
    })
  } catch (streamError) {
    debugLogger.error('OPENAI_STREAM_FATAL_ERROR', {
      totalChunks: String(chunkCount),
      errorCount: String(errorCount),
      errorMessage:
        streamError instanceof Error
          ? streamError.message
          : String(streamError),
      errorType:
        streamError instanceof Error
          ? streamError.constructor.name
          : typeof streamError,
    })
    throw streamError
  }
  return {
    id,
    created,
    model,
    object,
    choices: [
      {
        index: 0,
        message,
        finish_reason: 'stop',
        logprobs: undefined,
      },
    ],
    usage,
  }
}

function convertOpenAIResponseToAnthropic(
  response: OpenAI.ChatCompletion,
  tools?: Tool[],
) {
  let contentBlocks: ContentBlock[] = []
  const message = response.choices?.[0]?.message
  if (!message) {
    return {
      role: 'assistant',
      content: [],
      stop_reason: response.choices?.[0]?.finish_reason,
      type: 'message',
      usage: response.usage,
    }
  }

  if (message?.tool_calls) {
    for (const toolCall of message.tool_calls) {
      const tool = toolCall.function
      const toolName = tool?.name
      let toolArgs = {}
      try {
        toolArgs = tool?.arguments ? JSON.parse(tool.arguments) : {}
      } catch (e) {
      }

      contentBlocks.push({
        type: 'tool_use',
        input: toolArgs,
        name: toolName,
        id: toolCall.id?.length > 0 ? toolCall.id : nanoid(),
      })
    }
  }

  if ((message as any).reasoning) {
    contentBlocks.push({
      type: 'thinking',
      thinking: (message as any).reasoning,
      signature: '',
    })
  }

  if ((message as any).reasoning_content) {
    contentBlocks.push({
      type: 'thinking',
      thinking: (message as any).reasoning_content,
      signature: '',
    })
  }

  if (message.content) {
    contentBlocks.push({
      type: 'text',
      text: message?.content,
      citations: [],
    })
  }

  const finalMessage = {
    role: 'assistant',
    content: contentBlocks,
    stop_reason: response.choices?.[0]?.finish_reason,
    type: 'message',
    usage: response.usage,
  }

  return finalMessage
}

let anthropicClient: Anthropic | AnthropicBedrock | AnthropicVertex | null =
  null

export function getAnthropicClient(
  model?: string,
): Anthropic | AnthropicBedrock | AnthropicVertex {
  const config = getGlobalConfig()
  const provider = config.primaryProvider

  if (anthropicClient && provider) {
    anthropicClient = null
  }

  if (anthropicClient) {
    return anthropicClient
  }

  const region = getVertexRegionForModel(model)

  const modelManager = getModelManager()
  const modelProfile = modelManager.getModel('main')

  const defaultHeaders: { [key: string]: string } = {
    'x-app': 'cli',
    'User-Agent': USER_AGENT,
  }

  if (process.env.ANTHROPIC_AUTH_TOKEN) {
    defaultHeaders['Authorization'] =
      `Bearer ${process.env.ANTHROPIC_AUTH_TOKEN}`
  }

  const ARGS = {
    defaultHeaders,
    maxRetries: 0,
    timeout: parseInt(process.env.API_TIMEOUT_MS || String(60 * 1000), 10),
  }
  if (USE_BEDROCK) {
    const client = new AnthropicBedrock(ARGS)
    anthropicClient = client
    return client
  }
  if (USE_VERTEX) {
    const vertexArgs = {
      ...ARGS,
      region: region || process.env.CLOUD_ML_REGION || 'us-east5',
    }
    const client = new AnthropicVertex(vertexArgs)
    anthropicClient = client
    return client
  }

  let apiKey: string
  let baseURL: string | undefined

  if (modelProfile) {
    apiKey = modelProfile.apiKey || ''
    baseURL = modelProfile.baseURL
  } else {
    apiKey = getAnthropicApiKey()
    baseURL = undefined
  }

  if (process.env.USER_TYPE === 'ant' && !apiKey && provider === 'anthropic') {
    console.error(
      chalk.red(
        '[ANT-ONLY] Missing API key. Configure an API key in your model profile or environment variables.',
      ),
    )
  }

  const clientConfig = {
    apiKey,
    dangerouslyAllowBrowser: true,
    ...ARGS,
    ...(baseURL && { baseURL }),
  }

  anthropicClient = new Anthropic(clientConfig)
  return anthropicClient
}

export function resetAnthropicClient(): void {
  anthropicClient = null
}


function applyCacheControlWithLimits(
  systemBlocks: TextBlockParam[],
  messageParams: MessageParam[],
): { systemBlocks: TextBlockParam[]; messageParams: MessageParam[] } {
  if (!PROMPT_CACHING_ENABLED) {
    return { systemBlocks, messageParams }
  }

  const maxCacheBlocks = 4
  let usedCacheBlocks = 0

  const processedSystemBlocks = systemBlocks.map((block, index) => {
    if (usedCacheBlocks < maxCacheBlocks && block.text.length > 1000) {
      usedCacheBlocks++
      return {
        ...block,
        cache_control: { type: 'ephemeral' as const },
      }
    }
    const { cache_control, ...blockWithoutCache } = block
    return blockWithoutCache
  })

  const processedMessageParams = messageParams.map((message, messageIndex) => {
    if (Array.isArray(message.content)) {
      const processedContent = message.content.map(
        (contentBlock, blockIndex) => {
          const shouldCache =
            usedCacheBlocks < maxCacheBlocks &&
            contentBlock.type === 'text' &&
            typeof contentBlock.text === 'string' &&
            (contentBlock.text.length > 2000 ||
              (messageIndex === messageParams.length - 1 &&
                blockIndex === message.content.length - 1 &&
                contentBlock.text.length > 500))

          if (shouldCache) {
            usedCacheBlocks++
            return {
              ...contentBlock,
              cache_control: { type: 'ephemeral' as const },
            }
          }

          const { cache_control, ...blockWithoutCache } = contentBlock as any
          return blockWithoutCache
        },
      )

      return {
        ...message,
        content: processedContent,
      }
    }

    return message
  })

  return {
    systemBlocks: processedSystemBlocks,
    messageParams: processedMessageParams,
  }
}

export function userMessageToMessageParam(
  message: UserMessage,
  addCache = false,
): MessageParam {
  if (addCache) {
    if (typeof message.message.content === 'string') {
      return {
        role: 'user',
        content: [
          {
            type: 'text',
            text: message.message.content,
          },
        ],
      }
    } else {
      return {
        role: 'user',
        content: message.message.content.map(_ => ({ ..._ })),
      }
    }
  }
  return {
    role: 'user',
    content: message.message.content,
  }
}

export function assistantMessageToMessageParam(
  message: AssistantMessage,
  addCache = false,
): MessageParam {
  if (addCache) {
    if (typeof message.message.content === 'string') {
      return {
        role: 'assistant',
        content: [
          {
            type: 'text',
            text: message.message.content,
          },
        ],
      }
    } else {
      return {
        role: 'assistant',
        content: message.message.content.map(_ => ({ ..._ })),
      }
    }
  }
  return {
    role: 'assistant',
    content: message.message.content,
  }
}

function splitSysPromptPrefix(systemPrompt: string[]): string[] {

  const systemPromptFirstBlock = systemPrompt[0] || ''
  const systemPromptRest = systemPrompt.slice(1)
  return [systemPromptFirstBlock, systemPromptRest.join('\n')].filter(Boolean)
}

export async function queryLLM(
  messages: (UserMessage | AssistantMessage)[],
  systemPrompt: string[],
  maxThinkingTokens: number,
  tools: Tool[],
  signal: AbortSignal,
  options: {
    safeMode: boolean
    model: string | import('@utils/config').ModelPointerType
    prependCLISysprompt: boolean
    temperature?: number
    maxTokens?: number
    stopSequences?: string[]
    toolUseContext?: ToolUseContext
    __testModelManager?: any
    __testQueryLLMWithPromptCaching?: any
  },
): Promise<AssistantMessage> {
  const modelManager = options.__testModelManager ?? getModelManager()
  const modelResolution = modelManager.resolveModelWithInfo(options.model)

  if (!modelResolution.success || !modelResolution.profile) {
    const fallbackProfile = modelManager.resolveModel(options.model)
    if (!fallbackProfile) {
      throw new Error(
        modelResolution.error || `Failed to resolve model: ${options.model}`,
      )
    }

    debugLogger.warn('MODEL_RESOLUTION_FALLBACK', {
      inputParam: options.model,
      error: modelResolution.error,
      fallbackModelName: fallbackProfile.modelName,
      fallbackProvider: fallbackProfile.provider,
      requestId: getCurrentRequest()?.id,
    })

    modelResolution.success = true
    modelResolution.profile = fallbackProfile
  }

  const modelProfile = modelResolution.profile
  const resolvedModel = modelProfile.modelName

  const toolUseContext = options.toolUseContext
  if (toolUseContext && !toolUseContext.responseState) {
    const conversationId = getConversationId(
      toolUseContext.agentId,
      toolUseContext.messageId,
    )
    const previousResponseId =
      responseStateManager.getPreviousResponseId(conversationId)

    toolUseContext.responseState = {
      previousResponseId,
      conversationId,
    }
  }

  debugLogger.api('MODEL_RESOLVED', {
    inputParam: options.model,
    resolvedModelName: resolvedModel,
    provider: modelProfile.provider,
    isPointer: ['main', 'task', 'compact', 'quick'].includes(options.model),
    hasResponseState: !!toolUseContext?.responseState,
    conversationId: toolUseContext?.responseState?.conversationId,
    requestId: getCurrentRequest()?.id,
  })

  const currentRequest = getCurrentRequest()
  debugLogger.api('LLM_REQUEST_START', {
    messageCount: messages.length,
    systemPromptLength: systemPrompt.join(' ').length,
    toolCount: tools.length,
    model: resolvedModel,
    originalModelParam: options.model,
    requestId: getCurrentRequest()?.id,
  })

  markPhase('LLM_CALL')

  try {
    const queryFn =
      options.__testQueryLLMWithPromptCaching ?? queryLLMWithPromptCaching
    const cleanOptions: any = { ...options }
    delete cleanOptions.__testModelManager
    delete cleanOptions.__testQueryLLMWithPromptCaching

    const runQuery = () =>
      queryFn(
        messages,
        systemPrompt,
        maxThinkingTokens,
        tools,
        signal,
        {
          ...cleanOptions,
          model: resolvedModel,
          modelProfile,
          toolUseContext,
        },
      )

    const result = options.__testQueryLLMWithPromptCaching
      ? await runQuery()
      : await withVCR(messages, runQuery)

    debugLogger.api('LLM_REQUEST_SUCCESS', {
      costUSD: result.costUSD,
      durationMs: result.durationMs,
      responseLength: result.message.content?.length || 0,
      requestId: getCurrentRequest()?.id,
    })

    if (toolUseContext?.responseState?.conversationId && result.responseId) {
      responseStateManager.setPreviousResponseId(
        toolUseContext.responseState.conversationId,
        result.responseId,
      )

      debugLogger.api('RESPONSE_STATE_UPDATED', {
        conversationId: toolUseContext.responseState.conversationId,
        responseId: result.responseId,
        requestId: getCurrentRequest()?.id,
      })
    }

    return result
  } catch (error) {
    logErrorWithDiagnosis(
      error,
      {
        messageCount: messages.length,
        systemPromptLength: systemPrompt.join(' ').length,
        model: options.model,
        toolCount: tools.length,
        phase: 'LLM_CALL',
      },
      currentRequest?.id,
    )

    throw error
  }
}

export { formatSystemPromptWithContext } from '@services/systemPrompt'

async function queryLLMWithPromptCaching(
  messages: (UserMessage | AssistantMessage)[],
  systemPrompt: string[],
  maxThinkingTokens: number,
  tools: Tool[],
  signal: AbortSignal,
  options: {
    safeMode: boolean
    model: string
    prependCLISysprompt: boolean
    temperature?: number
    maxTokens?: number
    stopSequences?: string[]
    modelProfile?: ModelProfile | null
    toolUseContext?: ToolUseContext
  },
): Promise<AssistantMessage> {
  const config = getGlobalConfig()
  const modelManager = getModelManager()
  const toolUseContext = options.toolUseContext

  const modelProfile = options.modelProfile || modelManager.getModel('main')
  let provider: string

  if (modelProfile) {
    provider = modelProfile.provider || config.primaryProvider || 'anthropic'
  } else {
    provider = config.primaryProvider || 'anthropic'
  }

  if (
    provider === 'anthropic' ||
    provider === 'bigdream' ||
    provider === 'opendev' ||
    provider === 'minimax-coding'
  ) {
    return queryAnthropicNative(
      messages,
      systemPrompt,
      maxThinkingTokens,
      tools,
      signal,
      { ...options, modelProfile, toolUseContext },
    )
  }

  return queryOpenAI(messages, systemPrompt, maxThinkingTokens, tools, signal, {
    ...options,
    modelProfile,
    toolUseContext,
  })
}

async function queryAnthropicNative(
  messages: (UserMessage | AssistantMessage)[],
  systemPrompt: string[],
  maxThinkingTokens: number,
  tools: Tool[],
  signal: AbortSignal,
  options?: {
    safeMode: boolean
    model: string
    prependCLISysprompt: boolean
    temperature?: number
    maxTokens?: number
    stopSequences?: string[]
    modelProfile?: ModelProfile | null
    toolUseContext?: ToolUseContext
  },
): Promise<AssistantMessage> {
  const config = getGlobalConfig()
  const modelManager = getModelManager()
  const toolUseContext = options?.toolUseContext

  const modelProfile = options?.modelProfile || modelManager.getModel('main')
  let anthropic: Anthropic | AnthropicBedrock | AnthropicVertex
  let model: string
  let provider: string

  debugLogger.api('MODEL_CONFIG_ANTHROPIC', {
    modelProfileFound: !!modelProfile,
    modelProfileId: modelProfile?.modelName,
    modelProfileName: modelProfile?.name,
    modelProfileModelName: modelProfile?.modelName,
    modelProfileProvider: modelProfile?.provider,
    modelProfileBaseURL: modelProfile?.baseURL,
    modelProfileApiKeyExists: !!modelProfile?.apiKey,
    optionsModel: options?.model,
    requestId: getCurrentRequest()?.id,
  })

  if (modelProfile) {
    model = modelProfile.modelName
    provider = modelProfile.provider || config.primaryProvider || 'anthropic'

    if (
      modelProfile.provider === 'anthropic' ||
      modelProfile.provider === 'minimax-coding'
    ) {
      const clientConfig: any = {
        apiKey: modelProfile.apiKey,
        dangerouslyAllowBrowser: true,
        maxRetries: 0,
        timeout: parseInt(process.env.API_TIMEOUT_MS || String(60 * 1000), 10),
        defaultHeaders: {
          'x-app': 'cli',
          'User-Agent': USER_AGENT,
        },
      }

      if (modelProfile.baseURL) {
        clientConfig.baseURL = modelProfile.baseURL
      }

      anthropic = new Anthropic(clientConfig)
    } else {
      anthropic = getAnthropicClient(model)
    }
  } else {
    const errorDetails = {
      modelProfileExists: !!modelProfile,
      modelProfileModelName: modelProfile?.modelName,
      requestedModel: options?.model,
      requestId: getCurrentRequest()?.id,
    }
    debugLogger.error('ANTHROPIC_FALLBACK_ERROR', errorDetails)
    throw new Error(
      `No valid ModelProfile available for Anthropic provider. Please configure model through /model command. Debug: ${JSON.stringify(errorDetails)}`,
    )
  }

  if (options?.prependCLISysprompt) {
    const [firstSyspromptBlock] = splitSysPromptPrefix(systemPrompt)

    systemPrompt = [getCLISyspromptPrefix(), ...systemPrompt]
  }

  const system: TextBlockParam[] = splitSysPromptPrefix(systemPrompt).map(
    _ => ({
      text: _,
      type: 'text',
    }),
  )

  const toolSchemas = await Promise.all(
    tools.map(
      async tool =>
        ({
          name: tool.name,
          description: getToolDescription(tool),
          input_schema:
            'inputJSONSchema' in tool && tool.inputJSONSchema
              ? tool.inputJSONSchema
              : (zodToJsonSchema(tool.inputSchema as any) as any),
        }) as unknown as Anthropic.Beta.Messages.BetaTool,
    ),
  )

  const anthropicMessages = addCacheBreakpoints(messages)

  const { systemBlocks: processedSystem, messageParams: processedMessages } =
    applyCacheControlWithLimits(system, anthropicMessages)
  const startIncludingRetries = Date.now()

    logSystemPromptConstruction({
      basePrompt: systemPrompt.join('\n'),
      kodeContext: generateKodeContext() || '',
      reminders: [],
      finalPrompt: systemPrompt.join('\n'),
    })

  let start = Date.now()
  let attemptNumber = 0
  let response

  try {
    response = await withRetry(
      async attempt => {
        attemptNumber = attempt
        start = Date.now()

        const params: Anthropic.Beta.Messages.MessageCreateParams = {
          model,
          max_tokens:
            options?.maxTokens ?? getMaxTokensFromProfile(modelProfile),
          messages: processedMessages,
          system: processedSystem,
          tools: toolSchemas.length > 0 ? toolSchemas : undefined,
          tool_choice: toolSchemas.length > 0 ? { type: 'auto' } : undefined,
          ...(options?.temperature !== undefined
            ? { temperature: options.temperature }
            : {}),
          ...(options?.stopSequences && options.stopSequences.length > 0
            ? { stop_sequences: options.stopSequences }
            : {}),
        }

        if (maxThinkingTokens > 0) {
          ;(params as any).extra_headers = {
            'anthropic-beta': 'max-tokens-3-5-sonnet-2024-07-15',
          }
          ;(params as any).thinking = { max_tokens: maxThinkingTokens }
        }

        debugLogger.api('ANTHROPIC_API_CALL_START_STREAMING', {
          endpoint: modelProfile?.baseURL || 'DEFAULT_ANTHROPIC',
          model,
          provider,
          apiKeyConfigured: !!modelProfile?.apiKey,
          apiKeyPrefix: modelProfile?.apiKey
            ? modelProfile.apiKey.substring(0, 8)
            : null,
          maxTokens: params.max_tokens,
          temperature: options?.temperature ?? MAIN_QUERY_TEMPERATURE,
          params: params,
          messageCount: params.messages?.length || 0,
          streamMode: true,
          toolsCount: toolSchemas.length,
          thinkingTokens: maxThinkingTokens,
          timestamp: new Date().toISOString(),
          modelProfileId: modelProfile?.modelName,
          modelProfileName: modelProfile?.name,
        })

        if (config.stream) {
          const stream = await anthropic.beta.messages.create(
            {
              ...params,
              stream: true,
            },
            {
              signal: signal,
            },
          )

          let finalResponse: any | null = null
          let messageStartEvent: any = null
          const contentBlocks: any[] = []
          const inputJSONBuffers = new Map<number, string>()
          let usage: any = null
          let stopReason: string | null = null
          let stopSequence: string | null = null
          let hasMarkedStreaming = false

          for await (const event of stream) {
            if (signal.aborted) {
              debugLogger.flow('STREAM_ABORTED', {
                eventType: event.type,
                timestamp: Date.now(),
              })
              throw new Error('Request was cancelled')
            }

            switch (event.type) {
              case 'message_start':
                messageStartEvent = event
                finalResponse = {
                  ...event.message,
                  content: [],
                }
                break

              case 'content_block_start':
                contentBlocks[event.index] = { ...event.content_block }
                const contentBlockType = (event.content_block as any).type
                if (
                  contentBlockType === 'tool_use' ||
                  contentBlockType === 'server_tool_use' ||
                  contentBlockType === 'mcp_tool_use'
                ) {
                  setRequestStatus({
                    kind: 'tool',
                    detail: (event.content_block as any).name,
                  })
                  inputJSONBuffers.set(event.index, '')
                }
                break

              case 'content_block_delta':
                const blockIndex = event.index

                if (!contentBlocks[blockIndex]) {
                  contentBlocks[blockIndex] = {
                    type:
                      event.delta.type === 'text_delta' ? 'text' : 'tool_use',
                    text: event.delta.type === 'text_delta' ? '' : undefined,
                  }
                  if (event.delta.type === 'input_json_delta') {
                    inputJSONBuffers.set(blockIndex, '')
                  }
                }

                if (event.delta.type === 'text_delta') {
                  if (!hasMarkedStreaming) {
                    setRequestStatus({ kind: 'streaming' })
                    hasMarkedStreaming = true
                  }
                  contentBlocks[blockIndex].text += event.delta.text
                } else if (event.delta.type === 'input_json_delta') {
                  const currentBuffer = inputJSONBuffers.get(blockIndex) || ''
                  const nextBuffer = currentBuffer + event.delta.partial_json
                  inputJSONBuffers.set(blockIndex, nextBuffer)

                  const trimmed = nextBuffer.trim()
                  if (trimmed.length === 0) {
                    contentBlocks[blockIndex].input = {}
                    break
                  }

                  contentBlocks[blockIndex].input =
                    parseToolUsePartialJsonOrThrow(nextBuffer) ?? {}
                }
                break

              case 'message_delta':
                if (event.delta.stop_reason)
                  stopReason = event.delta.stop_reason
                if (event.delta.stop_sequence)
                  stopSequence = event.delta.stop_sequence
                if (event.usage) usage = { ...usage, ...event.usage }
                break

              case 'content_block_stop':
                const stopIndex = event.index
                const block = contentBlocks[stopIndex]

                if (
                  (block?.type === 'tool_use' ||
                    block?.type === 'server_tool_use' ||
                    block?.type === 'mcp_tool_use') &&
                  inputJSONBuffers.has(stopIndex)
                ) {
                  const jsonStr = inputJSONBuffers.get(stopIndex) ?? ''
                  if (block.input === undefined) {
                    const trimmed = jsonStr.trim()
                    if (trimmed.length === 0) {
                      block.input = {}
                    } else {
                      block.input =
                        parseToolUsePartialJsonOrThrow(jsonStr) ?? {}
                    }
                  }

                  inputJSONBuffers.delete(stopIndex)
                }
                break

              case 'message_stop':
                inputJSONBuffers.clear()
                break
            }

            if (event.type === 'message_stop') {
              break
            }
          }

          if (!finalResponse || !messageStartEvent) {
            throw new Error('Stream ended without proper message structure')
          }

          finalResponse = {
            ...messageStartEvent.message,
            content: contentBlocks.filter(Boolean),
            stop_reason: stopReason,
            stop_sequence: stopSequence,
            usage: {
              ...messageStartEvent.message.usage,
              ...usage,
            },
          }

          return finalResponse
        } else {
          debugLogger.api('ANTHROPIC_API_CALL_START_NON_STREAMING', {
            endpoint: modelProfile?.baseURL || 'DEFAULT_ANTHROPIC',
            model,
            provider,
            apiKeyConfigured: !!modelProfile?.apiKey,
            apiKeyPrefix: modelProfile?.apiKey
              ? modelProfile.apiKey.substring(0, 8)
              : null,
            maxTokens: params.max_tokens,
            temperature: options?.temperature ?? MAIN_QUERY_TEMPERATURE,
            messageCount: params.messages?.length || 0,
            streamMode: false,
            toolsCount: toolSchemas.length,
            thinkingTokens: maxThinkingTokens,
            timestamp: new Date().toISOString(),
            modelProfileId: modelProfile?.modelName,
            modelProfileName: modelProfile?.name,
          })

          return await anthropic.beta.messages.create(params, {
            signal: signal,
          })
        }
      },
      { signal },
    )

    debugLogger.api('ANTHROPIC_API_CALL_SUCCESS', {
      content: response.content,
    })

    const ttftMs = start - Date.now()
    const durationMs = Date.now() - startIncludingRetries

    const content = response.content.map((block: ContentBlock) => {
      if (block.type === 'text') {
        return {
          type: 'text' as const,
          text: block.text,
        }
      } else if (block.type === 'tool_use') {
        return {
          type: 'tool_use' as const,
          id: block.id,
          name: block.name,
          input: block.input,
        }
      }
      return block
    })

    const assistantMessage: AssistantMessage = {
      message: {
        id: response.id,
        content,
        model: response.model,
        role: 'assistant',
        stop_reason: response.stop_reason,
        stop_sequence: response.stop_sequence,
        type: 'message',
        usage: response.usage,
      },
      type: 'assistant',
      uuid: nanoid() as UUID,
      durationMs,
      costUSD: 0,
    }

    const systemMessages = system.map(block => ({
      role: 'system',
      content: block.text,
    }))

    logLLMInteraction({
      systemPrompt: systemPrompt.join('\n'),
      messages: [...systemMessages, ...anthropicMessages],
      response: response,
      usage: response.usage
        ? {
            inputTokens: response.usage.input_tokens,
            outputTokens: response.usage.output_tokens,
          }
        : undefined,
      timing: {
        start: start,
        end: Date.now(),
      },
      apiFormat: 'anthropic',
    })

    const inputTokens = response.usage.input_tokens
    const outputTokens = response.usage.output_tokens
    const cacheCreationInputTokens =
      response.usage.cache_creation_input_tokens ?? 0
    const cacheReadInputTokens = response.usage.cache_read_input_tokens ?? 0

    const costUSD =
      (inputTokens / 1_000_000) * getModelInputTokenCostUSD(model) +
      (outputTokens / 1_000_000) * getModelOutputTokenCostUSD(model) +
      (cacheCreationInputTokens / 1_000_000) *
        getModelInputTokenCostUSD(model) +
      (cacheReadInputTokens / 1_000_000) *
        (getModelInputTokenCostUSD(model) * 0.1)

    assistantMessage.costUSD = costUSD
    addToTotalCost(costUSD, durationMs)

    return assistantMessage
  } catch (error) {
    return getAssistantMessageFromError(error)
  }
}

function getAssistantMessageFromError(error: unknown): AssistantMessage {
  if (error instanceof Error && error.message.includes('prompt is too long')) {
    return createAssistantAPIErrorMessage(PROMPT_TOO_LONG_ERROR_MESSAGE)
  }
  if (
    error instanceof Error &&
    error.message.includes('Your credit balance is too low')
  ) {
    return createAssistantAPIErrorMessage(CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE)
  }
  if (
    error instanceof Error &&
    error.message.toLowerCase().includes('x-api-key')
  ) {
    return createAssistantAPIErrorMessage(INVALID_API_KEY_ERROR_MESSAGE)
  }
  if (error instanceof Error) {
    if (process.env.NODE_ENV === 'development') {
      debugLogger.error('ANTHROPIC_API_ERROR', {
        message: error.message,
        stack: error.stack,
      })
    }
    return createAssistantAPIErrorMessage(
      `${API_ERROR_MESSAGE_PREFIX}: ${error.message}`,
    )
  }
  return createAssistantAPIErrorMessage(API_ERROR_MESSAGE_PREFIX)
}

function addCacheBreakpoints(
  messages: (UserMessage | AssistantMessage)[],
): MessageParam[] {
  return messages.map((msg, index) => {
    return msg.type === 'user'
      ? userMessageToMessageParam(msg, index > messages.length - 3)
      : assistantMessageToMessageParam(msg, index > messages.length - 3)
  })
}

async function queryOpenAI(
  messages: (UserMessage | AssistantMessage)[],
  systemPrompt: string[],
  maxThinkingTokens: number,
  tools: Tool[],
  signal: AbortSignal,
  options?: {
    safeMode: boolean
    model: string
    prependCLISysprompt: boolean
    temperature?: number
    maxTokens?: number
    stopSequences?: string[]
    modelProfile?: ModelProfile | null
    toolUseContext?: ToolUseContext
  },
): Promise<AssistantMessage> {
  const config = getGlobalConfig()
  const modelManager = getModelManager()
  const toolUseContext = options?.toolUseContext

  const modelProfile = options?.modelProfile || modelManager.getModel('main')
  let model: string

  const currentRequest = getCurrentRequest()
  debugLogger.api('MODEL_CONFIG_OPENAI', {
    modelProfileFound: !!modelProfile,
    modelProfileId: modelProfile?.modelName,
    modelProfileName: modelProfile?.name,
    modelProfileModelName: modelProfile?.modelName,
    modelProfileProvider: modelProfile?.provider,
    modelProfileBaseURL: modelProfile?.baseURL,
    modelProfileApiKeyExists: !!modelProfile?.apiKey,
    optionsModel: options?.model,
    requestId: getCurrentRequest()?.id,
  })

  if (modelProfile) {
    model = modelProfile.modelName
  } else {
    model = options?.model || modelProfile?.modelName || ''
  }
  if (options?.prependCLISysprompt) {
    const [firstSyspromptBlock] = splitSysPromptPrefix(systemPrompt)

    systemPrompt = [getCLISyspromptPrefix() + systemPrompt]
  }

  const system: TextBlockParam[] = splitSysPromptPrefix(systemPrompt).map(
    _ => ({
      ...(PROMPT_CACHING_ENABLED
        ? { cache_control: { type: 'ephemeral' } }
        : {}),
      text: _,
      type: 'text',
    }),
  )

  const toolSchemas = await Promise.all(
    tools.map(
      async _ =>
        ({
          type: 'function',
          function: {
            name: _.name,
            description: await _.prompt({
              safeMode: options?.safeMode,
            }),
            parameters:
              'inputJSONSchema' in _ && _.inputJSONSchema
                ? _.inputJSONSchema
                : (zodToJsonSchema(_.inputSchema as any) as any),
          },
        }) as OpenAI.ChatCompletionTool,
    ),
  )

  const openaiSystem = system.map(
    s =>
      ({
        role: 'system',
        content: s.text,
      }) as OpenAI.ChatCompletionMessageParam,
  )

  const openaiMessages = convertAnthropicMessagesToOpenAIMessages(messages)

  logSystemPromptConstruction({
    basePrompt: systemPrompt.join('\n'),
    kodeContext: generateKodeContext() || '',
    reminders: [],
    finalPrompt: systemPrompt.join('\n'),
  })

  let start = Date.now()

  type AdapterExecutionContext = {
    adapter: ReturnType<typeof ModelAdapterFactory.createAdapter>
    request: any
    shouldUseResponses: boolean
  }

  type QueryResult = {
    assistantMessage: AssistantMessage
    rawResponse?: any
    apiFormat: 'openai'
  }

  let adapterContext: AdapterExecutionContext | null = null

  if (modelProfile && modelProfile.modelName) {
    debugLogger.api('CHECKING_ADAPTER_SYSTEM', {
      modelProfileName: modelProfile.modelName,
      modelName: modelProfile.modelName,
      provider: modelProfile.provider,
      requestId: getCurrentRequest()?.id,
    })

    const USE_NEW_ADAPTER_SYSTEM = process.env.USE_NEW_ADAPTERS !== 'false'

    if (USE_NEW_ADAPTER_SYSTEM) {
      const shouldUseResponses =
        ModelAdapterFactory.shouldUseResponsesAPI(modelProfile)

      if (shouldUseResponses) {
        const adapter = ModelAdapterFactory.createAdapter(modelProfile)
        const reasoningEffort = await getReasoningEffort(modelProfile, messages)

        let verbosity: 'low' | 'medium' | 'high' = 'medium'
        const modelNameLower = modelProfile.modelName.toLowerCase()
        if (modelNameLower.includes('high')) {
          verbosity = 'high'
        } else if (modelNameLower.includes('low')) {
          verbosity = 'low'
        }

        const unifiedParams: UnifiedRequestParams = {
          messages: openaiMessages,
          systemPrompt: openaiSystem.map(s => s.content as string),
          tools,
          maxTokens:
            options?.maxTokens ?? getMaxTokensFromProfile(modelProfile),
          stream: config.stream,
          reasoningEffort: reasoningEffort as any,
          temperature:
            options?.temperature ??
            (isGPT5Model(model) ? 1 : MAIN_QUERY_TEMPERATURE),
          previousResponseId: toolUseContext?.responseState?.previousResponseId,
          verbosity,
          ...(options?.stopSequences && options.stopSequences.length > 0
            ? { stopSequences: options.stopSequences }
            : {}),
        }

        adapterContext = {
          adapter,
          request: adapter.createRequest(unifiedParams),
          shouldUseResponses: true,
        }
      }
    }
  }

  let queryResult: QueryResult
  let startIncludingRetries = Date.now()

  try {
    queryResult = await withRetry(
      async () => {
        start = Date.now()

        if (adapterContext) {
          if (adapterContext.shouldUseResponses) {
            const { callGPT5ResponsesAPI } = await import('./openai')

            const response = await callGPT5ResponsesAPI(
              modelProfile,
              adapterContext.request,
              signal,
            )

            const unifiedResponse =
              await adapterContext.adapter.parseResponse(response)

            const assistantMessage = buildAssistantMessageFromUnifiedResponse(
              unifiedResponse,
              start,
            )
            assistantMessage.message.usage = normalizeUsage(
              assistantMessage.message.usage,
            )

            return {
              assistantMessage,
              rawResponse: unifiedResponse,
              apiFormat: 'openai',
            }
          }

          const s = await getCompletionWithProfile(
            modelProfile,
            adapterContext.request,
            0,
            10,
            signal,
          )
          let finalResponse
          if (config.stream) {
            finalResponse = await handleMessageStream(
              s as ChatCompletionStream,
              signal,
            )
          } else {
            finalResponse = s
          }

          const message = convertOpenAIResponseToAnthropic(finalResponse, tools)
          const assistantMsg: AssistantMessage = {
            type: 'assistant',
            message: message as any,
            costUSD: 0,
            durationMs: Date.now() - start,
            uuid: `${Date.now()}-${Math.random()
              .toString(36)
              .substr(2, 9)}` as any,
          }

          return {
            assistantMessage: assistantMsg,
            rawResponse: finalResponse,
            apiFormat: 'openai',
          }
        }

        const maxTokens =
          options?.maxTokens ?? getMaxTokensFromProfile(modelProfile)
        const isGPT5 = isGPT5Model(model)

        const opts: OpenAI.ChatCompletionCreateParams = {
          model,
          ...(isGPT5
            ? { max_completion_tokens: maxTokens }
            : { max_tokens: maxTokens }),
          messages: [...openaiSystem, ...openaiMessages],
          temperature:
            options?.temperature ?? (isGPT5 ? 1 : MAIN_QUERY_TEMPERATURE),
        }
        if (options?.stopSequences && options.stopSequences.length > 0) {
          ;(opts as any).stop = options.stopSequences
        }
        if (config.stream) {
          ;(opts as OpenAI.ChatCompletionCreateParams).stream = true
          opts.stream_options = {
            include_usage: true,
          }
        }

        if (toolSchemas.length > 0) {
          opts.tools = toolSchemas
          opts.tool_choice = 'auto'
        }
        const reasoningEffort = await getReasoningEffort(modelProfile, messages)
        if (reasoningEffort) {
          opts.reasoning_effort = reasoningEffort
        }

        const completionFunction = isGPT5Model(modelProfile?.modelName || '')
          ? getGPT5CompletionWithProfile
          : getCompletionWithProfile
        const s = await completionFunction(modelProfile, opts, 0, 10, signal)
        let finalResponse
        if (opts.stream) {
          finalResponse = await handleMessageStream(
            s as ChatCompletionStream,
            signal,
          )
        } else {
          finalResponse = s
        }
        const message = convertOpenAIResponseToAnthropic(finalResponse, tools)
        const assistantMsg: AssistantMessage = {
          type: 'assistant',
          message: message as any,
          costUSD: 0,
          durationMs: Date.now() - start,
          uuid: `${Date.now()}-${Math.random()
            .toString(36)
            .substr(2, 9)}` as any,
        }
        return {
          assistantMessage: assistantMsg,
          rawResponse: finalResponse,
          apiFormat: 'openai',
        }
      },
      { signal },
    )
  } catch (error) {
    logError(error)
    return getAssistantMessageFromError(error)
  }

  const durationMs = Date.now() - start
  const durationMsIncludingRetries = Date.now() - startIncludingRetries

  const assistantMessage = queryResult.assistantMessage
  assistantMessage.message.content = normalizeContentFromAPI(
    assistantMessage.message.content || [],
  )

  const normalizedUsage = normalizeUsage(assistantMessage.message.usage)
  assistantMessage.message.usage = normalizedUsage

  const inputTokens = normalizedUsage.input_tokens ?? 0
  const outputTokens = normalizedUsage.output_tokens ?? 0
  const cacheReadInputTokens = normalizedUsage.cache_read_input_tokens ?? 0
  const cacheCreationInputTokens =
    normalizedUsage.cache_creation_input_tokens ?? 0

  const costUSD =
    (inputTokens / 1_000_000) * SONNET_COST_PER_MILLION_INPUT_TOKENS +
    (outputTokens / 1_000_000) * SONNET_COST_PER_MILLION_OUTPUT_TOKENS +
    (cacheReadInputTokens / 1_000_000) *
      SONNET_COST_PER_MILLION_PROMPT_CACHE_READ_TOKENS +
    (cacheCreationInputTokens / 1_000_000) *
      SONNET_COST_PER_MILLION_PROMPT_CACHE_WRITE_TOKENS

  addToTotalCost(costUSD, durationMsIncludingRetries)

  logLLMInteraction({
    systemPrompt: systemPrompt.join('\n'),
    messages: [...openaiSystem, ...openaiMessages],
    response: assistantMessage.message || queryResult.rawResponse,
    usage: {
      inputTokens,
      outputTokens,
    },
    timing: {
      start,
      end: Date.now(),
    },
    apiFormat: queryResult.apiFormat,
  })

  assistantMessage.costUSD = costUSD
  assistantMessage.durationMs = durationMs
  assistantMessage.uuid = assistantMessage.uuid || (randomUUID() as UUID)

  return assistantMessage
}

function getMaxTokensFromProfile(modelProfile: any): number {
  return modelProfile?.maxTokens || 8000
}

function buildAssistantMessageFromUnifiedResponse(
  unifiedResponse: any,
  startTime: number,
): AssistantMessage {
  const contentBlocks = [...(unifiedResponse.content || [])]

  if (unifiedResponse.toolCalls && unifiedResponse.toolCalls.length > 0) {
    for (const toolCall of unifiedResponse.toolCalls) {
      const tool = toolCall.function
      const toolName = tool?.name
      let toolArgs = {}
      try {
        toolArgs = tool?.arguments ? JSON.parse(tool.arguments) : {}
      } catch (e) {
      }

      contentBlocks.push({
        type: 'tool_use',
        input: toolArgs,
        name: toolName,
        id: toolCall.id?.length > 0 ? toolCall.id : nanoid(),
      })
    }
  }

  return {
    type: 'assistant',
    message: {
      role: 'assistant',
      content: contentBlocks,
      usage: {
        input_tokens:
          unifiedResponse.usage?.promptTokens ??
          unifiedResponse.usage?.input_tokens ??
          0,
        output_tokens:
          unifiedResponse.usage?.completionTokens ??
          unifiedResponse.usage?.output_tokens ??
          0,
        prompt_tokens:
          unifiedResponse.usage?.promptTokens ??
          unifiedResponse.usage?.input_tokens ??
          0,
        completion_tokens:
          unifiedResponse.usage?.completionTokens ??
          unifiedResponse.usage?.output_tokens ??
          0,
        promptTokens:
          unifiedResponse.usage?.promptTokens ??
          unifiedResponse.usage?.input_tokens ??
          0,
        completionTokens:
          unifiedResponse.usage?.completionTokens ??
          unifiedResponse.usage?.output_tokens ??
          0,
        totalTokens:
          unifiedResponse.usage?.totalTokens ??
          (unifiedResponse.usage?.promptTokens ??
            unifiedResponse.usage?.input_tokens ??
            0) +
            (unifiedResponse.usage?.completionTokens ??
              unifiedResponse.usage?.output_tokens ??
              0),
      },
    },
    costUSD: 0,
    durationMs: Date.now() - startTime,
    uuid: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}` as any,
    responseId: unifiedResponse.responseId,
  }
}

function normalizeUsage(usage?: any) {
  if (!usage) {
    return {
      input_tokens: 0,
      output_tokens: 0,
      cache_read_input_tokens: 0,
      cache_creation_input_tokens: 0,
    }
  }

  const inputTokens =
    usage.input_tokens ?? usage.prompt_tokens ?? usage.inputTokens ?? 0
  const outputTokens =
    usage.output_tokens ?? usage.completion_tokens ?? usage.outputTokens ?? 0
  const cacheReadInputTokens =
    usage.cache_read_input_tokens ??
    usage.prompt_token_details?.cached_tokens ??
    usage.cacheReadInputTokens ??
    0
  const cacheCreationInputTokens =
    usage.cache_creation_input_tokens ?? usage.cacheCreatedInputTokens ?? 0

  return {
    ...usage,
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    cache_read_input_tokens: cacheReadInputTokens,
    cache_creation_input_tokens: cacheCreationInputTokens,
  }
}

function getModelInputTokenCostUSD(model: string): number {
  for (const providerModels of Object.values(models)) {
    const modelInfo = providerModels.find((m: any) => m.model === model)
    if (modelInfo) {
      return modelInfo.input_cost_per_token || 0
    }
  }
  return 0.000003
}

function getModelOutputTokenCostUSD(model: string): number {
  for (const providerModels of Object.values(models)) {
    const modelInfo = providerModels.find((m: any) => m.model === model)
    if (modelInfo) {
      return modelInfo.output_cost_per_token || 0
    }
  }
  return 0.000015
}

export async function queryModel(
  modelPointer: import('@utils/config').ModelPointerType,
  messages: (UserMessage | AssistantMessage)[],
  systemPrompt: string[] = [],
  signal?: AbortSignal,
): Promise<AssistantMessage> {
  return queryLLM(
    messages,
    systemPrompt,
    0,
    [],
    signal || new AbortController().signal,
    {
      safeMode: false,
      model: modelPointer,
      prependCLISysprompt: true,
    },
  )
}


export async function queryQuick({
  systemPrompt = [],
  userPrompt,
  assistantPrompt,
  enablePromptCaching = false,
  signal,
}: {
  systemPrompt?: string[]
  userPrompt: string
  assistantPrompt?: string
  enablePromptCaching?: boolean
  signal?: AbortSignal
}): Promise<AssistantMessage> {
  const messages = [
    {
      message: { role: 'user', content: userPrompt },
      type: 'user',
      uuid: randomUUID(),
    },
  ] as (UserMessage | AssistantMessage)[]

  return queryModel('quick', messages, systemPrompt, signal)
}
