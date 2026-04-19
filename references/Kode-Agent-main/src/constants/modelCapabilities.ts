import { ModelCapabilities } from '@kode-types/modelCapabilities'

const GPT5_CAPABILITIES: ModelCapabilities = {
  apiArchitecture: {
    primary: 'responses_api',
    fallback: 'chat_completions',
  },
  parameters: {
    maxTokensField: 'max_output_tokens',
    supportsReasoningEffort: true,
    supportsVerbosity: true,
    temperatureMode: 'fixed_one',
  },
  toolCalling: {
    mode: 'custom_tools',
    supportsFreeform: true,
    supportsAllowedTools: true,
    supportsParallelCalls: true,
  },
  stateManagement: {
    supportsResponseId: true,
    supportsConversationChaining: true,
    supportsPreviousResponseId: true,
  },
  streaming: {
    supported: true,
    includesUsage: true,
  },
}

const CHAT_COMPLETIONS_CAPABILITIES: ModelCapabilities = {
  apiArchitecture: {
    primary: 'chat_completions',
  },
  parameters: {
    maxTokensField: 'max_tokens',
    supportsReasoningEffort: false,
    supportsVerbosity: false,
    temperatureMode: 'flexible',
  },
  toolCalling: {
    mode: 'function_calling',
    supportsFreeform: false,
    supportsAllowedTools: false,
    supportsParallelCalls: true,
  },
  stateManagement: {
    supportsResponseId: false,
    supportsConversationChaining: false,
    supportsPreviousResponseId: false,
  },
  streaming: {
    supported: true,
    includesUsage: true,
  },
}

export const MODEL_CAPABILITIES_REGISTRY: Record<string, ModelCapabilities> = {
  'gpt-5': GPT5_CAPABILITIES,
  'gpt-5-mini': GPT5_CAPABILITIES,
  'gpt-5-nano': GPT5_CAPABILITIES,
  'gpt-5-chat-latest': GPT5_CAPABILITIES,
  'gpt-5-codex': GPT5_CAPABILITIES,

  'gpt-4o': CHAT_COMPLETIONS_CAPABILITIES,
  'gpt-4o-mini': CHAT_COMPLETIONS_CAPABILITIES,
  'gpt-4-turbo': CHAT_COMPLETIONS_CAPABILITIES,
  'gpt-4': CHAT_COMPLETIONS_CAPABILITIES,

  'claude-3-5-sonnet-20241022': CHAT_COMPLETIONS_CAPABILITIES,
  'claude-3-5-haiku-20241022': CHAT_COMPLETIONS_CAPABILITIES,
  'claude-3-opus-20240229': CHAT_COMPLETIONS_CAPABILITIES,

  o1: {
    ...CHAT_COMPLETIONS_CAPABILITIES,
    parameters: {
      ...CHAT_COMPLETIONS_CAPABILITIES.parameters,
      maxTokensField: 'max_completion_tokens',
      temperatureMode: 'fixed_one',
    },
  },
  'o1-mini': {
    ...CHAT_COMPLETIONS_CAPABILITIES,
    parameters: {
      ...CHAT_COMPLETIONS_CAPABILITIES.parameters,
      maxTokensField: 'max_completion_tokens',
      temperatureMode: 'fixed_one',
    },
  },
  'o1-preview': {
    ...CHAT_COMPLETIONS_CAPABILITIES,
    parameters: {
      ...CHAT_COMPLETIONS_CAPABILITIES.parameters,
      maxTokensField: 'max_completion_tokens',
      temperatureMode: 'fixed_one',
    },
  },
}

export function inferModelCapabilities(
  modelName: string,
): ModelCapabilities | null {
  if (!modelName) return null

  const lowerName = modelName.toLowerCase()

  if (lowerName.includes('gpt-5') || lowerName.includes('gpt5')) {
    return GPT5_CAPABILITIES
  }

  if (lowerName.includes('gpt-6') || lowerName.includes('gpt6')) {
    return {
      ...GPT5_CAPABILITIES,
      streaming: { supported: true, includesUsage: true },
    }
  }

  if (lowerName.includes('glm-5') || lowerName.includes('glm5')) {
    return {
      ...CHAT_COMPLETIONS_CAPABILITIES,
      toolCalling: {
        ...CHAT_COMPLETIONS_CAPABILITIES.toolCalling,
        supportsAllowedTools: false,
      },
    }
  }

  if (lowerName.startsWith('o1') || lowerName.includes('o1-')) {
    return {
      ...CHAT_COMPLETIONS_CAPABILITIES,
      parameters: {
        ...CHAT_COMPLETIONS_CAPABILITIES.parameters,
        maxTokensField: 'max_completion_tokens',
        temperatureMode: 'fixed_one',
      },
    }
  }

  return null
}

const capabilityCache = new Map<string, ModelCapabilities>()

export function getModelCapabilities(modelName: string): ModelCapabilities {
  if (capabilityCache.has(modelName)) {
    return capabilityCache.get(modelName)!
  }

  if (MODEL_CAPABILITIES_REGISTRY[modelName]) {
    const capabilities = MODEL_CAPABILITIES_REGISTRY[modelName]
    capabilityCache.set(modelName, capabilities)
    return capabilities
  }

  const inferred = inferModelCapabilities(modelName)
  if (inferred) {
    capabilityCache.set(modelName, inferred)
    return inferred
  }

  const defaultCapabilities = CHAT_COMPLETIONS_CAPABILITIES
  capabilityCache.set(modelName, defaultCapabilities)
  return defaultCapabilities
}
