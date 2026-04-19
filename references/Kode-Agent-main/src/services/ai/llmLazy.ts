import type { AssistantMessage, UserMessage } from '@query'
import type { Tool, ToolUseContext } from '@tool'
import type { ModelPointerType } from '@utils/config'

export async function queryLLM(
  messages: (UserMessage | AssistantMessage)[],
  systemPrompt: string[],
  maxThinkingTokens: number,
  tools: Tool[],
  signal: AbortSignal,
  options: {
    safeMode: boolean
    model: string | ModelPointerType
    prependCLISysprompt: boolean
    temperature?: number
    toolUseContext?: ToolUseContext
    __testModelManager?: any
    __testQueryLLMWithPromptCaching?: any
  },
): Promise<AssistantMessage> {
  const { queryLLM: inner } = await import('@services/llm')
  return inner(
    messages as any,
    systemPrompt,
    maxThinkingTokens,
    tools,
    signal,
    options as any,
  )
}

export async function queryQuick(args: {
  systemPrompt?: string[]
  userPrompt: string
  assistantPrompt?: string
  enablePromptCaching?: boolean
  signal?: AbortSignal
}): Promise<AssistantMessage> {
  const { queryQuick: inner } = await import('@services/llm')
  return inner(args as any)
}

export async function verifyApiKey(
  apiKey: string,
  baseURL?: string,
  provider?: string,
): Promise<boolean> {
  const { verifyApiKey: inner } = await import('@services/llm')
  return inner(apiKey, baseURL, provider)
}

export async function fetchAnthropicModels(
  apiKey: string,
  baseURL?: string,
): Promise<any[]> {
  const { fetchAnthropicModels: inner } = await import('@services/llm')
  return inner(apiKey, baseURL)
}
