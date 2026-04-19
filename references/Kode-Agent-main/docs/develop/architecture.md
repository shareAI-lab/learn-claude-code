# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   CLI Entry │  │     REPL     │  │  React/Ink UI    │  │
│  │  (cli.tsx)  │  │  (REPL.tsx)  │  │   Components     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Command & Control Layer                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Commands  │  │    Query     │  │     Context      │  │
│  │  (Slash /)  │  │  Engine      │  │   Management     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Tool Execution Layer                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ File Tools  │  │ System Tools │  │    AI Tools      │  │
│  │ (R/W/Edit)  │  │ (Bash/Grep)  │  │ (Task/Think)     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Service Integration Layer                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ AI Providers│  │  MCP Servers │  │  External APIs   │  │
│  │(Claude/GPT) │  │ (stdio/SSE)  │  │  (Git/Sentry)    │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │Configuration│  │  Permissions │  │    Logging &     │  │
│  │  Management │  │    System    │  │   Error Handling │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Relationships

### Data Flow Architecture

```
User Input → Command Parser → Route Decision
                                    ↓
                          ┌─────────────────────┐
                          │   Slash Command?    │
                          └─────────────────────┘
                                    ↓
                    Yes ←───────────┼───────────→ No
                     ↓                              ↓
            ┌──────────────┐              ┌──────────────┐
            │Command Handler│              │ AI Query     │
            └──────────────┘              └──────────────┘
                     ↓                              ↓
            ┌──────────────┐              ┌──────────────┐
            │   Execute    │              │Tool Selection│
            └──────────────┘              └──────────────┘
                     ↓                              ↓
            ┌──────────────┐              ┌──────────────┐
            │Return Result │              │Tool Execution│
            └──────────────┘              └──────────────┘
                     ↓                              ↓
                     └──────────┬──────────────────┘
                                ↓
                        ┌──────────────┐
                        │Render Response│
                        └──────────────┘
```

### Module Dependency Graph

```
cli.tsx (Entry Point)
    ├── REPL.tsx (Interactive Mode)
    │   ├── PromptInput.tsx
    │   ├── MessageResponse.tsx
    │   └── query.ts (AI Orchestration)
    │       ├── tools.ts (Tool Registry)
    │       │   ├── BashTool
    │       │   ├── FileEditTool
    │       │   ├── GrepTool
    │       │   └── [Other Tools]
    │       ├── permissions.ts
    │       └── context.ts
    ├── commands.ts (Command System)
    │   ├── Built-in Commands
    │   ├── MCP Commands
    │   └── Custom Commands
    └── services/
        ├── claude.ts
        ├── openai.ts
        ├── mcpClient.ts
        └── statsig.ts
```

## Core Module Interactions

### 1. Conversation Flow

```
User Prompt
    ↓
Context Injection (AGENTS.md, git status, etc.)
    ↓
Model Selection (based on context size)
    ↓
API Request with Tools
    ↓
Streaming Response
    ↓
Tool Use Detection
    ↓
Permission Check
    ↓
Tool Execution
    ↓
Result Integration
    ↓
Continue or Complete
```

### 2. Tool Execution Pipeline

```
AI Requests Tool Use
    ↓
Tool Validation (Zod Schema)
    ↓
Permission Check
    ├── Permissive Mode → Auto-approve safe operations
    └── Safe Mode → Request user permission
    ↓
Tool Execution (Async Generator)
    ├── Yield progress updates
    ├── Handle cancellation
    └── Return results
    ↓
Format Results for AI
    ↓
Continue Conversation
```

### 3. Configuration Cascade

```
Environment Variables
    ↓
Global Config (~/.claude/config.json)
    ↓
Project Config (./.claude/config.json)
    ↓
Runtime Overrides (CLI flags)
    ↓
Effective Configuration
```

### 4. MCP Server Integration

```
MCP Server Configuration
    ↓
Server Startup (stdio/SSE)
    ↓
Tool Discovery
    ↓
Dynamic Tool Registration
    ↓
Tool Available in Conversation
    ↓
Tool Execution via MCP Protocol
    ↓
Result Translation
```

## Key Architectural Decisions

### 1. Tool Abstraction
Every capability is a Tool implementing a standard interface:
```typescript
interface Tool {
  name: string
  description: string
  inputSchema: ZodSchema
  needsPermissions(): boolean
  call(): AsyncGenerator<ToolCallResult>
  renderResultForAssistant(): string
}
```

### 2. Streaming Architecture
All long-running operations use async generators:
- Enables real-time progress updates
- Supports cancellation at any point
- Allows incremental result display

### 3. React in Terminal
Using React with Ink for terminal UI:
- Component reusability
- State management
- Complex interactive UIs
- Consistent styling

### 4. Permission Layers
Multi-level permission system:
- **Tool Level**: Each tool declares permission needs
- **Session Level**: Temporary permissions for current session
- **Persistent Level**: Saved permissions across sessions
- **Mode Level**: Safe vs Permissive modes

### 5. Context Management
Automatic context injection:
- Project files (AGENTS.md, CLAUDE.md)
- Git status and recent commits
- Directory structure
- Previous conversation history

## Module Communication Patterns

### Event-Driven Updates
Components communicate through:
- React props and callbacks
- Abort signals for cancellation
- Progress generators for updates
- Event emitters for cross-cutting concerns

### Service Integration
External services accessed through:
- Dedicated service modules
- Unified error handling
- Retry logic with backoff
- Streaming response handling

### Configuration Access
Configuration accessed via:
- Singleton config manager
- Lazy loading on first access
- Automatic migration on version change
- Validation on load

## Security Architecture

### Permission Model
```
Request → Permission Check → Decision
             ↓                    ↓
    ┌──────────────┐      ┌──────────┐
    │  Check Cache │      │   Deny    │
    └──────────────┘      └──────────┘
             ↓
    ┌──────────────┐
    │ Check Session│
    └──────────────┘
             ↓
    ┌──────────────┐
    │  Ask User    │
    └──────────────┘
             ↓
    ┌──────────────┐
    │Cache Decision│
    └──────────────┘
```

### File System Security
- Directory-based access control
- Path traversal prevention
- Symbolic link resolution
- Hidden file protection

### Command Execution Security
- Command approval system
- Environment variable sanitization
- Working directory restrictions
- Output size limits

## Performance Considerations

### Caching Strategy
- Model responses cached in memory
- File reads cached with freshness checks
- Configuration cached per session
- MCP tool discovery cached

### Lazy Loading
- Commands loaded on first use
- MCP servers started on demand
- Context loaded incrementally
- Heavy dependencies loaded when needed

### Streaming Optimizations
- Chunked response processing
- Incremental rendering
- Partial result display
- Early termination support

## Extension Points

### Adding New Tools
1. Create class extending Tool
2. Implement required methods
3. Register in tools.ts
4. Tool automatically available

### Adding AI Providers
1. Implement provider interface
2. Add to ModelManager
3. Configure in model profiles
4. Provider available for use

### Adding Commands
1. Create command handler
2. Register in commands.ts
3. Command available via slash

### Adding MCP Servers
1. Configure server details
2. Server tools auto-discovered
3. Tools available in conversation

## System Boundaries

### Internal Boundaries
- Clear module interfaces
- Dependency injection
- Service abstractions
- Tool isolation

### External Boundaries
- API rate limiting
- File system access control
- Network request timeouts
- Resource consumption limits

## Scalability Considerations

### Horizontal Scalability
- Stateless command execution
- Independent tool operations
- Parallel tool execution (when safe)
- Distributed MCP servers

### Vertical Scalability
- Streaming for large responses
- Chunked file processing
- Incremental context loading
- Memory-efficient caching

This architecture provides a robust, extensible foundation for an AI-powered development assistant while maintaining security, performance, and user experience as primary concerns.