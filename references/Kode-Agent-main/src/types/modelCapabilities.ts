export interface ModelCapabilities {
  apiArchitecture: {
    primary: 'chat_completions' | 'responses_api'
    fallback?: 'chat_completions'
  }

  parameters: {
    maxTokensField: 'max_tokens' | 'max_completion_tokens' | 'max_output_tokens'
    supportsReasoningEffort: boolean
    supportsVerbosity: boolean
    temperatureMode: 'flexible' | 'fixed_one' | 'restricted'
  }

  toolCalling: {
    mode: 'none' | 'function_calling' | 'custom_tools'
    supportsFreeform: boolean
    supportsAllowedTools: boolean
    supportsParallelCalls: boolean
  }

  stateManagement: {
    supportsResponseId: boolean
    supportsConversationChaining: boolean
    supportsPreviousResponseId: boolean
  }

  streaming: {
    supported: boolean
    includesUsage: boolean
  }
}

export interface ReasoningConfig {
  enable: boolean
  effort: 'low' | 'medium' | 'high' | 'none' | 'minimal'
  summary: 'auto' | 'concise' | 'detailed' | 'none'
}

export interface ReasoningStreamingContext {
  thinkOpen: boolean
  thinkClosed: boolean
  sawAnySummary: boolean
  pendingSummaryParagraph: boolean
  thinkingContent?: string
  currentPartIndex?: number
}

export interface UnifiedRequestParams {
  messages: any[]
  systemPrompt: string[]
  tools?: any[]
  maxTokens: number
  stream?: boolean
  previousResponseId?: string
  reasoningEffort?: 'minimal' | 'low' | 'medium' | 'high'
  reasoning?: ReasoningConfig
  verbosity?: 'low' | 'medium' | 'high'
  temperature?: number
  allowedTools?: string[]
  stopSequences?: string[]
}

export interface UnifiedResponse {
  id: string
  content: string | Array<{ type: string; text?: string; [key: string]: any }>
  toolCalls?: any[]
  usage: {
    promptTokens: number
    completionTokens: number
    reasoningTokens?: number
  }
  responseId?: string
}
