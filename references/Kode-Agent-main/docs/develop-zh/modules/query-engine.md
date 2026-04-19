# 查询引擎模块

## 概述

查询引擎（`src/query.ts`）是 Kode AI 对话系统的核心。它编排整个对话流程，管理工具执行，处理流式响应，并确保正确的上下文管理。

## 核心功能

### 主查询函数

```typescript
export async function* query(
  queryOptions: QueryOptions
): AsyncGenerator<QueryStreamEvent> {
  // 1. 上下文准备
  // 2. 模型选择
  // 3. 带流式的 API 请求
  // 4. 工具使用检测和执行
  // 5. 结果集成
  // 6. 如需要则递归继续
}
```

### 查询选项

```typescript
interface QueryOptions {
  prompt: string
  model: ModelInfo
  messages: Message[]
  tools: Tool[]
  hasPermissionsToUseTool: PermissionChecker
  onUpdateUsage?: (usage: Usage) => void
  abortSignal?: AbortSignal
  enableThinking?: boolean
  safeMode?: boolean
}
```

## 对话流程

### 1. 消息准备

```typescript
function prepareMessages(
  messages: Message[],
  systemPrompt: string,
  context: Context
): AnthropicMessage[] {
  // 添加系统上下文
  const systemMessage = buildSystemMessage(systemPrompt, context)
  
  // 将内部消息转换为 API 格式
  const apiMessages = messages.map(convertToAPIFormat)
  
  // 优化令牌使用
  return compactMessages(apiMessages)
}
```

### 2. 流式响应处理器

```typescript
async function* handleStreamingResponse(
  stream: AsyncIterable<StreamEvent>
): AsyncGenerator<QueryStreamEvent> {
  for await (const event of stream) {
    switch (event.type) {
      case 'content_block_start':
        yield { type: 'text_delta', text: event.content }
        break
        
      case 'tool_use':
        yield { type: 'tool_request', tool: event.tool }
        break
        
      case 'message_stop':
        yield { type: 'complete' }
        break
    }
  }
}
```

### 3. 工具执行管道

```typescript
async function* executeTools(
  toolUses: ToolUse[],
  context: ToolContext
): AsyncGenerator<ToolExecutionEvent> {
  // 确定执行策略
  const strategy = context.safeMode ? 'serial' : 'concurrent'
  
  if (strategy === 'concurrent') {
    // 并行执行工具
    yield* executeConcurrent(toolUses, context)
  } else {
    // 为安全串行执行工具
    yield* executeSerial(toolUses, context)
  }
}
```

## 工具执行

### 串行执行（安全模式）

```typescript
async function* executeSerial(
  toolUses: ToolUse[],
  context: ToolContext
): AsyncGenerator<ToolResult> {
  for (const toolUse of toolUses) {
    // 请求权限
    const permission = await requestPermission(toolUse)
    
    if (!permission.granted) {
      yield {
        type: 'error',
        toolUseId: toolUse.id,
        error: '权限被拒绝'
      }
      continue
    }
    
    // 执行工具
    const tool = findTool(toolUse.name)
    yield* tool.call(toolUse.input, context)
  }
}
```

### 并发执行（宽松模式）

```typescript
async function* executeConcurrent(
  toolUses: ToolUse[],
  context: ToolContext
): AsyncGenerator<ToolResult> {
  // 按权限要求分组工具
  const { safe, needsPermission } = groupByPermission(toolUses)
  
  // 立即执行安全工具
  const safePromises = safe.map(tool => 
    executeToolAsync(tool, context)
  )
  
  // 为其他工具请求权限
  const permissions = await requestBatchPermissions(needsPermission)
  
  // 执行批准的工具
  const approvedPromises = permissions
    .filter(p => p.granted)
    .map(p => executeToolAsync(p.tool, context))
  
  // 在完成时产生结果
  for await (const result of mergeAsyncIterables([
    ...safePromises,
    ...approvedPromises
  ])) {
    yield result
  }
}
```

## 上下文管理

### 令牌计数

```typescript
class TokenManager {
  private usage: TokenUsage = {
    input: 0,
    output: 0,
    total: 0
  }
  
  count(messages: Message[]): number {
    // 使用 tiktoken 进行准确计数
    return messages.reduce((total, msg) => 
      total + countTokens(msg.content), 0
    )
  }
  
  shouldCompact(usage: TokenUsage, limit: number): boolean {
    return usage.total > limit * 0.8
  }
  
  compact(messages: Message[]): Message[] {
    // 删除旧消息同时保留上下文
    return intelligentCompaction(messages)
  }
}
```

### 上下文注入

```typescript
function injectContext(
  messages: Message[],
  context: ProjectContext
): Message[] {
  // 添加项目上下文
  const contextMessage = {
    role: 'system',
    content: formatContext(context)
  }
  
  // 添加最近的文件读取
  const fileContext = getRecentFileReads()
  
  // 添加 git 状态
  const gitContext = getGitStatus()
  
  return [
    contextMessage,
    ...fileContext,
    ...gitContext,
    ...messages
  ]
}
```

## 错误处理

### 错误恢复

```typescript
async function* handleError(
  error: Error,
  context: QueryContext
): AsyncGenerator<QueryStreamEvent> {
  if (error.name === 'AbortError') {
    yield { type: 'cancelled' }
    return
  }
  
  if (error.name === 'RateLimitError') {
    // 切换到备份模型
    const backupModel = getBackupModel()
    yield* retryWithModel(backupModel, context)
    return
  }
  
  if (error.name === 'ContextLengthError') {
    // 压缩并重试
    const compacted = compactMessages(context.messages)
    yield* retryWithMessages(compacted, context)
    return
  }
  
  // 不可恢复的错误
  yield {
    type: 'error',
    error: formatError(error)
  }
}
```

### 优雅降级

```typescript
function selectFallbackStrategy(error: Error): Strategy {
  switch (error.type) {
    case 'MODEL_UNAVAILABLE':
      return useAlternativeModel()
      
    case 'TOOL_FAILURE':
      return continueWithoutTool()
      
    case 'PERMISSION_DENIED':
      return requestAlternativeApproach()
      
    default:
      return reportErrorToUser()
  }
}
```

## 流式架构

### 事件类型

```typescript
type QueryStreamEvent = 
  | { type: 'text_delta', text: string }
  | { type: 'tool_request', tool: ToolUse }
  | { type: 'tool_result', result: ToolResult }
  | { type: 'thinking', content: string }
  | { type: 'error', error: Error }
  | { type: 'complete' }
  | { type: 'usage', usage: TokenUsage }
```

### 流管理

```typescript
class StreamManager {
  private buffer: string = ''
  private chunks: StreamEvent[] = []
  
  async *process(
    stream: ReadableStream
  ): AsyncGenerator<QueryStreamEvent> {
    const reader = stream.getReader()
    
    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        // 解析 SSE 事件
        const events = parseSSE(value)
        
        for (const event of events) {
          yield* processEvent(event)
        }
      }
    } finally {
      reader.releaseLock()
    }
  }
}
```

## 性能优化

### 缓存

```typescript
class ResponseCache {
  private cache = new LRUCache<string, CachedResponse>({
    max: 100,
    ttl: 1000 * 60 * 5 // 5 分钟
  })
  
  getCacheKey(messages: Message[], tools: Tool[]): string {
    return hash({ messages, tools: tools.map(t => t.name) })
  }
  
  get(key: string): CachedResponse | null {
    return this.cache.get(key)
  }
  
  set(key: string, response: CachedResponse): void {
    this.cache.set(key, response)
  }
}
```

### 并行处理

```typescript
async function processToolsInBatches(
  tools: ToolUse[],
  batchSize: number = 5
): Promise<ToolResult[]> {
  const results: ToolResult[] = []
  
  for (let i = 0; i < tools.length; i += batchSize) {
    const batch = tools.slice(i, i + batchSize)
    const batchResults = await Promise.all(
      batch.map(tool => executeTool(tool))
    )
    results.push(...batchResults)
  }
  
  return results
}
```

## 高级功能

### 思考令牌

```typescript
function processThinkingTokens(
  response: APIResponse
): ProcessedResponse {
  const thinkingBlocks = extractThinkingBlocks(response)
  
  if (shouldShowThinking()) {
    return {
      ...response,
      thinking: thinkingBlocks
    }
  } else {
    // 对用户隐藏思考
    return {
      ...response,
      content: removeThinkingBlocks(response.content)
    }
  }
}
```

### 二元反馈

```typescript
class BinaryFeedback {
  async collectFeedback(
    response1: Response,
    response2: Response
  ): Promise<Feedback> {
    // 显示两个响应
    displayComparison(response1, response2)
    
    // 收集用户偏好
    const preference = await getUserPreference()
    
    // 记录以改进模型
    logFeedback({
      responses: [response1, response2],
      preference,
      context: getCurrentContext()
    })
    
    return preference
  }
}
```

### 模型切换

```typescript
class ModelSwitcher {
  async switchModel(
    reason: SwitchReason,
    currentModel: Model
  ): Promise<Model> {
    switch (reason) {
      case 'CONTEXT_TOO_LARGE':
        return this.getLargerContextModel()
        
      case 'RATE_LIMITED':
        return this.getBackupModel()
        
      case 'SPECIALIZED_TASK':
        return this.getSpecializedModel()
        
      default:
        return this.getDefaultModel()
    }
  }
}
```

## 监控和指标

### 性能跟踪

```typescript
interface QueryMetrics {
  startTime: number
  endTime: number
  tokensUsed: TokenUsage
  toolsExecuted: number
  errorsEncountered: number
  modelUsed: string
  cacheHit: boolean
}

function trackQuery(metrics: QueryMetrics): void {
  // 记录到分析
  analytics.track('query_completed', metrics)
  
  // 更新成本跟踪
  updateCostTracking(metrics.tokensUsed, metrics.modelUsed)
  
  // 性能监控
  if (metrics.endTime - metrics.startTime > 30000) {
    logSlowQuery(metrics)
  }
}
```

## 错误恢复策略

### 重试逻辑

```typescript
async function* retryWithBackoff(
  operation: () => AsyncGenerator<QueryStreamEvent>,
  maxRetries: number = 3
): AsyncGenerator<QueryStreamEvent> {
  let retries = 0
  let delay = 1000
  
  while (retries < maxRetries) {
    try {
      yield* operation()
      return
    } catch (error) {
      if (!isRetryable(error)) throw error
      
      retries++
      yield {
        type: 'retry',
        attempt: retries,
        delay
      }
      
      await sleep(delay)
      delay *= 2 // 指数退避
    }
  }
  
  throw new Error('超过最大重试次数')
}
```

查询引擎提供强大、高效和可扩展的 AI 对话编排，具有全面的错误处理、性能优化和安全集成。