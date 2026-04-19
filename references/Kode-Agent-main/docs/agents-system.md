# Agent Configuration System

## Overview

Kode's Agent system allows you to create specialized AI agents with predefined configurations, tools, and prompts. This enables more efficient task execution by using purpose-built agents for specific types of work.

**New in this version**: Use `@run-agent-name` for intelligent delegation with auto-completion support.

## Features

- **Dynamic Agent Loading**: Agents are loaded from configuration files at runtime
- **Five-tier Priority System**: Built-in < .claude (user) < .kode (user) < .claude (project) < .kode (project)
- **Hot Reload**: Agent files monitored via Node.js fs.watch with cache invalidation
- **Tool Restrictions**: Limit agents to specific tools for security and focus
- **Model Selection**: Each agent can specify its preferred AI model
- **Interactive Management**: Use `/agents` command for graphical management

## Quick Start

### Using Pre-configured Agents

Kode has one built-in agent:

```bash
@run-agent-general-purpose Find all TypeScript test files
@run-agent-my-custom-agent Implement a new user authentication feature
```

### Managing Agents

Use the `/agents` command in the Kode REPL to manage agents:

```bash
kode
> /agents
```

This opens an interactive UI where you can:
- View all available agents
- Create new agents
- Edit existing agents
- Delete custom agents

Keyboard shortcuts:
- `c` - Create new agent
- `r` - Reload agents
- `d` - Delete selected agent (when viewing)
- `q` or `Esc` - Exit

## Agent Configuration

### File Structure

Agents are defined as Markdown files with YAML frontmatter:

```markdown
---
name: agent-name
description: "When to use this agent"
tools: ["Tool1", "Tool2", "Tool3"]  # or "*" for all tools
model_name: model-name  # optional (preferred over deprecated 'model' field)
---

System prompt content goes here...
```

**Note**: Use `model_name` to specify the AI model. The deprecated `model` field is ignored.

### Configuration Locations

Agents can be defined at five levels with priority order (later overrides earlier):

1. **Built-in** (lowest priority)
   - Provided with Kode
   - Cannot be modified

2. **.claude User (Claude Code)** (`~/.claude/agents/`)
   - Compatibility with Claude Code user directories
   - Personal agents available across all projects

3. **Kode User** (`~/.kode/agents/`)
   - Kode-specific user-level agents
   - Overrides Claude user agents with same name
   - Create with `/agents` command or manually

4. **.claude Project (Claude Code)** (`./.claude/agents/`)
   - Compatibility with Claude Code project directories
   - Overrides user-level agents

5. **Kode Project** (`./.kode/agents/`)
   - Kode-specific project agents
   - Highest priority, overrides all others

### Example: Creating a Custom Agent

#### 1. Manual Creation

Create a file `~/.kode/agents/api-designer.md`:

```markdown
---
name: api-designer
description: "Designs RESTful APIs and GraphQL schemas with best practices"
tools: ["FileRead", "FileWrite", "Grep"]
model_name: reasoning
---

You are an API design specialist. Your expertise includes:

- Designing RESTful APIs following OpenAPI specifications
- Creating GraphQL schemas with efficient resolvers
- Implementing proper authentication and authorization
- Ensuring API versioning and backward compatibility
- Writing comprehensive API documentation

Design principles:
- Follow REST best practices (proper HTTP verbs, status codes, etc.)
- Design for scalability and performance
- Include proper error handling and validation
- Consider rate limiting and caching strategies
- Maintain consistency across endpoints
```

#### 2. Using /agents Command

1. Run `kode` to start the REPL
2. Type `/agents`
3. Press `c` to create
4. Follow the prompts:
   - Enter agent name
   - Describe when to use it
   - Specify allowed tools
   - Optionally specify a model
   - Write the system prompt

## Advanced Usage

### Tool Restrictions

```yaml
tools: ["FileRead", "Grep", "Glob"]  # Specific tools
tools: ["*"]                         # All tools (default)
```

### Model Selection

Specify which AI model the agent should use:

```yaml
model_name: quick      # Fast responses for simple tasks
model_name: main       # Default model for general tasks  
model_name: reasoning  # Complex analysis and design
```


## Available Built-in Agents

### general-purpose
- **Use for**: General research, complex multi-step tasks
- **Tools**: All tools
- **Model**: task (default)

Note: This is currently the only built-in agent. Create custom agents using the `/agents` command or by adding configuration files.

## Custom Agents

Create your own agents in the appropriate directory:

```bash
mkdir -p .kode/agents    # Project-specific
mkdir -p ~/.kode/agents  # User-wide
```

## Best Practices

1. **Agent Naming**: Use descriptive, action-oriented names (e.g., `test-writer`, `api-designer`)

2. **Tool Selection**: Only include tools the agent actually needs

3. **System Prompts**: Be specific about the agent's role and guidelines

4. **Model Choice**: 
   - Use `quick` for simple, fast operations
   - Use `main` for general coding tasks
   - Use `reasoning` for complex analysis

5. **Organization**: 
   - Keep user agents for personal workflows
   - Keep project agents for team-shared configurations

## Troubleshooting

### Agents not loading?
- Check file permissions in `~/.kode/agents/` or `./.kode/agents/`
- Ensure YAML frontmatter is valid
- Use `/agents` command and press `r` to reload

### Agent not working as expected?
- Verify the tools list includes necessary tools
- Check the system prompt is clear and specific
- Test with verbose mode to see actual prompts

### Hot reload not working?
- File watcher requires proper file system events
- Try manual reload with `/agents` then `r`
- Restart Kode if needed

## Integration with Task Tool

The agent system is integrated with Kode's Task tool:

```typescript
// In your code or scripts
await TaskTool.call({
  description: "Search for patterns",
  prompt: "Find all instances of TODO comments",
  subagent_type: "general-purpose"
})
```

This allows programmatic use of agents in automation and scripts.

## Future Enhancements

Planned improvements:
- Agent templates and inheritance
- Performance metrics per agent
- Agent composition (agents using other agents)
- Cloud-based agent sharing
- Agent versioning and rollback
