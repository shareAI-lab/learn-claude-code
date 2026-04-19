# REPL Interface Module

## Overview

The REPL module (`src/screens/REPL.tsx`) provides the main interactive interface for Kode. It's a sophisticated React-based terminal UI that handles user input, displays responses, manages conversation state, and orchestrates the entire interactive experience.

## Architecture

### Component Structure

```typescript
interface REPLProps {
  commands: Command[]
  initialPrompt?: string
  messageLogName: string
  shouldShowPromptInput: boolean
  verbose?: boolean
  tools: Tool[]
  safeMode?: boolean
  mcpClients?: MCPClient[]
  isDefaultModel: boolean
  initialMessages?: Message[]
  initialForkNumber?: number
}

export function REPL(props: REPLProps): JSX.Element {
  // State management
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [currentModel, setCurrentModel] = useState<Model>()
  
  // Conversation handling
  // UI rendering
  // Event handlers
}
```

## State Management

### Message State

```typescript
interface ConversationState {
  messages: Message[]
  pendingMessages: Message[]
  streamingContent: string
  currentToolUse?: ToolUse
  error?: Error
}

const useConversationState = () => {
  const [state, dispatch] = useReducer(
    conversationReducer,
    initialState
  )
  
  const addMessage = (message: Message) => {
    dispatch({ type: 'ADD_MESSAGE', payload: message })
  }
  
  const updateStreamingContent = (content: string) => {
    dispatch({ type: 'UPDATE_STREAMING', payload: content })
  }
  
  return { state, addMessage, updateStreamingContent }
}
```

### Model State

```typescript
const useModelState = () => {
  const [modelPointer, setModelPointer] = useState('main')
  const [modelProfile, setModelProfile] = useState<ModelProfile>()
  const [isDefaultModel, setIsDefaultModel] = useState(true)
  
  const switchModel = async (pointer: string) => {
    const profile = await resolveModelProfile(pointer)
    setModelProfile(profile)
    setModelPointer(pointer)
  }
  
  return { modelProfile, switchModel, isDefaultModel }
}
```

## User Input Handling

### Prompt Input Component

```typescript
const PromptInput: React.FC<{
  onSubmit: (input: string) => void
  isLoading: boolean
  multiline: boolean
}> = ({ onSubmit, isLoading, multiline }) => {
  const [value, setValue] = useState('')
  const [cursorPosition, setCursorPosition] = useState(0)
  
  const handleKeyPress = (key: string, event: KeyEvent) => {
    if (key === 'enter' && !event.shift) {
      if (!isLoading && value.trim()) {
        onSubmit(value)
        setValue('')
      }
    }
    // Handle other keys (arrows, backspace, etc.)
  }
  
  return (
    <Box flexDirection="column">
      <TextInput
        value={value}
        onChange={setValue}
        onKeyPress={handleKeyPress}
        placeholder={isLoading ? 'Processing...' : 'Enter prompt...'}
        isDisabled={isLoading}
      />
      {multiline && <MultilineEditor value={value} />}
    </Box>
  )
}
```

### Command Processing

```typescript
async function processUserInput(
  input: string,
  context: REPLContext
): Promise<void> {
  // Check for slash commands
  if (input.startsWith('/')) {
    await handleSlashCommand(input, context)
    return
  }
  
  // Check for special shortcuts
  if (input === '!!') {
    await retryLastCommand(context)
    return
  }
  
  // Process as AI conversation
  await handleAIConversation(input, context)
}
```

## Message Rendering

### Message Display Pipeline

```typescript
const MessageRenderer: React.FC<{
  message: Message
  verbose: boolean
}> = ({ message, verbose }) => {
  switch (message.type) {
    case 'user':
      return <UserMessage message={message} />
      
    case 'assistant':
      return <AssistantMessage message={message} verbose={verbose} />
      
    case 'tool_use':
      return <ToolUseMessage message={message} />
      
    case 'tool_result':
      return <ToolResultMessage message={message} />
      
    case 'error':
      return <ErrorMessage message={message} />
      
    default:
      return null
  }
}
```

### Streaming Response Display

```typescript
const StreamingMessage: React.FC<{
  content: string
  isThinking?: boolean
}> = ({ content, isThinking }) => {
  const [displayContent, setDisplayContent] = useState('')
  const [cursor, setCursor] = useState(true)
  
  // Animate content appearance
  useEffect(() => {
    const chars = content.split('')
    let index = 0
    
    const interval = setInterval(() => {
      if (index < chars.length) {
        setDisplayContent(prev => prev + chars[index])
        index++
      } else {
        clearInterval(interval)
      }
    }, 10) // Typing animation speed
    
    return () => clearInterval(interval)
  }, [content])
  
  // Cursor blink
  useEffect(() => {
    const interval = setInterval(() => {
      setCursor(prev => !prev)
    }, 500)
    
    return () => clearInterval(interval)
  }, [])
  
  return (
    <Box>
      <Text color={isThinking ? 'gray' : 'white'}>
        {displayContent}
        {cursor && '█'}
      </Text>
    </Box>
  )
}
```

## Conversation Management

### Query Orchestration

```typescript
async function executeQuery(
  prompt: string,
  context: REPLContext
): Promise<void> {
  const abortController = new AbortController()
  
  try {
    setIsLoading(true)
    
    // Add user message
    const userMessage = createUserMessage(prompt)
    addMessage(userMessage)
    
    // Execute query
    const stream = query({
      prompt,
      messages: context.messages,
      model: context.currentModel,
      tools: context.tools,
      abortSignal: abortController.signal,
      safeMode: context.safeMode
    })
    
    // Process stream
    for await (const event of stream) {
      await processStreamEvent(event, context)
    }
    
  } catch (error) {
    handleQueryError(error, context)
  } finally {
    setIsLoading(false)
  }
}
```

### Stream Event Processing

```typescript
async function processStreamEvent(
  event: QueryStreamEvent,
  context: REPLContext
): Promise<void> {
  switch (event.type) {
    case 'text_delta':
      updateStreamingContent(event.text)
      break
      
    case 'tool_request':
      await handleToolRequest(event.tool, context)
      break
      
    case 'tool_result':
      displayToolResult(event.result)
      break
      
    case 'thinking':
      if (context.showThinking) {
        displayThinking(event.content)
      }
      break
      
    case 'complete':
      finalizeResponse(context)
      break
      
    case 'error':
      handleStreamError(event.error, context)
      break
  }
}
```

## Tool Integration

### Tool Execution Display

```typescript
const ToolExecutionDisplay: React.FC<{
  toolUse: ToolUse
  status: 'pending' | 'running' | 'complete' | 'error'
}> = ({ toolUse, status }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'pending': return '⏳'
      case 'running': return <Spinner />
      case 'complete': return '✅'
      case 'error': return '❌'
    }
  }
  
  return (
    <Box flexDirection="column" borderStyle="round" padding={1}>
      <Box>
        <Text bold>{getStatusIcon()} {toolUse.name}</Text>
      </Box>
      <Box marginTop={1}>
        <Text dim>{JSON.stringify(toolUse.input, null, 2)}</Text>
      </Box>
      {status === 'complete' && (
        <Box marginTop={1}>
          <Text color="green">Tool completed successfully</Text>
        </Box>
      )}
    </Box>
  )
}
```

### Permission Requests

```typescript
const PermissionRequestHandler: React.FC<{
  request: PermissionRequest
  onApprove: () => void
  onDeny: () => void
}> = ({ request, onApprove, onDeny }) => {
  const [showDetails, setShowDetails] = useState(false)
  
  return (
    <Box flexDirection="column" borderStyle="double" borderColor="yellow">
      <Text bold color="yellow">⚠️ Permission Required</Text>
      <Text>{request.description}</Text>
      
      {showDetails && (
        <Box marginTop={1}>
          <Text dim>{request.details}</Text>
        </Box>
      )}
      
      <Box marginTop={1}>
        <SelectInput
          items={[
            { label: 'Approve', value: 'approve' },
            { label: 'Deny', value: 'deny' },
            { label: 'View Details', value: 'details' }
          ]}
          onSelect={(item) => {
            switch (item.value) {
              case 'approve': onApprove(); break
              case 'deny': onDeny(); break
              case 'details': setShowDetails(true); break
            }
          }}
        />
      </Box>
    </Box>
  )
}
```

## UI Features

### Keyboard Shortcuts

```typescript
const useKeyboardShortcuts = (context: REPLContext) => {
  useInput((input, key) => {
    // Global shortcuts
    if (key.ctrl && input === 'c') {
      handleCancel(context)
    }
    
    if (key.ctrl && input === 'l') {
      clearScreen()
    }
    
    if (key.ctrl && input === 'r') {
      searchHistory(context)
    }
    
    // Vim mode shortcuts
    if (context.vimMode) {
      handleVimKeys(input, key, context)
    }
  })
}
```

### Status Bar

```typescript
const StatusBar: React.FC<{
  model: Model
  cost: number
  mode: 'normal' | 'safe'
  isLoading: boolean
}> = ({ model, cost, mode, isLoading }) => {
  return (
    <Box justifyContent="space-between" width="100%">
      <Box>
        <Text dim>Model: </Text>
        <Text color="cyan">{model.name}</Text>
      </Box>
      
      <Box>
        <Text dim>Cost: </Text>
        <Text color={cost > 1 ? 'red' : 'green'}>${cost.toFixed(4)}</Text>
      </Box>
      
      <Box>
        {mode === 'safe' && <Text color="yellow">🛡️ Safe Mode</Text>}
        {isLoading && <Spinner />}
      </Box>
    </Box>
  )
}
```

## History Management

### Conversation History

```typescript
class ConversationHistory {
  private history: Message[][] = []
  private currentIndex: number = -1
  
  save(messages: Message[]): void {
    this.history.push([...messages])
    this.currentIndex = this.history.length - 1
  }
  
  navigate(direction: 'prev' | 'next'): Message[] | null {
    if (direction === 'prev' && this.currentIndex > 0) {
      this.currentIndex--
      return this.history[this.currentIndex]
    }
    
    if (direction === 'next' && this.currentIndex < this.history.length - 1) {
      this.currentIndex++
      return this.history[this.currentIndex]
    }
    
    return null
  }
  
  search(query: string): Message[][] {
    return this.history.filter(messages =>
      messages.some(m => m.content.includes(query))
    )
  }
}
```

### Log Persistence

```typescript
async function saveConversationLog(
  messages: Message[],
  logName: string
): Promise<void> {
  const logPath = path.join(CACHE_DIR, 'messages', `${logName}.json`)
  
  const logData = {
    timestamp: new Date().toISOString(),
    messages: messages.map(sanitizeMessage),
    metadata: {
      model: getCurrentModel(),
      cost: calculateCost(messages),
      duration: getSessionDuration()
    }
  }
  
  await fs.writeFile(logPath, JSON.stringify(logData, null, 2))
}
```

## Error Handling

### Error Display

```typescript
const ErrorDisplay: React.FC<{ error: Error }> = ({ error }) => {
  const [showDetails, setShowDetails] = useState(false)
  
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="red">
      <Text color="red" bold>❌ Error</Text>
      <Text>{error.message}</Text>
      
      {showDetails && (
        <Box marginTop={1} flexDirection="column">
          <Text dim>Stack trace:</Text>
          <Text dim wrap="wrap">{error.stack}</Text>
        </Box>
      )}
      
      <Box marginTop={1}>
        <Text dim>
          Press 'd' for details, 'r' to retry, 'c' to continue
        </Text>
      </Box>
    </Box>
  )
}
```

### Recovery Options

```typescript
function handleError(
  error: Error,
  context: REPLContext
): RecoveryAction {
  if (error.name === 'AbortError') {
    return { type: 'cancelled' }
  }
  
  if (error.name === 'RateLimitError') {
    return {
      type: 'switch_model',
      suggestion: 'Switch to a different model?'
    }
  }
  
  if (error.name === 'ContextLengthError') {
    return {
      type: 'compact_context',
      suggestion: 'Compact conversation history?'
    }
  }
  
  return {
    type: 'retry',
    suggestion: 'Retry the operation?'
  }
}
```

## Performance Optimizations

### Virtual Scrolling

```typescript
const MessageList: React.FC<{
  messages: Message[]
  height: number
}> = ({ messages, height }) => {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 })
  
  const handleScroll = (offset: number) => {
    const start = Math.floor(offset / MESSAGE_HEIGHT)
    const end = start + Math.ceil(height / MESSAGE_HEIGHT)
    setVisibleRange({ start, end })
  }
  
  const visibleMessages = messages.slice(
    visibleRange.start,
    visibleRange.end
  )
  
  return (
    <VirtualScroll
      height={height}
      itemCount={messages.length}
      itemHeight={MESSAGE_HEIGHT}
      onScroll={handleScroll}
    >
      {visibleMessages.map(msg => (
        <MessageRenderer key={msg.id} message={msg} />
      ))}
    </VirtualScroll>
  )
}
```

### Memoization

```typescript
const MemoizedMessage = React.memo(
  MessageRenderer,
  (prevProps, nextProps) => {
    // Only re-render if message content changes
    return prevProps.message.content === nextProps.message.content &&
           prevProps.verbose === nextProps.verbose
  }
)
```

The REPL module provides a sophisticated, responsive, and user-friendly interface for AI conversations with comprehensive state management, error handling, and performance optimizations.