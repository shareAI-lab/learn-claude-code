# Security Model

## Overview

Kode implements a comprehensive security model that balances usability with safety. The system provides multiple layers of protection against potentially harmful operations while allowing power users to work efficiently.

## Security Principles

### 1. Principle of Least Privilege
Operations are granted minimum necessary permissions. Tools request only the specific permissions they need.

### 2. Explicit User Consent
Potentially dangerous operations require explicit user approval, with clear explanations of risks.

### 3. Defense in Depth
Multiple security layers ensure that a single failure doesn't compromise the system.

### 4. Transparency
All operations are logged and auditable. Users can see exactly what the AI is doing.

### 5. Safe Defaults
The system defaults to safer options, with more permissive modes requiring explicit opt-in.

## Security Modes

### Permissive Mode (Default)
Balances security with usability:
- Auto-approves safe read operations
- Prompts for file writes and system commands
- Caches approvals for session
- Suitable for trusted environments

### Safe Mode (--safe flag)
Maximum security for sensitive environments:
- Requires approval for all operations
- No automatic approvals
- No cached permissions
- Detailed operation descriptions
- Suitable for production systems

```bash
# Enable safe mode
kode --safe

# Safe mode for specific operations
kode --safe -p "update the production config"
```

## Permission System Architecture

```
┌─────────────────────────────────────────┐
│           Permission Request            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          Check Permission Type          │
├─────────────────────────────────────────┤
│ • No Permission Required (Read-only)    │
│ • Session Permission (Temporary)        │
│ • Persistent Permission (Saved)         │
│ • Always Ask (Critical)                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Permission Resolution           │
├─────────────────────────────────────────┤
│ 1. Check cached permissions             │
│ 2. Check session permissions            │
│ 3. Check persistent permissions         │
│ 4. Prompt user if needed               │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          Execute or Deny                │
└─────────────────────────────────────────┘
```

## Permission Types

### 1. File System Permissions

#### Read Permissions
- Automatically granted for project directories
- Restricted for system directories
- Hidden files require explicit permission

```typescript
interface FileReadPermission {
  path: string
  recursive: boolean
  includeHidden: boolean
  maxDepth?: number
}
```

#### Write Permissions
- Always require explicit approval
- Path validation to prevent traversal
- Backup creation for existing files

```typescript
interface FileWritePermission {
  path: string
  operation: 'create' | 'modify' | 'delete'
  createBackup: boolean
}
```

### 2. Command Execution Permissions

#### Command Approval Patterns
Commands are matched against approval patterns:

```json
{
  "allowedCommands": [
    "git *",           // All git commands
    "npm test",        // Specific command
    "bun run *",       // Pattern matching
    "echo *"           // Safe commands
  ]
}
```

#### Restricted Commands
Never allowed, even with permission:

```typescript
const RESTRICTED_COMMANDS = [
  'rm -rf /',
  'format',
  'fdisk',
  'dd',
  'mkfs',
  ':(){:|:&};:',  // Fork bomb
]
```

### 3. Network Permissions

#### API Access
- API keys stored securely
- Rate limiting enforced
- Request logging for audit

#### Web Fetch
- URL validation
- Redirect following with limits
- Content size restrictions

### 4. MCP Server Permissions

#### Server Approval
- Project-scoped server approval
- Capability-based permissions
- Runtime sandboxing

```typescript
interface MCPServerPermission {
  serverName: string
  capabilities: string[]
  scope: 'project' | 'global'
  autoApprove: boolean
}
```

## Security Features

### 1. Path Traversal Prevention

```typescript
function validatePath(requestedPath: string, allowedBase: string): boolean {
  const resolved = path.resolve(requestedPath)
  const base = path.resolve(allowedBase)
  
  // Prevent traversal outside allowed directory
  if (!resolved.startsWith(base)) {
    throw new SecurityError('Path traversal detected')
  }
  
  // Check for symbolic links
  const realPath = fs.realpathSync(resolved)
  if (!realPath.startsWith(base)) {
    throw new SecurityError('Symbolic link escape detected')
  }
  
  return true
}
```

### 2. Command Injection Prevention

```typescript
function sanitizeCommand(command: string): string {
  // Reject commands with dangerous characters
  const dangerous = /[;&|<>$`]/
  if (dangerous.test(command)) {
    throw new SecurityError('Dangerous command characters detected')
  }
  
  // Use array execution to prevent injection
  const [cmd, ...args] = shellQuote.parse(command)
  return { cmd, args }
}
```

### 3. Resource Limits

```typescript
interface ResourceLimits {
  maxFileSize: number      // 10MB default
  maxOutputSize: number    // 1MB default
  maxExecutionTime: number // 2 minutes default
  maxConcurrentOps: number // 10 default
  maxMemoryUsage: number   // 500MB default
}
```

### 4. Audit Logging

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
  // Write to secure audit log
  appendToAuditLog(event)
  
  // Alert on suspicious patterns
  if (detectSuspiciousPattern(event)) {
    alertSecurity(event)
  }
}
```

## Permission UI Components

### Permission Request Dialog

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

### Visual Indicators

- 🔒 **Locked**: Permission required
- ✅ **Approved**: Permission granted
- ❌ **Denied**: Permission rejected
- ⚠️ **Warning**: Potentially dangerous
- 🛡️ **Safe Mode**: Enhanced security active

## Security Best Practices

### For Users

1. **Use Safe Mode** for production systems
2. **Review Commands** before approval
3. **Limit Permissions** to necessary operations
4. **Regular Audits** of permission grants
5. **Secure API Keys** with environment variables

### For Developers

1. **Validate All Inputs** using Zod schemas
2. **Use Least Privilege** in tool design
3. **Clear Risk Communication** in permission requests
4. **Fail Securely** with safe defaults
5. **Log Security Events** for audit trail

## Threat Model

### Potential Threats

1. **Malicious Prompts**
   - **Threat**: User tricks AI into harmful actions
   - **Mitigation**: Permission system, command validation

2. **Path Traversal**
   - **Threat**: Access files outside project
   - **Mitigation**: Path validation, symlink checks

3. **Command Injection**
   - **Threat**: Execute unintended commands
   - **Mitigation**: Command sanitization, array execution

4. **Resource Exhaustion**
   - **Threat**: Consume excessive resources
   - **Mitigation**: Resource limits, timeouts

5. **Data Exfiltration**
   - **Threat**: Leak sensitive information
   - **Mitigation**: Network restrictions, audit logging

## Security Configuration

### Global Security Settings

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

### Project Security Policy

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

## Emergency Procedures

### Security Incident Response

1. **Immediate Actions**
   ```bash
   # Kill all Kode processes
   pkill -f kode
   
   # Revoke API keys
   kode config remove -g apiKey
   
   # Enable safe mode globally
   kode config set -g security.mode safe
   ```

2. **Investigation**
   ```bash
   # Check modified files
   git status
   git diff
   
   # Review permission grants
   kode security permissions list
   ```

3. **Recovery**
   ```bash
   # Reset permissions
   kode security reset
   
   # Restore from backup
   git restore .
   
   # Update security settings
   kode config set security.mode safe
   ```

## Security Monitoring

### Metrics and Alerts

```typescript
interface SecurityMetrics {
  permissionRequests: number
  deniedOperations: number
  suspiciousPatterns: number
  resourceViolations: number
  auditLogSize: number
}

function monitorSecurity() {
  // Check for anomalies
  if (metrics.deniedOperations > threshold) {
    alert('High number of denied operations')
  }
  
  // Pattern detection
  if (detectAttackPattern(auditLog)) {
    alert('Potential security threat detected')
  }
}
```

### Compliance

- **Audit Trail**: All operations logged
- **Access Control**: Role-based permissions
- **Data Protection**: Encryption for sensitive data
- **Incident Response**: Documented procedures
- **Regular Reviews**: Security audits and updates

The security model ensures that Kode provides powerful capabilities while maintaining strong protection against both accidental and malicious harm. The layered approach allows users to choose the appropriate security level for their environment while maintaining usability.