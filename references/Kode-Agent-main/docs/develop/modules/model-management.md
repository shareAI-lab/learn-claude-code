# Model Management System

Capability-driven architecture for managing multiple AI providers with intelligent adapter selection and model-specific behavior configuration.

## Overview

The Model Management System provides the foundational layer for Kode's multi-model architecture. It abstracts the complexity of different AI providers behind a unified interface while enabling intelligent model selection, cost optimization, and seamless switching between providers.

## Core Architecture

### ModelManager Class

The `ModelManager` serves as the central orchestrator for all model operations:

```typescript
export class ModelManager {
  private profiles: Map<string, ModelProfile>
  private pointers: ModelPointers
  private currentModel: ModelInfo
  private contextLimit: Map<string, number>

  constructor(config: ModelConfig) {
    this.loadProfiles(config.profiles)
    this.loadPointers(config.pointers)
    this.initializeContextLimits()
  }

  // Core operations
  resolveModel(pointer: string): ModelInfo
  switchToNextModel(reason: SwitchReason): ModelInfo
  analyzeContextCompatibility(messages: Message[]): ContextAnalysis
  addProfile(profile: ModelProfile): void
  updateProfile(id: string, updates: Partial<ModelProfile>): void
  deleteProfile(id: string): void
}
```

**Key Responsibilities:**
- **Profile Management**: Centralized storage and retrieval of model configurations
- **Intelligent Selection**: Choose optimal models based on context, cost, and requirements
- **Context Analysis**: Evaluate conversation context for model compatibility
- **Dynamic Switching**: Automatic fallback and upgrade based on conditions

## Model Configuration

### Model Profile Structure

Each model profile contains comprehensive configuration for provider integration:

```typescript
interface ModelProfile {
  id: string                    // Unique identifier
  name: string                  // Display name
  provider: ModelProvider       // Provider type
  config: {
    model: string              // API model identifier
    baseURL?: string           // Custom endpoint override
    apiKey?: string            // Provider API key
    maxTokens?: number         // Maximum output tokens
    temperature?: number       // Sampling temperature
    topP?: number             // Nucleus sampling
    topK?: number             // Top-K sampling
    stopSequences?: string[]   // Stop sequences
    systemPrompt?: string      // Default system prompt
    headers?: Record<string, string>  // Custom headers
    timeout?: number           // Request timeout
    retryConfig?: RetryConfig // Retry configuration
  }
  capabilities?: {
    supportsTools: boolean     // Tool/function calling support
    supportsVision: boolean    // Image input support
    supportsStreaming: boolean // Streaming response support
    maxContextTokens: number   // Context window size
    costPer1kTokens: {
      input: number
      output: number
    }
  }
  metadata?: {
    description?: string       // Profile description
    tags?: string[]           // Classification tags
    createdAt?: Date
    updatedAt?: Date
    usageCount?: number
  }
}
```

### Model Pointers

Model pointers enable semantic model selection for different use cases:

```typescript
interface ModelPointers {
  main: string        // Primary conversation model
  task: string        // Task execution model (fast, efficient)
  reasoning: string   // Complex reasoning model (powerful)
  quick: string       // Quick responses (ultra-fast)
  vision?: string     // Image analysis model
  code?: string       // Code-specific model
  [key: string]: string | undefined  // Custom pointers
}
```

**Usage Example:**
```typescript
// Select model for complex reasoning task
const reasoningModel = modelManager.resolveModel('reasoning')

// Select fastest model for quick response
const quickModel = modelManager.resolveModel('quick')
```

## Model Capabilities System

### Capability-Driven Architecture

The Model Management System uses a comprehensive capabilities registry to drive adapter selection and behavior:

```typescript
interface ModelCapabilities {
  apiArchitecture: {
    primary: 'responses_api' | 'chat_completions'
    fallback?: 'chat_completions'
  }
  parameters: {
    maxTokensField: string
    supportsReasoningEffort: boolean
    supportsVerbosity: boolean
    temperatureMode: 'flexible' | 'restricted' | 'fixed_one'
  }
  toolCalling: {
    mode: 'function_calling' | 'custom_tools'
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
```

### Capability Registry

Pre-defined capabilities for known models:

```typescript
export const MODEL_CAPABILITIES_REGISTRY: Record<string, ModelCapabilities> = {
  // GPT-5 series - Responses API native
  'gpt-5': GPT5_CAPABILITIES,
  'gpt-5-mini': GPT5_CAPABILITIES,

  // GPT-4 series - Chat Completions
  'gpt-4o': CHAT_COMPLETIONS_CAPABILITIES,
  'gpt-4o-mini': CHAT_COMPLETIONS_CAPABILITIES,

  // O1 series - Special reasoning models
  'o1': {
    ...CHAT_COMPLETIONS_CAPABILITIES,
    parameters: {
      ...CHAT_COMPLETIONS_CAPABILITIES.parameters,
      maxTokensField: 'max_completion_tokens',
      temperatureMode: 'fixed_one'
    }
  }
}
```

### Dynamic Capability Inference

For unregistered models, the system intelligently infers capabilities based on naming patterns:

```typescript
export function inferModelCapabilities(modelName: string): ModelCapabilities | null {
  const lowerName = modelName.toLowerCase()

  // GPT-5 series - Use Responses API
  if (lowerName.includes('gpt-5') || lowerName.includes('gpt5')) {
    return GPT5_CAPABILITIES
  }

  // O1 series - Special reasoning models
  if (lowerName.startsWith('o1') || lowerName.includes('o1-')) {
    return {
      ...CHAT_COMPLETIONS_CAPABILITIES,
      parameters: {
        ...CHAT_COMPLETIONS_CAPABILITIES.parameters,
        maxTokensField: 'max_completion_tokens',
        temperatureMode: 'fixed_one'
      }
    }
  }

  // GLM series - Chat Completions with limited tool support
  if (lowerName.includes('glm-5') || lowerName.includes('glm5')) {
    return {
      ...CHAT_COMPLETIONS_CAPABILITIES,
      toolCalling: {
        ...CHAT_COMPLETIONS_CAPABILITIES.toolCalling,
        supportsAllowedTools: false
      }
    }
  }

  return null // Use default Chat Completions
}
```

### Adapter Selection Logic

The `ModelAdapterFactory` uses capabilities to determine the appropriate adapter:

```typescript
class ModelAdapterFactory {
  static shouldUseResponsesAPI(modelProfile: ModelProfile): boolean {
    const capabilities = getModelCapabilities(modelProfile.modelName)
    return capabilities.apiArchitecture.primary === 'responses_api'
  }

  static createAdapter(modelProfile: ModelProfile): ModelAPIAdapter {
    const capabilities = getModelCapabilities(modelProfile.modelName)

    if (capabilities.apiArchitecture.primary === 'responses_api') {
      return new ResponsesAPIAdapter(capabilities, modelProfile)
    } else {
      return new ChatCompletionsAdapter(capabilities, modelProfile)
    }
  }
}
```

### Capability Caching

For performance, capabilities are cached after first lookup:

```typescript
const capabilityCache = new Map<string, ModelCapabilities>()

export function getModelCapabilities(modelName: string): ModelCapabilities {
  // Check cache first
  if (capabilityCache.has(modelName)) {
    return capabilityCache.get(modelName)!
  }

  // Look up in registry
  if (MODEL_CAPABILITIES_REGISTRY[modelName]) {
    const capabilities = MODEL_CAPABILITIES_REGISTRY[modelName]
    capabilityCache.set(modelName, capabilities)
    return capabilities
  }

  // Try to infer
  const inferred = inferModelCapabilities(modelName)
  if (inferred) {
    capabilityCache.set(modelName, inferred)
    return inferred
  }

  // Default to Chat Completions
  const defaultCapabilities = CHAT_COMPLETIONS_CAPABILITIES
  capabilityCache.set(modelName, defaultCapabilities)
  return defaultCapabilities
}
```

## Model Selection Logic

### Intelligent Model Selection

The system uses a sophisticated scoring algorithm to select the optimal model:

```typescript
class ModelSelector {
  selectModel(context: SelectionContext): ModelProfile {
    // Priority-based selection
    const candidates = this.filterCandidates(context)

    // Score each candidate
    const scored = candidates.map(model => ({
      model,
      score: this.scoreModel(model, context)
    }))

    // Sort by score and select best
    scored.sort((a, b) => b.score - a.score)
    return scored[0].model
  }

  private scoreModel(
    model: ModelProfile,
    context: SelectionContext
  ): number {
    let score = 0

    // Context size compatibility
    if (context.tokenCount <= model.capabilities.maxContextTokens) {
      score += 100
    } else {
      return -1 // Disqualify if context too large
    }

    // Tool support requirement
    if (context.requiresTools && model.capabilities.supportsTools) {
      score += 50
    } else if (context.requiresTools) {
      return -1 // Disqualify if tools required but not supported
    }

    // Cost optimization
    const costScore = 100 - (model.capabilities.costPer1kTokens.input * 10)
    score += costScore * context.costWeight

    // Speed optimization
    if (context.prioritizeSpeed && model.metadata?.tags?.includes('fast')) {
      score += 50
    }

    // Quality optimization
    if (context.prioritizeQuality && model.metadata?.tags?.includes('powerful')) {
      score += 50
    }

    return score
  }
}
```

### Context-Based Switching

Intelligent analysis of conversation context for model optimization:

```typescript
class ContextAnalyzer {
  analyzeContext(messages: Message[]): ContextAnalysis {
    const tokenCount = this.countTokens(messages)
    const hasImages = this.detectImages(messages)
    const codeRatio = this.calculateCodeRatio(messages)
    const complexity = this.estimateComplexity(messages)

    return {
      tokenCount,
      hasImages,
      codeRatio,
      complexity,
      recommendedModel: this.recommendModel({
        tokenCount,
        hasImages,
        codeRatio,
        complexity
      })
    }
  }

  private estimateComplexity(messages: Message[]): ComplexityLevel {
    const indicators = {
      multiStep: /step \d+|first|then|finally/i,
      technical: /algorithm|optimize|refactor|architecture/i,
      analysis: /analyze|explain|compare|evaluate/i,
      creative: /create|design|generate|imagine/i
    }

    let score = 0
    for (const message of messages) {
      for (const [type, pattern] of Object.entries(indicators)) {
        if (pattern.test(message.content)) {
          score += 1
        }
      }
    }

    if (score >= 4) return 'high'
    if (score >= 2) return 'medium'
    return 'low'
  }
}
```

## Model Switching

### Automatic Switching

The system automatically switches models based on various conditions:

```typescript
class ModelSwitcher {
  async switchModel(
    reason: SwitchReason,
    currentModel: ModelProfile,
    context: SwitchContext
  ): Promise<ModelProfile> {
    switch (reason) {
      case 'CONTEXT_OVERFLOW':
        return this.switchToLargerContext(currentModel, context)

      case 'RATE_LIMITED':
        return this.switchToBackup(currentModel)

      case 'ERROR':
        return this.switchToFallback(currentModel)

      case 'COST_OPTIMIZATION':
        return this.switchToCheaper(currentModel, context)

      case 'QUALITY_NEEDED':
        return this.switchToStronger(currentModel)

      case 'SPEED_NEEDED':
        return this.switchToFaster(currentModel)

      default:
        return currentModel
    }
  }

  private switchToBackup(current: ModelProfile): ModelProfile {
    // Define backup chain
    const backupChain = {
      'claude-3-5-sonnet': 'claude-3-5-haiku',
      'claude-3-5-haiku': 'gpt-4o',
      'gpt-4o': 'gpt-3.5-turbo',
      'gpt-3.5-turbo': 'claude-3-5-haiku'
    }

    const backupId = backupChain[current.id]
    return this.getProfile(backupId) || current
  }
}
```

## Cost Management

### Cost Tracking

Comprehensive tracking of model usage and costs:

```typescript
class CostTracker {
  private usage: Map<string, ModelUsage> = new Map()

  track(
    model: ModelProfile,
    inputTokens: number,
    outputTokens: number
  ): void {
    const usage = this.usage.get(model.id) || {
      inputTokens: 0,
      outputTokens: 0,
      cost: 0,
      requests: 0
    }

    usage.inputTokens += inputTokens
    usage.outputTokens += outputTokens
    usage.requests += 1

    // Calculate cost
    const inputCost = (inputTokens / 1000) * model.capabilities.costPer1kTokens.input
    const outputCost = (outputTokens / 1000) * model.capabilities.costPer1kTokens.output
    usage.cost += inputCost + outputCost

    this.usage.set(model.id, usage)
    this.emitCostUpdate(model.id, usage)
  }

  async enforceCostLimit(limit: number): Promise<void> {
    const summary = this.getUsageSummary()

    if (summary.totalCost >= limit) {
      throw new CostLimitExceededError(
        `Cost limit of $${limit} exceeded. Current: $${summary.totalCost.toFixed(4)}`
      )
    }

    if (summary.totalCost >= limit * 0.8) {
      this.emitCostWarning(summary.totalCost, limit)
    }
  }
}
```

## Profile Management

### CRUD Operations

Complete lifecycle management for model profiles:

```typescript
class ProfileManager {
  private profiles: Map<string, ModelProfile> = new Map()
  private configPath: string

  async createProfile(profile: ModelProfile): Promise<void> {
    this.validateProfile(profile)

    if (this.profiles.has(profile.id)) {
      throw new Error(`Profile ${profile.id} already exists`)
    }

    this.profiles.set(profile.id, {
      ...profile,
      metadata: {
        ...profile.metadata,
        createdAt: new Date(),
        updatedAt: new Date()
      }
    })

    await this.saveProfiles()
  }

  private validateProfile(profile: ModelProfile): void {
    // Required fields validation
    if (!profile.id) throw new Error('Profile ID is required')
    if (!profile.name) throw new Error('Profile name is required')
    if (!profile.provider) throw new Error('Provider is required')
    if (!profile.config.model) throw new Error('Model is required')

    // Provider-specific validation
    switch (profile.provider) {
      case 'anthropic':
        this.validateAnthropicProfile(profile)
        break
      case 'openai':
        this.validateOpenAIProfile(profile)
        break
      case 'custom':
        this.validateCustomProfile(profile)
        break
    }
  }
}
```

## Error Handling

### Provider Error Management

Comprehensive error handling and recovery strategies:

```typescript
class ProviderErrorHandler {
  async handleError(
    error: Error,
    provider: AIProvider,
    request: MessageRequest
  ): Promise<MessageResponse> {
    if (this.isRateLimitError(error)) {
      return this.handleRateLimit(provider, request)
    }

    if (this.isAuthError(error)) {
      return this.handleAuthError(provider)
    }

    if (this.isNetworkError(error)) {
      return this.retryWithBackoff(provider, request)
    }

    if (this.isContextLengthError(error)) {
      return this.handleContextOverflow(request)
    }

    // Unrecoverable error
    throw new ProviderError(error.message, provider, error)
  }

  private async handleRateLimit(
    provider: AIProvider,
    request: MessageRequest
  ): Promise<MessageResponse> {
    const retryAfter = this.extractRetryAfter(error)

    if (retryAfter) {
      await sleep(retryAfter * 1000)
      return provider.createMessage(request)
    }

    // Switch to backup provider
    const backup = this.getBackupProvider(provider)
    return backup.createMessage(request)
  }
}
```

## Benefits of Capability-Driven Design

1. **Eliminates Hardcoded Logic**: No more if/else chains for model-specific behavior
2. **Consistent Behavior**: Same capabilities produce same behavior across adapters
3. **Easy Extension**: Adding new models only requires capability definition
4. **Type Safety**: Compile-time validation of model capabilities
5. **Performance**: Cached lookups prevent repeated computation
6. **Maintainability**: Centralized capability definitions reduce code duplication

---

The Model Management System provides comprehensive, flexible, and robust handling of multiple AI providers with intelligent model selection, cost optimization, and error recovery.