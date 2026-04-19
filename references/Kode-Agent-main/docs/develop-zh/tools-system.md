# 工具系统文档

## 概述

工具系统是 Kode 功能的核心，为 AI 可以执行的所有操作提供标准化接口。每个功能 - 从读取文件到执行命令 - 都作为工具实现。

## 工具接口

### 核心工具类

```typescript
export abstract class Tool {
  abstract name: string
  abstract description: string
  abstract inputSchema: z.ZodTypeAny
  
  // 权限检查
  abstract needsPermissions(input: unknown): boolean
  
  // 输入验证
  validateInput(input: unknown): unknown
  
  // 主执行方法
  abstract call(
    input: unknown, 
    context: ToolUseContext
  ): AsyncGenerator<ToolCallEvent>
  
  // 为 AI 格式化结果
  abstract renderResultForAssistant(
    input: unknown,
    result: unknown
  ): string
}
```

### 工具生命周期

```
1. 工具注册
   ↓
2. AI 请求工具使用
   ↓
3. 输入验证 (Zod Schema)
   ↓
4. 权限检查
   ↓
5. 用户批准（如需要）
   ↓
6. 工具执行
   ↓
7. 进度更新（通过生成器）
   ↓
8. 结果格式化
   ↓
9. 返回给 AI
```

## 工具类别

### 1. 文件操作工具

#### FileReadTool（文件读取工具）
- **用途**：读取带编码检测的文件内容
- **主要功能**：
  - 自动编码检测（UTF-8、UTF-16 等）
  - 二进制文件处理
  - 支持带偏移/限制的大文件
  - 新鲜度跟踪以检测外部更改
- **安全性**：检查文件访问权限

#### FileEditTool（文件编辑工具）
- **用途**：对现有文件进行精确编辑
- **主要功能**：
  - 精确匹配的字符串替换
  - 文件新鲜度验证
  - 防止在未读取前编辑
  - 多重编辑支持（MultiEditTool）
- **安全性**：需要文件写入权限

#### FileWriteTool（文件写入工具）
- **用途**：创建或覆盖整个文件
- **主要功能**：
  - 完整文件替换
  - 如需要创建目录
  - 编码规范
- **安全性**：需要明确的写入权限

#### NotebookEditTool（笔记本编辑工具）
- **用途**：编辑 Jupyter 笔记本单元格
- **主要功能**：
  - 单元格级操作（替换、插入、删除）
  - 代码和 markdown 单元格支持
  - 保留笔记本元数据

### 2. 搜索和发现工具

#### GrepTool（搜索工具）
- **用途**：使用正则表达式搜索文件内容
- **主要功能**：
  - Ripgrep 集成以提高速度
  - 多种输出模式（内容、文件、计数）
  - 上下文行支持（-A、-B、-C）
  - 文件类型过滤
- **实现**：使用 ripgrep 二进制文件以提高性能

#### GlobTool（文件匹配工具）
- **用途**：按名称模式查找文件
- **主要功能**：
  - Glob 模式匹配
  - 隐藏文件支持
  - 按修改时间排序结果
  - 符号链接跟随选项

#### LSTool（列表工具）
- **用途**：列出目录内容
- **主要功能**：
  - 递归列表
  - 隐藏文件显示
  - 大小和权限信息
  - 模式过滤

### 3. 系统执行工具

#### BashTool（Shell 工具）
- **用途**：执行 shell 命令
- **主要功能**：
  - 持久 shell 会话
  - 工作目录管理
  - 环境变量处理
  - 超时支持（默认 2 分钟）
  - 输出流式传输
- **安全性**：
  - 安全模式下的命令批准
  - 受限命令黑名单
  - 环境清理

### 4. AI 增强工具

#### TaskTool（任务工具/架构师）
- **用途**：为复杂任务启动子代理
- **主要功能**：
  - 自主多步骤执行
  - 专门的代理类型
  - 上下文保留
  - 并行任务执行
- **用例**：复杂重构、系统设计

#### ThinkTool（思考工具）
- **用途**：允许 AI 推理问题
- **主要功能**：
  - 结构化思考块
  - 问题分解
  - 对用户输出隐藏
- **实现**：特殊消息格式

#### TodoWriteTool（待办事项工具）
- **用途**：任务管理和跟踪
- **主要功能**：
  - 持久待办事项列表
  - 状态跟踪（待处理、进行中、已完成）
  - 进度可视化
  - 自动任务分解

### 5. 外部集成工具

#### MCPTool（MCP 工具）
- **用途**：桥接到模型上下文协议服务器
- **主要功能**：
  - 动态工具发现
  - 协议转换
  - 服务器生命周期管理
  - 错误传播
- **实现**：通过 stdio/SSE 的 JSON-RPC

#### WebFetchTool（网页获取工具）
- **用途**：获取和处理网页内容
- **主要功能**：
  - HTML 到 markdown 转换
  - 内容提取
  - 缓存支持
  - 重定向处理

## 工具实现指南

### 创建新工具

```typescript
export class MyCustomTool extends Tool {
  name = 'my_custom_tool'
  description = '执行自定义操作'
  
  inputSchema = z.object({
    param1: z.string(),
    param2: z.number().optional()
  })
  
  needsPermissions(input: unknown): boolean {
    // 如果此操作需要用户批准，返回 true
    return true
  }
  
  async *call(
    input: z.infer<typeof this.inputSchema>,
    context: ToolUseContext
  ): AsyncGenerator<ToolCallEvent> {
    // 产生进度更新
    yield {
      type: 'progress',
      message: '开始操作...'
    }
    
    // 检查中止信号
    if (context.abortSignal.aborted) {
      throw new Error('操作已取消')
    }
    
    // 执行操作
    const result = await this.performOperation(input)
    
    // 产生最终结果
    yield {
      type: 'result',
      result: result
    }
  }
  
  renderResultForAssistant(input: unknown, result: unknown): string {
    // 为 AI 消费格式化结果
    return `操作完成：${JSON.stringify(result)}`
  }
}
```

### 工具注册

```typescript
// 在 tools.ts 中
export async function getTools(): Promise<Tool[]> {
  const tools = [
    new FileReadTool(),
    new FileEditTool(),
    new BashTool(),
    new MyCustomTool(), // 在这里添加您的工具
    // ... 其他工具
  ]
  
  // 动态添加 MCP 工具
  const mcpTools = await getMCPTools()
  tools.push(...mcpTools)
  
  return tools
}
```

## 权限系统集成

### 权限类型

1. **无需权限**：只读操作
2. **会话权限**：当前会话的临时批准
3. **持久权限**：保存以供将来使用的批准
4. **始终询问**：需要明确批准的关键操作

### 权限流程

```typescript
async function checkPermissionsAndCallTool(
  tool: Tool,
  input: unknown,
  context: ToolUseContext
): Promise<ToolResult> {
  if (!tool.needsPermissions(input)) {
    // 无需权限
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

## 工具上下文

### ToolUseContext 接口

```typescript
interface ToolUseContext {
  // 取消支持
  abortSignal: AbortSignal
  
  // 当前工作目录
  cwd: string
  
  // 权限助手
  hasPermission: (operation: string) => boolean
  requestPermission: (operation: string) => Promise<boolean>
  
  // 日志和指标
  logEvent: (event: string, data: any) => void
  
  // UI 助手
  showProgress: (message: string) => void
  
  // 配置访问
  config: Configuration
}
```

## 工具最佳实践

### 1. 输入验证
- 使用 Zod 模式进行类型安全验证
- 为无效输入提供清晰的错误消息
- 验证文件路径和命令参数

### 2. 错误处理
- 抛出带有可操作消息的描述性错误
- 优雅地处理常见故障情况
- 提供恢复建议

### 3. 进度报告
- 为长操作产生进度更新
- 包括百分比或步骤信息
- 以合理的间隔更新（不要太频繁）

### 4. 取消支持
- 定期检查中止信号
- 取消时清理资源
- 可能时保存部分进度

### 5. 结果格式化
- 为用户提供人类可读的输出
- 包括用于 AI 解析的结构化数据
- 适当地总结大型结果

### 6. 安全考虑
- 始终验证和清理输入
- 在操作前检查权限
- 限制资源消耗
- 防止路径遍历攻击

## 工具测试

### 单元测试

```typescript
describe('MyCustomTool', () => {
  it('应该正确验证输入', () => {
    const tool = new MyCustomTool()
    const validInput = { param1: 'test' }
    expect(() => tool.validateInput(validInput)).not.toThrow()
  })
  
  it('应该处理取消', async () => {
    const tool = new MyCustomTool()
    const abortController = new AbortController()
    abortController.abort()
    
    const context = {
      abortSignal: abortController.signal,
      // ... 其他上下文
    }
    
    await expect(
      tool.call(input, context)
    ).rejects.toThrow('操作已取消')
  })
})
```

### 集成测试

```typescript
it('应该与权限系统集成', async () => {
  const tool = new MyCustomTool()
  const context = createTestContext({
    permissions: ['my_custom_tool']
  })
  
  const result = await tool.call(input, context)
  expect(result).toBeDefined()
})
```

## 高级工具模式

### 复合工具
编排多个其他工具的工具：

```typescript
class CompositeAnalysisTool extends Tool {
  async *call(input, context) {
    // 首先，搜索文件
    const files = await this.globTool.call(
      { pattern: input.pattern },
      context
    )
    
    // 然后 grep 每个文件
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

### 流式工具
增量处理数据的工具：

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

### 有状态工具
跨调用维护状态的工具：

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

## 工具指标和监控

### 性能跟踪

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

### 错误跟踪

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

工具系统为 Kode 的所有功能提供了基础，在为 AI 和人类用户维护一致接口的同时，实现了安全、高效和可扩展的操作。