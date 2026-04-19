# Query Engine Module

## Overview

The Query Engine (`src/query.ts`) is the heart of Kode's AI conversation system. It orchestrates the entire conversation flow, manages tool execution, handles streaming responses, and ensures proper context management.

## Core Functionality

### Main Query Function

```typescript
export async function* query(
  queryOptions: QueryOptions
): AsyncGenerator<QueryStreamEvent> {
  // 1. Context preparation
  // 2. Model selection
  // 3. API request with streaming
  // 4. Tool use detection and execution
  // 5. Result integration
  // 6. Recursive continuation if needed
}
```

### Query Options

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

## Conversation Flow

### 1. Message Preparation

```typescript
function prepareMessages(
  messages: Message[],
  systemPrompt: string,
  context: Context
): AnthropicMessage[] {
  // Add system context
  const systemMessage = buildSystemMessage(systemPrompt, context)
  
  // Convert internal messages to API format
  const apiMessages = messages.map(convertToAPIFormat)
  
  // Optimize token usage
  return compactMessages(apiMessages)
}
```

### 2. Streaming Response Handler

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

### 3. Tool Execution Pipeline

```typescript
async function* executeTools(
  toolUses: ToolUse[],
  context: ToolContext
): AsyncGenerator<ToolExecutionEvent> {
  // Determine execution strategy
  const strategy = context.safeMode ? 'serial' : 'concurrent'
  
  if (strategy === 'concurrent') {
    // Execute tools in parallel
    yield* executeConcurrent(toolUses, context)
  } else {
    // Execute tools serially for safety
    yield* executeSerial(toolUses, context)
  }
}
```

## Tool Execution

### Serial Execution (Safe Mode)

```typescript
async function* executeSerial(
  toolUses: ToolUse[],
  context: ToolContext
): AsyncGenerator<ToolResult> {
  for (const toolUse of toolUses) {
    // Request permission
    const permission = await requestPermission(toolUse)
    
    if (!permission.granted) {
      yield {
        type: 'error',
        toolUseId: toolUse.id,
        error: 'Permission denied'
      }
      continue
    }
    
    // Execute tool
    const tool = findTool(toolUse.name)
    yield* tool.call(toolUse.input, context)
  }
}
```

### Concurrent Execution (Permissive Mode)

```typescript
async function* executeConcurrent(
  toolUses: ToolUse[],
  context: ToolContext
): AsyncGenerator<ToolResult> {
  // Group tools by permission requirements
  const { safe, needsPermission } = groupByPermission(toolUses)
  
  // Execute safe tools immediately
  const safePromises = safe.map(tool => 
    executeToolAsync(tool, context)
  )
  
  // Request permissions for others
  const permissions = await requestBatchPermissions(needsPermission)
  
  // Execute approved tools
  const approvedPromises = permissions
    .filter(p => p.granted)
    .map(p => executeToolAsync(p.tool, context))
  
  // Yield results as they complete
  for await (const result of mergeAsyncIterables([
    ...safePromises,
    ...approvedPromises
  ])) {
    yield result
  }
}
```

## Context Management

### Token Counting

```typescript
class TokenManager {
  private usage: TokenUsage = {
    input: 0,
    output: 0,
    total: 0
  }
  
  count(messages: Message[]): number {
    // Use tiktoken for accurate counting
    return messages.reduce((total, msg) => 
      total + countTokens(msg.content), 0
    )
  }
  
  shouldCompact(usage: TokenUsage, limit: number): boolean {
    return usage.total > limit * 0.8
  }
  
  compact(messages: Message[]): Message[] {
    // Remove old messages while preserving context
    return intelligentCompaction(messages)
  }
}
```

### Context Injection

```typescript
function injectContext(
  messages: Message[],
  context: ProjectContext
): Message[] {
  // Add project context
  const contextMessage = {
    role: 'system',
    content: formatContext(context)
  }
  
  // Add recent file reads
  const fileContext = getRecentFileReads()
  
  // Add git status
  const gitContext = getGitStatus()
  
  return [
    contextMessage,
    ...fileContext,
    ...gitContext,
    ...messages
  ]
}
```

## Error Handling

### Error Recovery

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
    // Switch to backup model
    const backupModel = getBackupModel()
    yield* retryWithModel(backupModel, context)
    return
  }
  
  if (error.name === 'ContextLengthError') {
    // Compact and retry
    const compacted = compactMessages(context.messages)
    yield* retryWithMessages(compacted, context)
    return
  }
  
  // Unrecoverable error
  yield {
    type: 'error',
    error: formatError(error)
  }
}
```

### Graceful Degradation

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

## Streaming Architecture

### Kode's Three-Level Streaming Pipeline

Kode implements a sophisticated async generator streaming architecture that ensures real-time responsiveness:

1. **Provider Stream** (`claude.ts` / `openai.ts`)
   - Handles raw API chunks (SSE events)
   - Performs real-time event processing
   - Normalizes provider-specific events into internal format

2. **Query Generator** (`query.ts`)
   - Async generator yielding `Message` events as they arrive
   - Builds structured message objects with content blocks
   - Tracks TTFT (Time-To-First-Token)

3. **REPL Consumer** (`REPL.tsx`)
   - Consumes query generator with `for await` loop
   - Updates UI in real-time
   - Supports cancellation via AbortSignal

### Event Types

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

### Stream Management

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
        
        // Parse SSE events
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

## Performance Optimizations

### Caching

```typescript
class ResponseCache {
  private cache = new LRUCache<string, CachedResponse>({
    max: 100,
    ttl: 1000 * 60 * 5 // 5 minutes
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

### Parallel Processing

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

## Advanced Features

### Thinking Tokens

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
    // Hide thinking from user
    return {
      ...response,
      content: removeThinkingBlocks(response.content)
    }
  }
}
```

### Binary Feedback

```typescript
class BinaryFeedback {
  async collectFeedback(
    response1: Response,
    response2: Response
  ): Promise<Feedback> {
    // Show both responses
    displayComparison(response1, response2)
    
    // Collect user preference
    const preference = await getUserPreference()
    
    // Log for model improvement
    logFeedback({
      responses: [response1, response2],
      preference,
      context: getCurrentContext()
    })
    
    return preference
  }
}
```

### Model Switching

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

## Monitoring and Metrics

### Performance Tracking

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
  // Log to analytics
  analytics.track('query_completed', metrics)
  
  // Update cost tracking
  updateCostTracking(metrics.tokensUsed, metrics.modelUsed)
  
  // Performance monitoring
  if (metrics.endTime - metrics.startTime > 30000) {
    logSlowQuery(metrics)
  }
}
```

## Error Recovery Strategies

### Retry Logic

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
      delay *= 2 // Exponential backoff
    }
  }
  
  throw new Error('Max retries exceeded')
}
```

The Query Engine provides robust, efficient, and extensible AI conversation orchestration with comprehensive error handling, performance optimization, and security integration.