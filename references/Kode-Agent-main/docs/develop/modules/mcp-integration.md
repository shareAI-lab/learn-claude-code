# MCP (Model Context Protocol) Integration

## Overview

The MCP Integration module (`src/services/mcpClient.ts`) enables Kode to connect with external tools and services through the Model Context Protocol. MCP allows third-party developers to create servers that provide additional capabilities to AI assistants.

## Architecture

### MCP Client System

```typescript
class MCPClientManager {
  private clients: Map<string, MCPClient> = new Map()
  private servers: Map<string, MCPServerConfig> = new Map()
  private tools: Map<string, MCPTool> = new Map()
  
  // Server lifecycle
  async startServer(name: string, config: MCPServerConfig): Promise<void>
  async stopServer(name: string): Promise<void>
  async restartServer(name: string): Promise<void>
  
  // Tool discovery
  async discoverTools(serverName: string): Promise<MCPTool[]>
  async refreshTools(): Promise<void>
  
  // Tool execution
  async executeTool(toolName: string, args: any): Promise<any>
}
```

## Server Types

### Stdio Server

```typescript
interface StdioServerConfig {
  type: 'stdio'
  command: string
  args: string[]
  env?: Record<string, string>
  cwd?: string
}

class StdioMCPClient implements MCPClient {
  private process: ChildProcess
  private transport: StdioTransport
  private client: Client
  
  async start(config: StdioServerConfig): Promise<void> {
    // Spawn process
    this.process = spawn(config.command, config.args, {
      env: { ...process.env, ...config.env },
      cwd: config.cwd,
      stdio: ['pipe', 'pipe', 'pipe']
    })
    
    // Create transport
    this.transport = new StdioTransport(
      this.process.stdout,
      this.process.stdin
    )
    
    // Initialize client
    this.client = new Client(
      { name: 'kode', version: VERSION },
      { capabilities: {} }
    )
    
    // Connect
    await this.client.connect(this.transport)
    
    // Discover capabilities
    await this.discoverCapabilities()
  }
  
  async discoverCapabilities(): Promise<void> {
    const response = await this.client.request({
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {
          roots: { listChanged: true },
          sampling: {}
        },
        clientInfo: {
          name: 'kode',
          version: VERSION
        }
      }
    })
    
    this.capabilities = response.capabilities
    this.serverInfo = response.serverInfo
  }
}
```

### SSE Server

```typescript
interface SSEServerConfig {
  type: 'sse'
  url: string
  headers?: Record<string, string>
  apiKey?: string
}

class SSEMCPClient implements MCPClient {
  private transport: SSETransport
  private client: Client
  private eventSource: EventSource
  
  async start(config: SSEServerConfig): Promise<void> {
    // Create SSE transport
    const headers = {
      ...config.headers,
      'Authorization': config.apiKey ? `Bearer ${config.apiKey}` : undefined
    }
    
    this.transport = new SSETransport(
      new URL(config.url),
      { headers }
    )
    
    // Initialize client
    this.client = new Client(
      { name: 'kode', version: VERSION },
      { capabilities: {} }
    )
    
    // Connect
    await this.client.connect(this.transport)
    
    // Setup event handlers
    this.setupEventHandlers()
  }
  
  private setupEventHandlers(): void {
    this.client.on('notification', this.handleNotification.bind(this))
    this.client.on('error', this.handleError.bind(this))
    this.client.on('close', this.handleClose.bind(this))
  }
}
```

## Tool Discovery

### Tool Registration

```typescript
class MCPToolRegistry {
  private tools: Map<string, MCPToolDefinition> = new Map()
  
  async discoverTools(client: MCPClient): Promise<MCPToolDefinition[]> {
    const response = await client.request({
      method: 'tools/list'
    })
    
    const tools: MCPToolDefinition[] = []
    
    for (const tool of response.tools) {
      const definition: MCPToolDefinition = {
        name: `mcp_${client.name}_${tool.name}`,
        description: tool.description,
        inputSchema: tool.inputSchema,
        serverName: client.name,
        originalName: tool.name
      }
      
      tools.push(definition)
      this.tools.set(definition.name, definition)
    }
    
    return tools
  }
  
  async refreshAllTools(): Promise<void> {
    this.tools.clear()
    
    const clients = await this.getActiveClients()
    
    for (const client of clients) {
      try {
        await this.discoverTools(client)
      } catch (error) {
        console.error(`Failed to discover tools from ${client.name}:`, error)
      }
    }
  }
}
```

### Dynamic Tool Creation

```typescript
class MCPToolAdapter extends Tool {
  constructor(
    private definition: MCPToolDefinition,
    private client: MCPClient
  ) {
    super()
    this.name = definition.name
    this.description = definition.description
    this.inputSchema = this.convertSchema(definition.inputSchema)
  }
  
  async *call(
    input: unknown,
    context: ToolUseContext
  ): AsyncGenerator<ToolCallEvent> {
    yield { type: 'progress', message: `Calling MCP tool ${this.definition.originalName}...` }
    
    try {
      // Execute via MCP
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: this.definition.originalName,
          arguments: input
        }
      })
      
      // Handle streaming responses
      if (response.stream) {
        yield* this.handleStreamingResponse(response.stream)
      } else {
        yield { type: 'result', result: response.content }
      }
      
    } catch (error) {
      yield { type: 'error', error: this.formatError(error) }
    }
  }
  
  private async *handleStreamingResponse(
    stream: AsyncIterable<any>
  ): AsyncGenerator<ToolCallEvent> {
    for await (const chunk of stream) {
      if (chunk.type === 'text') {
        yield { type: 'partial', content: chunk.text }
      } else if (chunk.type === 'error') {
        yield { type: 'error', error: chunk.error }
      }
    }
  }
  
  needsPermissions(input: unknown): boolean {
    // MCP tools always require permission in safe mode
    return true
  }
  
  renderResultForAssistant(input: unknown, result: unknown): string {
    if (typeof result === 'string') {
      return result
    }
    return JSON.stringify(result, null, 2)
  }
}
```

## Server Management

### Configuration Storage

```typescript
interface MCPServerStore {
  global: Record<string, MCPServerConfig>
  project: Record<string, MCPServerConfig>
  mcprc?: Record<string, MCPServerConfig>  // From .mcprc files
}

class MCPConfigManager {
  private store: MCPServerStore
  
  async loadConfigurations(): Promise<void> {
    // Load global config
    this.store.global = await this.loadGlobalConfig()
    
    // Load project config
    this.store.project = await this.loadProjectConfig()
    
    // Load .mcprc files
    this.store.mcprc = await this.loadMcprcFiles()
    
    // Merge configurations
    this.mergeConfigurations()
  }
  
  private async loadMcprcFiles(): Promise<Record<string, MCPServerConfig>> {
    const configs: Record<string, MCPServerConfig> = {}
    
    // Search for .mcprc files
    const mcprcPaths = [
      path.join(process.cwd(), '.mcprc'),
      path.join(process.cwd(), '.mcp.json'),
      path.join(homedir(), '.mcprc')
    ]
    
    for (const mcprcPath of mcprcPaths) {
      if (existsSync(mcprcPath)) {
        const content = await fs.readFile(mcprcPath, 'utf-8')
        const parsed = JSON.parse(content)
        
        if (parsed.mcpServers) {
          Object.assign(configs, parsed.mcpServers)
        }
      }
    }
    
    return configs
  }
  
  addServer(
    name: string,
    config: MCPServerConfig,
    scope: 'global' | 'project'
  ): void {
    this.store[scope][name] = config
    this.saveConfiguration(scope)
  }
  
  removeServer(
    name: string,
    scope: 'global' | 'project' | 'mcprc'
  ): void {
    delete this.store[scope][name]
    if (scope !== 'mcprc') {
      this.saveConfiguration(scope)
    }
  }
}
```

### Server Lifecycle

```typescript
class MCPServerLifecycle {
  private servers: Map<string, MCPServerInstance> = new Map()
  
  async startServer(
    name: string,
    config: MCPServerConfig
  ): Promise<void> {
    if (this.servers.has(name)) {
      throw new Error(`Server ${name} is already running`)
    }
    
    const instance = await this.createServerInstance(config)
    
    try {
      await instance.start()
      this.servers.set(name, instance)
      
      // Discover tools
      await this.discoverServerTools(name, instance)
      
      // Monitor health
      this.monitorServerHealth(name, instance)
      
    } catch (error) {
      await instance.cleanup()
      throw new Error(`Failed to start server ${name}: ${error.message}`)
    }
  }
  
  async stopServer(name: string): Promise<void> {
    const instance = this.servers.get(name)
    if (!instance) {
      throw new Error(`Server ${name} is not running`)
    }
    
    try {
      await instance.stop()
    } finally {
      this.servers.delete(name)
      await instance.cleanup()
    }
  }
  
  private monitorServerHealth(
    name: string,
    instance: MCPServerInstance
  ): void {
    const healthCheck = setInterval(async () => {
      try {
        await instance.ping()
      } catch (error) {
        console.error(`Server ${name} health check failed:`, error)
        
        // Attempt restart
        try {
          await this.restartServer(name)
        } catch (restartError) {
          console.error(`Failed to restart server ${name}:`, restartError)
          clearInterval(healthCheck)
        }
      }
    }, 30000) // Check every 30 seconds
    
    instance.on('close', () => clearInterval(healthCheck))
  }
}
```

## Server Approval System

### Project-Scoped Approval

```typescript
class MCPServerApproval {
  private approved: Set<string> = new Set()
  private rejected: Set<string> = new Set()
  
  async checkApproval(
    serverName: string,
    config: MCPServerConfig
  ): Promise<boolean> {
    // Check if already approved/rejected
    if (this.approved.has(serverName)) return true
    if (this.rejected.has(serverName)) return false
    
    // Check if from trusted source
    if (this.isTrustedServer(serverName, config)) {
      this.approved.add(serverName)
      return true
    }
    
    // Ask user for approval
    const approval = await this.promptUserApproval(serverName, config)
    
    if (approval.approved) {
      this.approved.add(serverName)
      if (approval.remember) {
        await this.saveApproval(serverName)
      }
    } else {
      this.rejected.add(serverName)
      if (approval.remember) {
        await this.saveRejection(serverName)
      }
    }
    
    return approval.approved
  }
  
  private async promptUserApproval(
    serverName: string,
    config: MCPServerConfig
  ): Promise<ApprovalResult> {
    const details = this.getServerDetails(config)
    
    return await prompt({
      type: 'expand',
      message: `Approve MCP server "${serverName}"?`,
      choices: [
        { key: 'y', name: 'Yes, approve for this session', value: { approved: true, remember: false } },
        { key: 'a', name: 'Always approve for this project', value: { approved: true, remember: true } },
        { key: 'n', name: 'No, reject for this session', value: { approved: false, remember: false } },
        { key: 'r', name: 'Always reject for this project', value: { approved: false, remember: true } },
        { key: 'd', name: 'View details', value: 'details' }
      ],
      default: 'y'
    })
  }
  
  private isTrustedServer(
    name: string,
    config: MCPServerConfig
  ): boolean {
    const trustedCommands = [
      '@modelcontextprotocol/server-filesystem',
      '@modelcontextprotocol/server-github',
      '@modelcontextprotocol/server-postgres'
    ]
    
    if (config.type === 'stdio') {
      return trustedCommands.some(cmd => 
        config.command.includes(cmd) || 
        config.args?.some(arg => arg.includes(cmd))
      )
    }
    
    return false
  }
}
```

## Protocol Implementation

### JSON-RPC Communication

```typescript
class MCPProtocol {
  private messageId: number = 0
  private pendingRequests: Map<number, PendingRequest> = new Map()
  
  async request(
    method: string,
    params?: any
  ): Promise<any> {
    const id = ++this.messageId
    
    const message: JSONRPCRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params
    }
    
    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject })
      
      // Set timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id)
        reject(new Error(`Request ${id} timed out`))
      }, 30000)
      
      // Send message
      this.transport.send(message)
      
      // Store timeout for cleanup
      this.pendingRequests.get(id)!.timeout = timeout
    })
  }
  
  handleResponse(message: JSONRPCResponse): void {
    const pending = this.pendingRequests.get(message.id)
    if (!pending) {
      console.warn(`Received response for unknown request ${message.id}`)
      return
    }
    
    clearTimeout(pending.timeout)
    this.pendingRequests.delete(message.id)
    
    if (message.error) {
      pending.reject(new MCPError(message.error))
    } else {
      pending.resolve(message.result)
    }
  }
  
  handleNotification(message: JSONRPCNotification): void {
    this.emit('notification', {
      method: message.method,
      params: message.params
    })
  }
}
```

### Transport Layer

```typescript
abstract class Transport {
  abstract send(message: any): Promise<void>
  abstract close(): Promise<void>
  
  protected emit(event: string, data: any): void
  
  on(event: string, handler: (data: any) => void): void
  off(event: string, handler: (data: any) => void): void
}

class StdioTransport extends Transport {
  constructor(
    private stdout: Readable,
    private stdin: Writable
  ) {
    super()
    this.setupStreams()
  }
  
  private setupStreams(): void {
    const parser = new MessageParser()
    
    this.stdout.pipe(parser)
    
    parser.on('message', (message) => {
      this.emit('message', message)
    })
    
    parser.on('error', (error) => {
      this.emit('error', error)
    })
  }
  
  async send(message: any): Promise<void> {
    const serialized = JSON.stringify(message)
    const frame = `Content-Length: ${Buffer.byteLength(serialized)}\r\n\r\n${serialized}`
    
    return new Promise((resolve, reject) => {
      this.stdin.write(frame, (error) => {
        if (error) reject(error)
        else resolve()
      })
    })
  }
  
  async close(): Promise<void> {
    this.stdin.end()
    this.stdout.destroy()
  }
}
```

## Resource Management

### Resource Discovery

```typescript
class MCPResourceManager {
  async listResources(client: MCPClient): Promise<Resource[]> {
    const response = await client.request({
      method: 'resources/list'
    })
    
    return response.resources.map(r => ({
      uri: r.uri,
      name: r.name,
      description: r.description,
      mimeType: r.mimeType
    }))
  }
  
  async readResource(
    client: MCPClient,
    uri: string
  ): Promise<ResourceContent> {
    const response = await client.request({
      method: 'resources/read',
      params: { uri }
    })
    
    return {
      uri: response.contents[0].uri,
      mimeType: response.contents[0].mimeType,
      text: response.contents[0].text,
      blob: response.contents[0].blob
    }
  }
  
  async subscribeToResource(
    client: MCPClient,
    uri: string,
    handler: (update: ResourceUpdate) => void
  ): Promise<() => void> {
    await client.request({
      method: 'resources/subscribe',
      params: { uri }
    })
    
    const listener = (notification: Notification) => {
      if (notification.method === 'resources/updated' &&
          notification.params.uri === uri) {
        handler(notification.params)
      }
    }
    
    client.on('notification', listener)
    
    // Return unsubscribe function
    return async () => {
      await client.request({
        method: 'resources/unsubscribe',
        params: { uri }
      })
      client.off('notification', listener)
    }
  }
}
```

## Prompt Management

### MCP Prompts

```typescript
class MCPPromptManager {
  async listPrompts(client: MCPClient): Promise<Prompt[]> {
    const response = await client.request({
      method: 'prompts/list'
    })
    
    return response.prompts.map(p => ({
      name: p.name,
      description: p.description,
      arguments: p.arguments
    }))
  }
  
  async getPrompt(
    client: MCPClient,
    name: string,
    args?: Record<string, any>
  ): Promise<PromptContent> {
    const response = await client.request({
      method: 'prompts/get',
      params: {
        name,
        arguments: args
      }
    })
    
    return {
      messages: response.messages,
      description: response.description
    }
  }
  
  async createCommandFromPrompt(
    client: MCPClient,
    prompt: Prompt
  ): Command {
    return {
      name: `mcp_${client.name}_${prompt.name}`,
      description: prompt.description,
      type: 'prompt',
      isEnabled: true,
      isHidden: false,
      userFacingName: () => `mcp:${prompt.name}`,
      
      async getPromptForCommand(args: string): Promise<MessageParam[]> {
        const parsedArgs = this.parseArguments(args, prompt.arguments)
        const content = await this.getPrompt(client, prompt.name, parsedArgs)
        
        return content.messages.map(msg => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content
        }))
      }
    }
  }
}
```

## Error Handling

### MCP Error Types

```typescript
class MCPError extends Error {
  constructor(
    public code: number,
    message: string,
    public data?: any
  ) {
    super(message)
    this.name = 'MCPError'
  }
  
  static fromJSONRPCError(error: JSONRPCError): MCPError {
    return new MCPError(error.code, error.message, error.data)
  }
}

class MCPConnectionError extends Error {
  constructor(
    message: string,
    public serverName: string,
    public cause?: Error
  ) {
    super(message)
    this.name = 'MCPConnectionError'
  }
}

class MCPTimeoutError extends Error {
  constructor(
    public method: string,
    public timeout: number
  ) {
    super(`MCP request '${method}' timed out after ${timeout}ms`)
    this.name = 'MCPTimeoutError'
  }
}
```

### Error Recovery

```typescript
class MCPErrorRecovery {
  async handleError(
    error: Error,
    client: MCPClient,
    operation: () => Promise<any>
  ): Promise<any> {
    if (error instanceof MCPConnectionError) {
      // Attempt reconnection
      await this.reconnect(client)
      return operation()
    }
    
    if (error instanceof MCPTimeoutError) {
      // Retry with longer timeout
      return this.retryWithTimeout(operation, error.timeout * 2)
    }
    
    if (error.message.includes('rate limit')) {
      // Apply backoff
      await this.applyBackoff()
      return operation()
    }
    
    // Unrecoverable error
    throw error
  }
  
  private async reconnect(client: MCPClient): Promise<void> {
    console.log(`Attempting to reconnect to ${client.name}...`)
    
    await client.close()
    await sleep(1000)
    await client.connect()
    
    console.log(`Successfully reconnected to ${client.name}`)
  }
}
```

## Integration Examples

### Claude Desktop Import

```typescript
class ClaudeDesktopImporter {
  async importServers(): Promise<ImportResult> {
    const configPath = this.getClaudeDesktopConfigPath()
    
    if (!existsSync(configPath)) {
      throw new Error('Claude Desktop configuration not found')
    }
    
    const config = JSON.parse(
      await fs.readFile(configPath, 'utf-8')
    )
    
    const imported: string[] = []
    const failed: string[] = []
    
    for (const [name, serverConfig] of Object.entries(config.mcpServers || {})) {
      try {
        await this.importServer(name, serverConfig as any)
        imported.push(name)
      } catch (error) {
        console.error(`Failed to import ${name}:`, error)
        failed.push(name)
      }
    }
    
    return { imported, failed }
  }
  
  private getClaudeDesktopConfigPath(): string {
    switch (process.platform) {
      case 'darwin':
        return path.join(
          homedir(),
          'Library/Application Support/Claude/claude_desktop_config.json'
        )
      case 'win32':
        return path.join(
          process.env.APPDATA || '',
          'Claude/claude_desktop_config.json'
        )
      case 'linux':
        return path.join(
          homedir(),
          '.config/Claude/claude_desktop_config.json'
        )
      default:
        throw new Error(`Unsupported platform: ${process.platform}`)
    }
  }
}
```

The MCP Integration provides powerful extensibility through standardized protocol communication, enabling seamless integration with third-party tools and services while maintaining security through approval systems and error handling.