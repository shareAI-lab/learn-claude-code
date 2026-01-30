# Learn Claude Code - Java Edition

Java implementation of v4 Skills Agent pattern.

## Quick Start

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Build
mvn clean package

# Run
mvn exec:java
```

## Project Structure

```
code/
├── pom.xml
├── .env.example
├── .gitignore
└── src/main/java/com/agent/
    ├── AgentApplication.java    # Entry point
    ├── Agent.java               # Main loop
    ├── AgentRepl.java           # Interactive REPL
    ├── config/
    │   └── AgentConfig.java     # Configuration
    ├── tool/
    │   ├── ToolDefinitions.java # Tool schemas
    │   └── ToolExecutor.java    # Tool execution
    ├── skill/
    │   ├── Skill.java           # Skill model
    │   └── SkillLoader.java     # Skill loader
    └── util/
        └── Environment.java     # .env loader
```

## Core Pattern

```java
while (true) {
    response = model(messages, tools);
    if (response.stopReason != "tool_use") {
        return response.text;
    }
    results = execute(response.toolCalls);
    messages.append(results);
}
```

## Adding Skills

Create `skills/{skill-name}/SKILL.md`:

```yaml
---
name: myskill
description: Description of what this skill does
---
# Skill Content

Detailed instructions here...
```

## License

MIT
