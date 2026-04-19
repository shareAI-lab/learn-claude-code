# MCP（模型上下文协议）集成

## 概述

MCP 集成模块（`src/services/mcpClient.ts`）使 Kode 能够通过模型上下文协议连接外部工具和服务。MCP 允许第三方开发者创建为 AI 助手提供额外功能的服务器。

## 架构

### MCP 客户端系统

```typescript
class MCPClientManager {
  private clients: Map<string, MCPClient> = new Map()
  private servers: Map<string, MCPServerConfig> = new Map()
  private tools: Map<string, MCPTool> = new Map()
  
  // 服务器生命周期
  async startServer(name: string, config: MCPServerConfig): Promise<void>
  async stopServer(name: string): Promise<void>
  async restartServer(name: string): Promise<void>
  
  // 工具发现
  async discoverTools(serverName: string): Promise<MCPTool[]>
  async refreshTools(): Promise<void>
  
  // 工具执行
  async executeTool(toolName: string, args: any): Promise<any>
}
```

## 服务器类型

### Stdio 服务器

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
    // 生成进程
    this.process = spawn(config.command, config.args, {
      env: { ...process.env, ...config.env },
      cwd: config.cwd,
      stdio: ['pipe', 'pipe', 'pipe']
    })
    
    // 创建传输
    this.transport = new StdioTransport(
      this.process.stdout,
      this.process.stdin
    )
    
    // 初始化客户端
    this.client = new Client(
      { name: 'kode', version: VERSION },
      { capabilities: {} }
    )
    
    // 连接
    await this.client.connect(this.transport)
    
    // 发现功能
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

### SSE 服务器

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
    // 创建 SSE 传输
    const headers = {
      ...config.headers,
      'Authorization': config.apiKey ? `Bearer ${config.apiKey}` : undefined
    }
    
    this.transport = new SSETransport(
      new URL(config.url),
      { headers }
    )
    
    // 初始化客户端
    this.client = new Client(
      { name: 'kode', version: VERSION },
      { capabilities: {} }
    )
    
    // 连接
    await this.client.connect(this.transport)
    
    // 设置事件处理器
    this.setupEventHandlers()
  }
  
  private setupEventHandlers(): void {
    this.client.on('notification', this.handleNotification.bind(this))
    this.client.on('error', this.handleError.bind(this))
    this.client.on('close', this.handleClose.bind(this))
  }
}
```

## 工具发现

### 工具注册

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
        console.error(`从 ${client.name} 发现工具失败：`, error)
      }
    }
  }
}
```

### 动态工具创建

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
    yield { type: 'progress', message: `调用 MCP 工具 ${this.definition.originalName}...` }
    
    try {
      // 通过 MCP 执行
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: this.definition.originalName,
          arguments: input
        }
      })
      
      // 处理流式响应
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
    // MCP 工具在安全模式下始终需要权限
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

## 服务器管理

### 配置存储

```typescript
interface MCPServerStore {
  global: Record<string, MCPServerConfig>
  project: Record<string, MCPServerConfig>
  mcprc?: Record<string, MCPServerConfig>  // 来自 .mcprc 文件
}

class MCPConfigManager {
  private store: MCPServerStore
  
  async loadConfigurations(): Promise<void> {
    // 加载全局配置
    this.store.global = await this.loadGlobalConfig()
    
    // 加载项目配置
    this.store.project = await this.loadProjectConfig()
    
    // 加载 .mcprc 文件
    this.store.mcprc = await this.loadMcprcFiles()
    
    // 合并配置
    this.mergeConfigurations()
  }
  
  private async loadMcprcFiles(): Promise<Record<string, MCPServerConfig>> {
    const configs: Record<string, MCPServerConfig> = {}
    
    // 搜索 .mcprc 文件
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

### 服务器生命周期

```typescript
class MCPServerLifecycle {
  private servers: Map<string, MCPServerInstance> = new Map()
  
  async startServer(
    name: string,
    config: MCPServerConfig
  ): Promise<void> {
    if (this.servers.has(name)) {
      throw new Error(`服务器 ${name} 已在运行`)
    }
    
    const instance = await this.createServerInstance(config)
    
    try {
      await instance.start()
      this.servers.set(name, instance)
      
      // 发现工具
      await this.discoverServerTools(name, instance)
      
      // 监控健康状态
      this.monitorServerHealth(name, instance)
      
    } catch (error) {
      await instance.cleanup()
      throw new Error(`启动服务器 ${name} 失败：${error.message}`)
    }
  }
  
  async stopServer(name: string): Promise<void> {
    const instance = this.servers.get(name)
    if (!instance) {
      throw new Error(`服务器 ${name} 未运行`)
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
        console.error(`服务器 ${name} 健康检查失败：`, error)
        
        // 尝试重启
        try {
          await this.restartServer(name)
        } catch (restartError) {
          console.error(`重启服务器 ${name} 失败：`, restartError)
          clearInterval(healthCheck)
        }
      }
    }, 30000) // 每 30 秒检查一次
    
    instance.on('close', () => clearInterval(healthCheck))
  }
}
```

## 服务器批准系统

### 项目范围批准

```typescript
class MCPServerApproval {
  private approved: Set<string> = new Set()
  private rejected: Set<string> = new Set()
  
  async checkApproval(
    serverName: string,
    config: MCPServerConfig
  ): Promise<boolean> {
    // 检查是否已批准/拒绝
    if (this.approved.has(serverName)) return true
    if (this.rejected.has(serverName)) return false
    
    // 检查是否来自受信任的源
    if (this.isTrustedServer(serverName, config)) {
      this.approved.add(serverName)
      return true
    }
    
    // 询问用户批准
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
      message: `批准 MCP 服务器 "${serverName}" 吗？`,
      choices: [
        { key: 'y', name: '是，为此会话批准', value: { approved: true, remember: false } },
        { key: 'a', name: '始终为此项目批准', value: { approved: true, remember: true } },
        { key: 'n', name: '否，为此会话拒绝', value: { approved: false, remember: false } },
        { key: 'r', name: '始终为此项目拒绝', value: { approved: false, remember: true } },
        { key: 'd', name: '查看详情', value: 'details' }
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

## 协议实现

### JSON-RPC 通信

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
      
      // 设置超时
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id)
        reject(new Error(`请求 ${id} 超时`))
      }, 30000)
      
      // 发送消息
      this.transport.send(message)
      
      // 存储超时以便清理
      this.pendingRequests.get(id)!.timeout = timeout
    })
  }
  
  handleResponse(message: JSONRPCResponse): void {
    const pending = this.pendingRequests.get(message.id)
    if (!pending) {
      console.warn(`收到未知请求 ${message.id} 的响应`)
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

### 传输层

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

## 集成示例

### Claude Desktop 导入

```typescript
class ClaudeDesktopImporter {
  async importServers(): Promise<ImportResult> {
    const configPath = this.getClaudeDesktopConfigPath()
    
    if (!existsSync(configPath)) {
      throw new Error('未找到 Claude Desktop 配置')
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
        console.error(`导入 ${name} 失败：`, error)
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
        throw new Error(`不支持的平台：${process.platform}`)
    }
  }
}
```

MCP 集成通过标准化协议通信提供强大的可扩展性，实现与第三方工具和服务的无缝集成，同时通过批准系统和错误处理保持安全性。