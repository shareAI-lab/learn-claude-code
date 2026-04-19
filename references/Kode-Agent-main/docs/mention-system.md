# @ Mention System

## Overview

Kode's @ mention system provides intelligent auto-completion and smart delegation for models, agents, and files. This unified interface makes it easy to reference different resources and trigger appropriate actions.

## Features

- 🦜 **Expert Model Consultation** - `@ask-model-name`
- 👤 **Agent Delegation** - `@run-agent-name` 
- 📁 **File References** - `@path/to/file`
- ⚡ **Smart Completion** - Real-time suggestions as you type
- 🔍 **Context-Aware** - Shows relevant options based on input

## Mention Types

### 🦜 Expert Model Consultation (`@ask-model-name`)

Consult specific AI models for specialized analysis and expert opinions.

**Format**: `@ask-{model-name}`

**Examples**:
```bash
@ask-claude-sonnet-4 How should I optimize this React component?
@ask-gpt-5 What are the security implications of this API design?
@ask-o1-preview Analyze the time complexity of this algorithm
```

**Behavior**:
- Triggers `AskExpertModelTool`
- Model receives only your question (no conversation history)
- Requires complete, self-contained questions
- Ideal for getting fresh perspectives from different models

### 👤 Agent Delegation (`@run-agent-name`)

Delegate tasks to specialized subagents with predefined capabilities.

**Format**: `@run-agent-{agent-type}`

**Examples**:
```bash
@run-agent-general-purpose Review this code for over-engineering
@run-agent-my-custom-agent Design a microservices architecture
```

**Behavior**:
- Triggers `TaskTool` with specified subagent
- Agent has access to project context and tools
- Uses agent's specialized prompt and model preferences
- Ideal for focused, expert-level task execution

### 📁 File References (`@path/to/file`)

Reference files and directories with intelligent path completion.

**Format**: `@{file-path}`

**Examples**:
```bash
@src/components/Button.tsx
@docs/api-reference.md
@package.json
@README.md
```

**Behavior**:
- Shows file/directory structure as you type
- Supports relative and absolute paths
- Integrates with file reading tools
- Provides context for file-based discussions

## Smart Completion UI

### Completion Priority

1. **🦜 Ask Models** (Score: 90) - Expert consultation options
2. **👤 Run Agents** (Score: 85) - Available subagents  
3. **📁 Files** (Score: 70-80) - Project files and directories

### Keyboard Navigation

- **Tab** - Cycle through suggestions or complete partial matches
- **↑/↓** - Navigate suggestion list
- **Enter** - Select highlighted suggestion
- **Esc** - Close completion menu
- **Space** - Complete and continue (for directories)

### Visual Indicators

- 🦜 - Expert model consultation
- 👤 - Agent delegation
- 📁 - Directory
- 📄 - File

## Implementation Details

### Mention Processing Pipeline

1. **Pattern Matching** - Regular expressions detect @ask-, @run-agent-, and @file patterns
2. **Event Emission** - MentionProcessor emits events to SystemReminder service
3. **System Reminder Generation** - Creates tool-specific guidance messages
4. **Tool Invocation** - AI selects appropriate tool based on reminder context

### Supported Patterns

```typescript
// Recognized patterns
/@(ask-[\w\-]+)/g           // @ask-model-name
/@(run-agent-[\w\-]+)/g     // @run-agent-name  
/@(agent-[\w\-]+)/g         // @agent-name (legacy)
/@([a-zA-Z0-9/._-]+)/g      // @file/path
```

### Email Protection

The system intelligently detects email addresses and treats them as regular text:
```bash
user@domain.com  # Treated as regular text, no completion
@ask-claude      # Triggers completion
```

## Legacy Support

### Legacy Support

- `@agent-name` format supported by agentMentionDetector
- `@run-agent-name` format supported by mentionProcessor
- Both patterns trigger TaskTool with subagent_type parameter

### Migration Guide

```bash
# Old format (still works)
@my-agent

# New format (recommended)  
@run-agent-my-agent
```

## Configuration

### Available Models

Models are loaded dynamically from your configuration:
```bash
# View configured models
/model

# Models appear in @ask- completions automatically
```

### Available Agents

Agents are loaded from multiple sources:
- Built-in agents (only general-purpose currently available)
- User agents (`~/.kode/agents/`)
- Project agents (`./.kode/agents/`)

```bash
# View available agents
/agents

# Create new agent
/agents -> c (create)
```

## Best Practices

### For Expert Model Consultation

1. **Provide Complete Context**: Include all relevant background information
2. **Structure Questions**: Background → Situation → Question
3. **Be Specific**: Ask for particular types of analysis or perspectives
4. **Use Right Model**: Choose models based on their strengths

### For Agent Delegation

1. **Match Task to Agent**: Use specialists for their expertise areas
2. **Clear Instructions**: Provide specific, actionable task descriptions
3. **Context Awareness**: Agents have project context, use it effectively
4. **Tool Permissions**: Ensure agents have necessary tool access

### For File References

1. **Use Auto-completion**: Let the system suggest valid paths
2. **Relative Paths**: Prefer relative paths for project portability
3. **Context Clarity**: Explain what you want to do with the file
4. **Multiple Files**: Reference multiple files when needed

## Troubleshooting

### Completion Not Working?

- Check if you're in the terminal input area
- Ensure @ is at the start of a word boundary
- Try typing more characters to trigger completion
- Restart Kode if completion seems stuck

### Models/Agents Not Appearing?

- Verify model configuration with `/model`
- Check agent configurations with `/agents`
- Ensure proper file permissions for agent directories
- Try reloading agents with `/agents` → `r`

### Wrong Tool Being Selected?

- Check system reminder events in verbose mode
- Verify mention format matches expected patterns
- Ensure agent configurations are valid
- Review tool descriptions for conflicts

## Future Enhancements

Planned improvements:
- **Fuzzy Matching** - Better completion matching
- **Context Hints** - Show tool descriptions in completions
- **Custom Shortcuts** - User-defined @ shortcuts
- **Completion Analytics** - Track most-used mentions
- **Multi-file Selection** - Select multiple files at once