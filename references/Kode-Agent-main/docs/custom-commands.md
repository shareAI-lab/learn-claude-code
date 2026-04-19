# Custom Commands Documentation

## Overview

Kode supports custom slash commands through Markdown files placed in `.claude/commands/` or `.kode/commands/` directories. This feature allows you to create reusable prompts and workflows tailored to your specific needs.

## Directory Structure

Custom commands are loaded from multiple locations (both .claude and .kode directories are supported):

- **Global commands**: 
  - `~/.claude/commands/` - Available in all projects
  - `~/.kode/commands/` - Available in all projects
- **Project commands**: 
  - `./.claude/commands/` - Specific to the current project
  - `./.kode/commands/` - Specific to the current project

Note: Both .claude and .kode directories work identically for backward compatibility.

## Command File Format

Each command is defined in a Markdown file with YAML frontmatter:

```markdown
---
name: command-name
description: Brief description of what this command does
aliases: [alias1, alias2]
enabled: true
hidden: false
progressMessage: Custom progress message...
argNames: [arg1, arg2]
---

Command prompt content goes here.

You can reference arguments using {arg1} and {arg2} placeholders.
```

### Frontmatter Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | filename | Command name (used as `/name`) |
| `description` | string | auto-generated | Description shown in help |
| `aliases` | string[] | `[]` | Alternative command names |
| `enabled` | boolean | `true` | Whether command is available |
| `hidden` | boolean | `false` | Hide from help output |
| `progressMessage` | string | auto-generated | Message shown while running |
| `argNames` | string[] | `[]` | Named arguments for substitution |

## Examples

### 1. Simple Command

**File**: `~/.claude/commands/status.md` or `~/.kode/commands/status.md`

```markdown
---
name: status
description: Show project status
aliases: [st, info]
---

Provide a comprehensive project status including:
- Current git status and recent commits
- Modified files summary
- Test results and build status
- Development environment state

Please analyze the current state and provide a structured status report.
```

**Usage**: `/status` or `/st` or `/info`

### 2. Parameterized Command

**File**: `./.claude/commands/deploy.md` or `./.kode/commands/deploy.md`

```markdown
---
name: deploy
description: Generate deployment checklist
aliases: [ship]
argNames: [environment, version]
progressMessage: Preparing deployment for {environment}...
---

Generate deployment checklist for {environment} environment, version {version}:

**Pre-deployment:**
- Code review completion
- All tests passing
- Security scans completed

**Deployment steps:**
1. Backup current state
2. Deploy to {environment}
3. Verify deployment
4. Monitor metrics

**Post-deployment:**
- Health checks
- Performance monitoring
- Documentation updates

Please provide environment-specific recommendations and validate the deployment readiness.
```

**Usage**: `/deploy staging v2.1.0`

### 3. Security Audit Command

**File**: `~/.claude/commands/security.md` or `~/.kode/commands/security.md`

```markdown
---
name: security-audit
description: Perform comprehensive security analysis
aliases: [sec, audit]
enabled: true
progressMessage: Conducting security analysis...
---

Perform a comprehensive security analysis:

**Vulnerability Assessment:**
- OWASP Top 10 vulnerabilities
- Dependency vulnerabilities
- Input validation issues
- Authentication/authorization flaws

**Code Security Review:**
- Hardcoded secrets detection
- Insecure data handling
- Error handling security
- Access control issues

**Infrastructure Security:**
- Environment configuration
- Network security
- SSL/TLS configuration
- Container security

Please provide prioritized security recommendations with remediation steps.
```

**Usage**: `/security-audit` or `/sec` or `/audit`

## Best Practices

### 1. Command Naming
- Use descriptive names with hyphens: `code-review`, `performance-audit`
- Provide meaningful aliases: `[cr, review]` for `code-review`
- Keep names concise but clear

### 2. Content Structure
- Start with clear objectives
- Use structured lists and sections
- Include specific context requests
- End with actionable requests

### 3. Argument Usage
- Define clear `argNames` for parameterized commands
- Use descriptive placeholder names: `{environment}`, `{version}`
- Provide default behavior when arguments are optional

### 4. Organization
- Group related commands in directories
- Use consistent naming patterns
- Keep global commands general-purpose
- Make project commands specific to the codebase

## Advanced Features

### Argument Substitution

When `argNames` are defined, you can use `{argName}` placeholders in your content:

```markdown
---
argNames: [framework, feature]
---

Implement {feature} using {framework} framework:

1. Setup {framework} project structure
2. Create {feature} component
3. Add {framework}-specific configuration
4. Write tests for {feature}
```

### Progress Messages

Customize the message shown while the command executes:

```markdown
---
progressMessage: Analyzing {framework} codebase for {feature} implementation...
---
```

### Conditional Display

Use `hidden: true` for internal commands or work-in-progress commands:

```markdown
---
hidden: true  # Won't appear in /help output
---
```

## Troubleshooting

### Commands Not Loading
1. Check file extension is `.md`
2. Verify frontmatter syntax (YAML format)
3. Ensure directories exist: `~/.claude/commands/`, `~/.kode/commands/`, `./.claude/commands/`, or `./.kode/commands/`
4. Check file permissions

### Syntax Errors
- YAML frontmatter must be properly formatted
- Arrays can be `[item1, item2]` or multi-line with `- item`
- Boolean values should be `true`/`false` (not quoted)
- Strings with special characters should be quoted

### Performance
- Commands are cached and loaded once per session
- Large numbers of commands may affect startup time
- Use `enabled: false` to temporarily disable commands

## Integration with Kode

Custom commands integrate seamlessly with the existing command system:

- Loaded alongside built-in commands (`/help`, `/config`, etc.)
- Support all existing features (aliases, help display, etc.)
- Respect the same permission and security models
- Logged with performance metrics

Use `/help` to see all available commands, including your custom ones highlighted in the Custom Commands section.