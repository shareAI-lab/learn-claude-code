# 安全模型

## 概述

Kode 实现了全面的安全模型，在可用性和安全性之间取得平衡。系统提供多层保护，防止潜在有害的操作，同时允许高级用户高效工作。

## 安全原则

### 1. 最小权限原则
操作被授予最小必要权限。工具只请求它们需要的特定权限。

### 2. 明确的用户同意
潜在危险的操作需要明确的用户批准，并清楚地解释风险。

### 3. 纵深防御
多个安全层确保单一故障不会危及系统。

### 4. 透明度
所有操作都被记录并可审计。用户可以看到 AI 正在做什么。

### 5. 安全默认值
系统默认为更安全的选项，更宽松的模式需要明确选择加入。

## 安全模式

### 宽松模式（默认）
平衡安全性和可用性：
- 自动批准安全的读取操作
- 提示文件写入和系统命令
- 为会话缓存批准
- 适用于受信任的环境

### 安全模式（--safe 标志）
对敏感环境的最大安全性：
- 所有操作都需要批准
- 无自动批准
- 无缓存权限
- 详细的操作描述
- 适用于生产系统

```bash
# 启用安全模式
kode --safe

# 特定操作的安全模式
kode --safe -p "更新生产配置"
```

## 权限系统架构

```
┌─────────────────────────────────────────┐
│            权限请求                       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          检查权限类型                     │
├─────────────────────────────────────────┤
│ • 无需权限（只读）                        │
│ • 会话权限（临时）                        │
│ • 持久权限（保存）                        │
│ • 始终询问（关键）                        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         权限解析                          │
├─────────────────────────────────────────┤
│ 1. 检查缓存权限                          │
│ 2. 检查会话权限                          │
│ 3. 检查持久权限                          │
│ 4. 如需要则提示用户                      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          执行或拒绝                       │
└─────────────────────────────────────────┘
```

## 权限类型

### 1. 文件系统权限

#### 读取权限
- 自动授予项目目录
- 限制系统目录
- 隐藏文件需要明确权限

```typescript
interface FileReadPermission {
  path: string
  recursive: boolean
  includeHidden: boolean
  maxDepth?: number
}
```

#### 写入权限
- 始终需要明确批准
- 路径验证以防止遍历
- 为现有文件创建备份

```typescript
interface FileWritePermission {
  path: string
  operation: 'create' | 'modify' | 'delete'
  createBackup: boolean
}
```

### 2. 命令执行权限

#### 命令批准模式
命令与批准模式匹配：

```json
{
  "allowedCommands": [
    "git *",           // 所有 git 命令
    "npm test",        // 特定命令
    "bun run *",       // 模式匹配
    "echo *"           // 安全命令
  ]
}
```

#### 受限命令
永不允许，即使有权限：

```typescript
const RESTRICTED_COMMANDS = [
  'rm -rf /',
  'format',
  'fdisk',
  'dd',
  'mkfs',
  ':(){:|:&};:',  // Fork 炸弹
]
```

### 3. 网络权限

#### API 访问
- API 密钥安全存储
- 强制执行速率限制
- 用于审计的请求日志

#### 网页获取
- URL 验证
- 带限制的重定向跟随
- 内容大小限制

### 4. MCP 服务器权限

#### 服务器批准
- 项目范围的服务器批准
- 基于功能的权限
- 运行时沙箱

```typescript
interface MCPServerPermission {
  serverName: string
  capabilities: string[]
  scope: 'project' | 'global'
  autoApprove: boolean
}
```

## 安全功能

### 1. 路径遍历防护

```typescript
function validatePath(requestedPath: string, allowedBase: string): boolean {
  const resolved = path.resolve(requestedPath)
  const base = path.resolve(allowedBase)
  
  // 防止在允许的目录外遍历
  if (!resolved.startsWith(base)) {
    throw new SecurityError('检测到路径遍历')
  }
  
  // 检查符号链接
  const realPath = fs.realpathSync(resolved)
  if (!realPath.startsWith(base)) {
    throw new SecurityError('检测到符号链接逃逸')
  }
  
  return true
}
```

### 2. 命令注入防护

```typescript
function sanitizeCommand(command: string): string {
  // 拒绝带有危险字符的命令
  const dangerous = /[;&|<>$`]/
  if (dangerous.test(command)) {
    throw new SecurityError('检测到危险的命令字符')
  }
  
  // 使用数组执行以防止注入
  const [cmd, ...args] = shellQuote.parse(command)
  return { cmd, args }
}
```

### 3. 资源限制

```typescript
interface ResourceLimits {
  maxFileSize: number      // 默认 10MB
  maxOutputSize: number    // 默认 1MB
  maxExecutionTime: number // 默认 2 分钟
  maxConcurrentOps: number // 默认 10
  maxMemoryUsage: number   // 默认 500MB
}
```

### 4. 审计日志

```typescript
interface AuditLog {
  timestamp: Date
  operation: string
  tool: string
  input: any
  result: 'approved' | 'denied' | 'error'
  user: string
  sessionId: string
}

function logSecurityEvent(event: AuditLog) {
  // 写入安全审计日志
  appendToAuditLog(event)
  
  // 检测可疑模式时发出警报
  if (detectSuspiciousPattern(event)) {
    alertSecurity(event)
  }
}
```

## 权限 UI 组件

### 权限请求对话框

```typescript
interface PermissionRequest {
  title: string
  description: string
  risks: string[]
  operation: {
    tool: string
    action: string
    target: string
  }
  options: {
    approve: boolean
    deny: boolean
    alwaysAllow: boolean
    saveForSession: boolean
  }
}
```

### 视觉指示器

- 🔒 **锁定**：需要权限
- ✅ **批准**：权限已授予
- ❌ **拒绝**：权限被拒绝
- ⚠️ **警告**：潜在危险
- 🛡️ **安全模式**：增强安全激活

## 安全最佳实践

### 对于用户

1. **为生产系统使用安全模式**
2. **批准前审查命令**
3. **将权限限制为必要的操作**
4. **定期审计权限授予**
5. **使用环境变量保护 API 密钥**

### 对于开发者

1. **使用 Zod 模式验证所有输入**
2. **在工具设计中使用最小权限**
3. **在权限请求中清晰的风险沟通**
4. **使用安全默认值安全失败**
5. **记录安全事件以供审计跟踪**

## 威胁模型

### 潜在威胁

1. **恶意提示**
   - **威胁**：用户欺骗 AI 进行有害操作
   - **缓解**：权限系统、命令验证

2. **路径遍历**
   - **威胁**：访问项目外的文件
   - **缓解**：路径验证、符号链接检查

3. **命令注入**
   - **威胁**：执行非预期的命令
   - **缓解**：命令清理、数组执行

4. **资源耗尽**
   - **威胁**：消耗过多资源
   - **缓解**：资源限制、超时

5. **数据泄露**
   - **威胁**：泄露敏感信息
   - **缓解**：网络限制、审计日志

## 安全配置

### 全局安全设置

```json
{
  "security": {
    "mode": "permissive",
    "maxFileSize": 10485760,
    "maxExecutionTime": 120000,
    "auditLogging": true,
    "restrictedPaths": [
      "/etc",
      "/sys",
      "/proc",
      "~/.ssh"
    ]
  }
}
```

### 项目安全策略

```json
{
  "security": {
    "allowedCommands": [
      "git *",
      "npm test",
      "npm run build"
    ],
    "allowedPaths": [
      "./src",
      "./tests",
      "./docs"
    ],
    "deniedTools": [
      "bash"
    ],
    "requireApproval": [
      "file_write",
      "file_delete"
    ]
  }
}
```

## 紧急程序

### 安全事件响应

1. **立即行动**
   ```bash
   # 终止所有 Kode 进程
   pkill -f kode
   
   # 撤销 API 密钥
   kode config remove -g apiKey
   
   # 全局启用安全模式
   kode config set -g security.mode safe
   ```

2. **调查**
   ```bash
   # 检查修改的文件
   git status
   git diff
   
   # 审查权限授予
   kode security permissions list
   ```

3. **恢复**
   ```bash
   # 重置权限
   kode security reset
   
   # 从备份恢复
   git restore .
   
   # 更新安全设置
   kode config set security.mode safe
   ```

## 安全监控

### 指标和警报

```typescript
interface SecurityMetrics {
  permissionRequests: number
  deniedOperations: number
  suspiciousPatterns: number
  resourceViolations: number
  auditLogSize: number
}

function monitorSecurity() {
  // 检查异常
  if (metrics.deniedOperations > threshold) {
    alert('拒绝操作数量过多')
  }
  
  // 模式检测
  if (detectAttackPattern(auditLog)) {
    alert('检测到潜在的安全威胁')
  }
}
```

### 合规性

- **审计跟踪**：所有操作都被记录
- **访问控制**：基于角色的权限
- **数据保护**：敏感数据加密
- **事件响应**：记录的程序
- **定期审查**：安全审计和更新

安全模型确保 Kode 提供强大的功能，同时保持对意外和恶意伤害的强大保护。分层方法允许用户为其环境选择适当的安全级别，同时保持可用性。