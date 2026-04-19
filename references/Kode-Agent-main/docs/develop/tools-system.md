# Tool System Documentation

## Overview

The Tool System is the heart of Kode's functionality, providing a standardized interface for all operations that the AI can perform. Every capability - from reading files to executing commands - is implemented as a Tool.

## Tool Interface

### Core Tool Class

```typescript
export abstract class Tool {
  abstract name: string
  abstract description: string
  abstract inputSchema: z.ZodTypeAny
  
  // Permission checking
  abstract needsPermissions(input: unknown): boolean
  
  // Input validation
  validateInput(input: unknown): unknown
  
  // Main execution method
  abstract call(
    input: unknown, 
    context: ToolUseContext
  ): AsyncGenerator<ToolCallEvent>
  
  // Format results for AI
  abstract renderResultForAssistant(
    input: unknown,
    result: unknown
  ): string
}
```

### Tool Lifecycle

```
1. Tool Registration
   ↓
2. AI Requests Tool Use
   ↓
3. Input Validation (Zod Schema)
   ↓
4. Permission Check
   ↓
5. User Approval (if needed)
   ↓
6. Tool Execution
   ↓
7. Progress Updates (via generator)
   ↓
8. Result Formatting
   ↓
9. Return to AI
```

## Tool Categories

### 1. File Operation Tools

#### FileReadTool
- **Purpose**: Read file contents with encoding detection
- **Key Features**:
  - Automatic encoding detection (UTF-8, UTF-16, etc.)
  - Binary file handling
  - Large file support with offset/limit
  - Freshness tracking to detect external changes
- **Security**: Checks file access permissions

#### FileEditTool
- **Purpose**: Make precise edits to existing files
- **Key Features**:
  - String replacement with exact matching
- File freshness validation
  - Prevents editing without reading first
  - Multiple edit support (MultiEditTool)
- **Security**: Requires file write permissions

#### FileWriteTool
- **Purpose**: Create or overwrite entire files
- **Key Features**:
  - Full file replacement
  - Directory creation if needed
  - Encoding specification
- **Security**: Requires explicit write permissions

#### NotebookEditTool
- **Purpose**: Edit Jupyter notebook cells
- **Key Features**:
  - Cell-level operations (replace, insert, delete)
  - Code and markdown cell support
  - Preserves notebook metadata

### 2. Search and Discovery Tools

#### GrepTool
- **Purpose**: Search file contents using regular expressions
- **Key Features**:
  - Ripgrep integration for speed
  - Multiple output modes (content, files, count)
  - Context lines support (-A, -B, -C)
  - File type filtering
- **Implementation**: Uses ripgrep binary for performance

#### GlobTool
- **Purpose**: Find files by name patterns
- **Key Features**:
  - Glob pattern matching
  - Hidden file support
  - Result sorting by modification time
  - Symlink following options

#### LSTool
- **Purpose**: List directory contents
- **Key Features**:
  - Recursive listing
  - Hidden file display
  - Size and permission information
  - Pattern filtering

#### WebSearchTool
- **Purpose**: Search the web for current information
- **Key Features**:
  - DuckDuckGo integration for web search
  - Returns all available results (no artificial limits)
  - Provides titles, snippets, and links
  - Fast search results for current events and data
- **Use Cases**: Finding recent news, current documentation, product updates
- **Implementation**: HTML parsing of DuckDuckGo search results

#### URLFetcherTool
- **Purpose**: Fetch and analyze web content using AI
- **Key Features**:
  - Fetches content from any URL
  - Converts HTML to clean markdown
  - AI-powered content analysis based on user prompts
  - 15-minute caching for raw content efficiency
  - Smart content truncation for large pages
  - Uses quick model for fast analysis
- **Input Schema**:
  ```typescript
  {
    url: string (URI format, required)
    prompt: string (analysis instruction, required) 
  }
  ```
- **Use Cases**: 
  - Summarizing articles or documentation
  - Extracting specific information from web pages
  - Analyzing pricing, features, or technical requirements
  - Content research and analysis
- **Implementation**: Combines web fetching with AI analysis using queryQuick

### 3. System Execution Tools

#### BashTool
- **Purpose**: Execute shell commands
- **Key Features**:
  - Persistent shell sessions
  - Working directory management
  - Environment variable handling
  - Timeout support (default 2 minutes)
  - Output streaming
- **Security**: 
  - Command approval in safe mode
  - Restricted commands blacklist
  - Environment sanitization

### 4. AI Enhancement Tools

#### TaskTool (Architect)
- **Purpose**: Launch sub-agents for complex tasks
- **Key Features**:
  - Autonomous multi-step execution
  - Specialized agent types
  - Context preservation
  - Parallel task execution
- **Use Cases**: Complex refactoring, system design

#### ThinkTool
- **Purpose**: Allow AI to reason through problems
- **Key Features**:
  - Structured thinking blocks
  - Problem decomposition
  - Hidden from user output
- **Implementation**: Special message formatting

#### TodoWriteTool
- **Purpose**: Task management and tracking
- **Key Features**:
  - Persistent todo lists
  - Status tracking (pending, in_progress, completed)
  - Progress visualization
  - Automatic task breakdown

### 5. External Integration Tools

#### MCPTool
- **Purpose**: Bridge to Model Context Protocol servers
- **Key Features**:
  - Dynamic tool discovery
  - Protocol translation
  - Server lifecycle management
  - Error propagation
- **Implementation**: JSON-RPC over stdio/SSE

## Tool Implementation Guide

### Creating a New Tool

```typescript
export class MyCustomTool extends Tool {
  name = 'my_custom_tool'
  description = 'Does something custom'
  
  inputSchema = z.object({
    param1: z.string(),
    param2: z.number().optional()
  })
  
  needsPermissions(input: unknown): boolean {
    // Return true if this operation needs user approval
    return true
  }
  
  async *call(
    input: z.infer<typeof this.inputSchema>,
    context: ToolUseContext
  ): AsyncGenerator<ToolCallEvent> {
    // Yield progress updates
    yield {
      type: 'progress',
      message: 'Starting operation...'
    }
    
    // Check abort signal
    if (context.abortSignal.aborted) {
      throw new Error('Operation cancelled')
    }
    
    // Perform operation
    const result = await this.performOperation(input)
    
    // Yield final result
    yield {
      type: 'result',
      result: result
    }
  }
  
  renderResultForAssistant(input: unknown, result: unknown): string {
    // Format result for AI consumption
    return `Operation completed: ${JSON.stringify(result)}`
  }
}
```

### Tool Registration

```typescript
// In tools.ts
export async function getTools(): Promise<Tool[]> {
  const tools = [
    new FileReadTool(),
    new FileEditTool(),
    new BashTool(),
    new MyCustomTool(), // Add your tool here
    // ... other tools
  ]
  
  // Add MCP tools dynamically
  const mcpTools = await getMCPTools()
  tools.push(...mcpTools)
  
  return tools
}
```

## Permission System Integration

### Permission Types

1. **No Permission Required**: Read-only operations
2. **Session Permission**: Temporary approval for current session
3. **Persistent Permission**: Saved approval for future use
4. **Always Ask**: Critical operations requiring explicit approval

### Permission Flow

```typescript
async function checkPermissionsAndCallTool(
  tool: Tool,
  input: unknown,
  context: ToolUseContext
): Promise<ToolResult> {
  if (!tool.needsPermissions(input)) {
    // No permission needed
    return await tool.call(input, context)
  }
  
  const permission = await requestPermission({
    tool: tool.name,
    operation: describeOperation(input)
  })
  
  if (permission.approved) {
    if (permission.saveForSession) {
      saveSessionPermission(tool.name, input)
    }
    return await tool.call(input, context)
  } else {
    throw new PermissionDeniedError()
  }
}
```

## Tool Context

### ToolUseContext Interface

```typescript
interface ToolUseContext {
  // Cancellation support
  abortSignal: AbortSignal
  
  // Current working directory
  cwd: string
  
  // Permission helpers
  hasPermission: (operation: string) => boolean
  requestPermission: (operation: string) => Promise<boolean>
  
  // Logging and metrics
  logEvent: (event: string, data: any) => void
  
  // UI helpers
  showProgress: (message: string) => void
  
  // Configuration access
  config: Configuration
}
```

## Tool Best Practices

### 1. Input Validation
- Use Zod schemas for type-safe validation
- Provide clear error messages for invalid input
- Validate file paths and command arguments

### 2. Error Handling
- Throw descriptive errors with actionable messages
- Handle common failure cases gracefully
- Provide recovery suggestions

### 3. Progress Reporting
- Yield progress updates for long operations
- Include percentage or step information
- Update at reasonable intervals (not too frequent)

### 4. Cancellation Support
- Check abort signal regularly
- Clean up resources on cancellation
- Save partial progress when possible

### 5. Result Formatting
- Provide human-readable output for users
- Include structured data for AI parsing
- Summarize large results appropriately

### 6. Security Considerations
- Always validate and sanitize inputs
- Check permissions before operations
- Limit resource consumption
- Prevent path traversal attacks

## Tool Testing

### Unit Testing

```typescript
describe('MyCustomTool', () => {
  it('should validate input correctly', () => {
    const tool = new MyCustomTool()
    const validInput = { param1: 'test' }
    expect(() => tool.validateInput(validInput)).not.toThrow()
  })
  
  it('should handle cancellation', async () => {
    const tool = new MyCustomTool()
    const abortController = new AbortController()
    abortController.abort()
    
    const context = {
      abortSignal: abortController.signal,
      // ... other context
    }
    
    await expect(
      tool.call(input, context)
    ).rejects.toThrow('Operation cancelled')
  })
})
```

### Integration Testing

```typescript
it('should integrate with permission system', async () => {
  const tool = new MyCustomTool()
  const context = createTestContext({
    permissions: ['my_custom_tool']
  })
  
  const result = await tool.call(input, context)
  expect(result).toBeDefined()
})
```

## Advanced Tool Patterns

### Composite Tools
Tools that orchestrate multiple other tools:

```typescript
class CompositeAnalysisTool extends Tool {
  async *call(input, context) {
    // First, search for files
    const files = await this.globTool.call(
      { pattern: input.pattern },
      context
    )
    
    // Then grep each file
    for (const file of files) {
      const results = await this.grepTool.call(
        { file, pattern: input.search },
        context
      )
      yield { type: 'progress', file, results }
    }
  }
}
```

### Streaming Tools
Tools that process data incrementally:

```typescript
class StreamingFileTool extends Tool {
  async *call(input, context) {
    const stream = createReadStream(input.file)
    
    for await (const chunk of stream) {
      const processed = processChunk(chunk)
      yield { type: 'partial', data: processed }
      
      if (context.abortSignal.aborted) break
    }
    
    yield { type: 'complete' }
  }
}
```

### Stateful Tools
Tools that maintain state across calls:

```typescript
class SessionTool extends Tool {
  private session: Session
  
  async *call(input, context) {
    if (!this.session) {
      this.session = await createSession()
    }
    
    const result = await this.session.execute(input.command)
    yield { type: 'result', result }
  }
  
  cleanup() {
    this.session?.close()
  }
}
```

## Tool Metrics and Monitoring

### Performance Tracking

```typescript
class InstrumentedTool extends Tool {
  async *call(input, context) {
    const startTime = Date.now()
    
    try {
      yield* super.call(input, context)
    } finally {
      const duration = Date.now() - startTime
      context.logEvent('tool_execution', {
        tool: this.name,
        duration,
        success: true
      })
    }
  }
}
```

### Error Tracking

```typescript
class MonitoredTool extends Tool {
  async *call(input, context) {
    try {
      yield* super.call(input, context)
    } catch (error) {
      context.logEvent('tool_error', {
        tool: this.name,
        error: error.message,
        stack: error.stack
      })
      throw error
    }
  }
}
```

The Tool System provides the foundation for all of Kode's capabilities, enabling safe, efficient, and extensible operations while maintaining a consistent interface for both AI and human users.