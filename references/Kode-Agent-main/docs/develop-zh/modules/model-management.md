# 模型管理系统

## 概述

模型管理系统（`src/utils/model.ts`）为管理多个 AI 提供商、模型配置和智能模型切换提供了统一的接口。它将不同 AI API 的复杂性抽象在一致的接口后面。

## 核心架构

### ModelManager 类

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
  
  // 模型解析
  resolveModel(pointer: string): ModelInfo
  
  // 模型切换
  switchToNextModel(reason: SwitchReason): ModelInfo
  
  // 上下文分析
  analyzeContextCompatibility(messages: Message[]): ContextAnalysis
  
  // 配置文件管理
  addProfile(profile: ModelProfile): void
  updateProfile(id: string, updates: Partial<ModelProfile>): void
  deleteProfile(id: string): void
}
```

## 模型配置

### 模型配置文件结构

```typescript
interface ModelProfile {
  id: string                    // 唯一标识符
  name: string                  // 显示名称
  provider: ModelProvider       // 'anthropic' | 'openai' | 'bedrock' | 'vertex' | 'custom'
  config: {
    model: string              // 模型标识符（例如 'claude-3-5-sonnet-20241022'）
    baseURL?: string           // 自定义端点 URL
    apiKey?: string            // 提供商 API 密钥
    maxTokens?: number         // 最大输出令牌
    temperature?: number       // 采样温度
    topP?: number             // 核采样
    topK?: number             // Top-K 采样
    stopSequences?: string[]   // 停止序列
    systemPrompt?: string      // 默认系统提示
    headers?: Record<string, string>  // 自定义头部
    timeout?: number           // 请求超时
    retryConfig?: RetryConfig // 重试配置
  }
  capabilities?: {
    supportsTools: boolean     // 工具/函数调用支持
    supportsVision: boolean    // 图像输入支持
    supportsStreaming: boolean // 流式响应支持
    maxContextTokens: number   // 上下文窗口大小
    costPer1kTokens: {
      input: number
      output: number
    }
  }
  metadata?: {
    description?: string       // 配置文件描述
    tags?: string[]           // 分类标签
    createdAt?: Date
    updatedAt?: Date
    usageCount?: number
  }
}
```

### 模型指针

```typescript
interface ModelPointers {
  main: string        // 主要对话模型
  task: string        // 任务执行模型（快速、高效）
  reasoning: string   // 复杂推理模型（强大）
  quick: string       // 快速响应（超快）
  vision?: string     // 图像分析模型
  code?: string       // 代码特定模型
  [key: string]: string | undefined  // 自定义指针
}
```

### 默认配置文件

```typescript
const DEFAULT_PROFILES: ModelProfile[] = [
  {
    id: 'claude-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'anthropic',
    config: {
      model: 'claude-3-5-sonnet-20241022',
      maxTokens: 8192,
      temperature: 0.7
    },
    capabilities: {
      supportsTools: true,
      supportsVision: true,
      supportsStreaming: true,
      maxContextTokens: 200000,
      costPer1kTokens: {
        input: 0.003,
        output: 0.015
      }
    }
  },
  {
    id: 'claude-haiku',
    name: 'Claude 3.5 Haiku',
    provider: 'anthropic',
    config: {
      model: 'claude-3-5-haiku-20241022',
      maxTokens: 8192,
      temperature: 0.7
    },
    capabilities: {
      supportsTools: true,
      supportsVision: false,
      supportsStreaming: true,
      maxContextTokens: 200000,
      costPer1kTokens: {
        input: 0.0008,
        output: 0.004
      }
    }
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    config: {
      model: 'gpt-4o',
      maxTokens: 4096,
      temperature: 0.7
    },
    capabilities: {
      supportsTools: true,
      supportsVision: true,
      supportsStreaming: true,
      maxContextTokens: 128000,
      costPer1kTokens: {
        input: 0.0025,
        output: 0.01
      }
    }
  }
]
```

## 提供商集成

### 提供商工厂

```typescript
class ProviderFactory {
  static createProvider(profile: ModelProfile): AIProvider {
    switch (profile.provider) {
      case 'anthropic':
        return new AnthropicProvider(profile)
      
      case 'openai':
        return new OpenAIProvider(profile)
      
      case 'bedrock':
        return new BedrockProvider(profile)
      
      case 'vertex':
        return new VertexProvider(profile)
      
      case 'custom':
        return new CustomProvider(profile)
      
      default:
        throw new Error(`未知提供商：${profile.provider}`)
    }
  }
}
```

### Anthropic 提供商

```typescript
class AnthropicProvider implements AIProvider {
  private client: Anthropic
  private profile: ModelProfile
  
  constructor(profile: ModelProfile) {
    this.profile = profile
    this.client = new Anthropic({
      apiKey: profile.config.apiKey,
      baseURL: profile.config.baseURL,
      defaultHeaders: profile.config.headers,
      timeout: profile.config.timeout
    })
  }
  
  async createMessage(request: MessageRequest): Promise<MessageResponse> {
    const response = await this.client.messages.create({
      model: this.profile.config.model,
      messages: this.convertMessages(request.messages),
      max_tokens: request.maxTokens || this.profile.config.maxTokens,
      temperature: request.temperature || this.profile.config.temperature,
      system: request.systemPrompt,
      tools: this.convertTools(request.tools),
      stream: request.stream
    })
    
    return this.normalizeResponse(response)
  }
  
  async *streamMessage(
    request: MessageRequest
  ): AsyncGenerator<StreamEvent> {
    const stream = await this.client.messages.stream({
      ...this.buildRequest(request),
      stream: true
    })
    
    for await (const event of stream) {
      yield this.normalizeStreamEvent(event)
    }
  }
}
```

### OpenAI 提供商

```typescript
class OpenAIProvider implements AIProvider {
  private client: OpenAI
  private profile: ModelProfile
  
  constructor(profile: ModelProfile) {
    this.profile = profile
    this.client = new OpenAI({
      apiKey: profile.config.apiKey || process.env.OPENAI_API_KEY,
      baseURL: profile.config.baseURL,
      defaultHeaders: profile.config.headers,
      timeout: profile.config.timeout
    })
  }
  
  async createMessage(request: MessageRequest): Promise<MessageResponse> {
    const completion = await this.client.chat.completions.create({
      model: this.profile.config.model,
      messages: this.convertMessages(request.messages),
      max_tokens: request.maxTokens,
      temperature: request.temperature,
      functions: this.convertTools(request.tools),
      stream: request.stream
    })
    
    return this.normalizeResponse(completion)
  }
  
  private convertMessages(messages: Message[]): OpenAIMessage[] {
    return messages.map(msg => ({
      role: this.mapRole(msg.role),
      content: msg.content,
      name: msg.name,
      function_call: msg.toolCalls?.[0]
    }))
  }
}
```

### 自定义提供商

```typescript
class CustomProvider implements AIProvider {
  private profile: ModelProfile
  private httpClient: HTTPClient
  
  constructor(profile: ModelProfile) {
    this.profile = profile
    this.httpClient = new HTTPClient({
      baseURL: profile.config.baseURL,
      headers: {
        'Authorization': `Bearer ${profile.config.apiKey}`,
        ...profile.config.headers
      },
      timeout: profile.config.timeout
    })
  }
  
  async createMessage(request: MessageRequest): Promise<MessageResponse> {
    // 自定义 API 实现
    const response = await this.httpClient.post('/v1/messages', {
      model: this.profile.config.model,
      ...this.transformRequest(request)
    })
    
    return this.normalizeResponse(response)
  }
  
  private transformRequest(request: MessageRequest): any {
    // 转换为自定义 API 格式
    return {
      prompt: this.buildPrompt(request.messages),
      max_length: request.maxTokens,
      temperature: request.temperature,
      // 自定义转换...
    }
  }
}
```

## 模型选择逻辑

### 智能模型选择

```typescript
class ModelSelector {
  selectModel(context: SelectionContext): ModelProfile {
    // 基于优先级的选择
    const candidates = this.filterCandidates(context)
    
    // 为每个候选者评分
    const scored = candidates.map(model => ({
      model,
      score: this.scoreModel(model, context)
    }))
    
    // 按分数排序并选择最佳
    scored.sort((a, b) => b.score - a.score)
    return scored[0].model
  }
  
  private scoreModel(
    model: ModelProfile,
    context: SelectionContext
  ): number {
    let score = 0
    
    // 上下文大小兼容性
    if (context.tokenCount <= model.capabilities.maxContextTokens) {
      score += 100
    } else {
      return -1 // 如果上下文太大则取消资格
    }
    
    // 工具支持要求
    if (context.requiresTools && model.capabilities.supportsTools) {
      score += 50
    } else if (context.requiresTools) {
      return -1 // 如果需要工具但不支持则取消资格
    }
    
    // 成本优化
    const costScore = 100 - (model.capabilities.costPer1kTokens.input * 10)
    score += costScore * context.costWeight
    
    // 速度优化
    if (context.prioritizeSpeed && model.metadata?.tags?.includes('fast')) {
      score += 50
    }
    
    // 质量优化
    if (context.prioritizeQuality && model.metadata?.tags?.includes('powerful')) {
      score += 50
    }
    
    return score
  }
}
```

### 基于上下文的切换

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
  
  private countTokens(messages: Message[]): number {
    // 使用 tiktoken 进行准确计数
    const encoder = getEncoding('cl100k_base')
    
    let total = 0
    for (const message of messages) {
      const tokens = encoder.encode(message.content)
      total += tokens.length
      
      // 添加消息结构开销
      total += 4 // 角色、内容标记
    }
    
    encoder.free()
    return total
  }
  
  private estimateComplexity(messages: Message[]): ComplexityLevel {
    const indicators = {
      multiStep: /步骤 \d+|首先|然后|最后/i,
      technical: /算法|优化|重构|架构/i,
      analysis: /分析|解释|比较|评估/i,
      creative: /创建|设计|生成|想象/i
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

## 模型切换

### 自动切换

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
  
  private async switchToLargerContext(
    current: ModelProfile,
    context: SwitchContext
  ): Promise<ModelProfile> {
    const candidates = this.getAllProfiles()
      .filter(p => p.capabilities.maxContextTokens > context.requiredTokens)
      .sort((a, b) => a.capabilities.maxContextTokens - b.capabilities.maxContextTokens)
    
    if (candidates.length === 0) {
      throw new Error('没有可用的具有足够上下文的模型')
    }
    
    // 选择最小的足够模型以优化成本
    return candidates[0]
  }
  
  private switchToBackup(current: ModelProfile): ModelProfile {
    // 定义备份链
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

### 手动模型选择

```typescript
class ModelUI {
  async selectModel(
    profiles: ModelProfile[],
    current: ModelProfile
  ): Promise<ModelProfile> {
    const items = profiles.map(profile => ({
      label: this.formatProfileLabel(profile),
      value: profile.id,
      description: this.formatProfileDescription(profile)
    }))
    
    const selected = await prompt({
      type: 'select',
      message: '选择一个模型：',
      choices: items,
      initial: current.id
    })
    
    return profiles.find(p => p.id === selected)!
  }
  
  private formatProfileLabel(profile: ModelProfile): string {
    const cost = profile.capabilities.costPer1kTokens
    const context = profile.capabilities.maxContextTokens
    
    return `${profile.name} (${this.formatTokens(context)} 上下文, $${cost.input}/$${cost.output} 每千令牌)`
  }
  
  private formatTokens(tokens: number): string {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(1)}M`
    }
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(0)}k`
    }
    return tokens.toString()
  }
}
```

## 成本管理

### 成本跟踪

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
    
    // 计算成本
    const inputCost = (inputTokens / 1000) * model.capabilities.costPer1kTokens.input
    const outputCost = (outputTokens / 1000) * model.capabilities.costPer1kTokens.output
    usage.cost += inputCost + outputCost
    
    this.usage.set(model.id, usage)
    
    // 发出成本更新事件
    this.emitCostUpdate(model.id, usage)
  }
  
  getUsageSummary(): UsageSummary {
    const summary: UsageSummary = {
      totalCost: 0,
      totalInputTokens: 0,
      totalOutputTokens: 0,
      totalRequests: 0,
      byModel: {}
    }
    
    for (const [modelId, usage] of this.usage) {
      summary.totalCost += usage.cost
      summary.totalInputTokens += usage.inputTokens
      summary.totalOutputTokens += usage.outputTokens
      summary.totalRequests += usage.requests
      summary.byModel[modelId] = { ...usage }
    }
    
    return summary
  }
  
  async enforceCostLimit(limit: number): Promise<void> {
    const summary = this.getUsageSummary()
    
    if (summary.totalCost >= limit) {
      throw new CostLimitExceededError(
        `超出成本限制 $${limit}。当前：$${summary.totalCost.toFixed(4)}`
      )
    }
    
    if (summary.totalCost >= limit * 0.8) {
      this.emitCostWarning(summary.totalCost, limit)
    }
  }
}
```

### 成本优化

```typescript
class CostOptimizer {
  optimizeModelSelection(
    task: TaskType,
    budget: number,
    profiles: ModelProfile[]
  ): ModelProfile {
    // 估算任务的令牌
    const estimatedTokens = this.estimateTokensForTask(task)
    
    // 筛选预算内的模型
    const affordable = profiles.filter(profile => {
      const cost = this.calculateCost(profile, estimatedTokens)
      return cost <= budget
    })
    
    if (affordable.length === 0) {
      throw new Error('预算内没有可用的模型')
    }
    
    // 在预算内选择最佳质量
    return this.selectBestQuality(affordable, task)
  }
  
  private estimateTokensForTask(task: TaskType): TokenEstimate {
    const estimates = {
      simple_question: { input: 500, output: 500 },
      code_generation: { input: 1000, output: 2000 },
      analysis: { input: 2000, output: 1500 },
      refactoring: { input: 3000, output: 3000 },
      complex_task: { input: 5000, output: 5000 }
    }
    
    return estimates[task] || estimates.complex_task
  }
}
```

模型管理系统提供了全面、灵活和强大的多个 AI 提供商处理，具有智能模型选择、成本优化和错误恢复功能。
