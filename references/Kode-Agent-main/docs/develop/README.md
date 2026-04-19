# Kode Development Documentation

This comprehensive documentation provides a complete understanding of the Kode codebase architecture, design patterns, and implementation details for developers.

## Documentation Structure

### Core Documentation

- **[System Overview](./overview.md)** - Introduction to Kode's design philosophy, capabilities, and core principles
- **[Architecture](./architecture.md)** - High-level system architecture, component relationships, and data flow
- **[Security Model](./security-model.md)** - Comprehensive security architecture, permission system, and threat model
- **[Configuration System](./configuration.md)** - Multi-level configuration management and settings
- **[Testing](./testing.md)** - Comprehensive testing guide and infrastructure

### System Components

- **[Tool System](./tools-system.md)** - The heart of Kode's functionality, standardized tool interface and implementation
- **[Model Management](./modules/model-management.md)** - Multi-provider AI model integration and intelligent switching
- **[MCP Integration](./modules/mcp-integration.md)** - Model Context Protocol for third-party tool integration
- **[Custom Commands](./modules/custom-commands.md)** - Markdown-based extensible command system
- **[OpenAI Adapter Layer](./modules/openai-adapters.md)** - Anthropic-to-OpenAI request translation for Chat Completions and Responses API

### Core Modules

- **[Query Engine](./modules/query-engine.md)** - AI conversation orchestration and streaming response handling
- **[REPL Interface](./modules/repl-interface.md)** - Interactive terminal UI and user interaction management
- **[Context System](./modules/context-system.md)** - Project context gathering and intelligent injection

## Quick Navigation

### For New Contributors

1. Start with the [System Overview](./overview.md) to understand Kode's purpose and design
2. Read the [Architecture](./architecture.md) document to understand component relationships
3. Review the [Tool System](./tools-system.md) to understand how capabilities are implemented
4. Check the [Security Model](./security-model.md) for permission and safety considerations

### For Feature Development

- **Adding a new tool**: See [Tool System](./tools-system.md#creating-a-new-tool)
- **Adding a new AI provider**: See [Model Management](./modules/model-management.md#provider-integration)
- **Creating custom commands**: See [Custom Commands](./modules/custom-commands.md#examples)
- **Integrating MCP servers**: See [MCP Integration](./modules/mcp-integration.md#server-management)

### For System Understanding

- **How conversations work**: [Query Engine](./modules/query-engine.md#conversation-flow)
- **How UI is rendered**: [REPL Interface](./modules/repl-interface.md#message-rendering)
- **How context is managed**: [Context System](./modules/context-system.md#context-injection)
- **How security is enforced**: [Security Model](./security-model.md#permission-system-architecture)

## Key Concepts

### Tool-First Architecture
Everything in Kode is implemented as a Tool with standardized interfaces for validation, permissions, and execution. This provides unlimited extensibility while maintaining consistency.

### Multi-Level Configuration
Configuration cascades from environment variables → runtime flags → project config → global config → defaults, allowing flexible customization at any level.

### Context-Aware AI
The system automatically gathers and injects relevant project context (git status, directory structure, documentation) to improve AI response quality.

### Security Layers
Multiple security layers including permission system, command validation, path traversal prevention, and resource limits ensure safe operation.

### Streaming Architecture
All long-running operations use async generators for real-time progress updates and cancellation support.

## Development Workflow

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/shareAI-lab/kode.git
cd kode

# Install dependencies
bun install

# Run in development mode
bun run dev
```

### Running Tests

```bash
# Run all tests
bun test

# Run specific test file
bun test src/tools/BashTool.test.ts

# Run with coverage
bun test --coverage
```

### Building for Production

```bash
# Build CLI
bun run build

# Run type checking
bun run typecheck

# Format code
bun run format
```

## Architecture Principles

### 1. Modular Design
Each component has a single responsibility with clear interfaces and minimal dependencies.

### 2. Extensibility
New capabilities can be added through Tools, Commands, or MCP servers without modifying core code.

### 3. Security by Default
All operations require appropriate permissions with safe defaults and explicit user consent.

### 4. Performance Conscious
Streaming responses, lazy loading, and intelligent caching ensure responsive interaction.

### 5. User Experience First
Terminal-native design with keyboard shortcuts, syntax highlighting, and clear error messages.

## Code Organization

```
src/
├── entrypoints/        # Application entry points
│   ├── cli.tsx        # Main CLI entry
│   └── mcp.ts         # MCP server entry
├── screens/           # Full-screen UI components
│   ├── REPL.tsx       # Main interactive interface
│   └── Doctor.tsx     # System diagnostics
├── components/        # Reusable UI components
│   ├── messages/      # Message rendering
│   └── permissions/   # Permission dialogs
├── tools/            # Tool implementations
│   ├── BashTool.ts   # Shell execution
│   └── FileEditTool.ts # File manipulation
├── services/         # External service integrations
│   ├── claude.ts     # Anthropic API
│   └── mcpClient.ts  # MCP client
├── utils/            # Utility functions
│   ├── config.ts     # Configuration management
│   └── model.ts      # Model management
└── Tool.ts           # Base Tool class
```

## Contributing Guidelines

### Code Style
- TypeScript with relaxed strict mode
- 2-space indentation
- No semicolons (Prettier enforced)
- Descriptive variable names
- Comprehensive error handling

### Testing Requirements
- Unit tests for new Tools
- Integration tests for command flows
- Mock external dependencies
- Test error conditions

### Documentation Standards
- Update relevant documentation
- Include code examples
- Document breaking changes
- Add inline comments for complex logic

### Pull Request Process
1. Create feature branch
2. Implement with tests
3. Update documentation
4. Run `bun test` and `bun run typecheck`
5. Submit PR with clear description

## Advanced Topics

### Performance Optimization
- Use streaming for large operations
- Implement caching strategically
- Lazy load heavy dependencies
- Profile with Chrome DevTools

### Debugging
- Enable debug mode: `kode --debug`
- Check logs: `kode error`
- Use verbose output: `kode --verbose`
- Inspect with Node debugger

### Security Considerations
- Always validate user input
- Use path.resolve for file operations
- Implement rate limiting
- Log security events

## Resources

### Internal Documentation
- [Project Structure](../PROJECT_STRUCTURE.md)
- [Custom Commands Guide](../custom-commands.md)
- [Publishing Guide](../PUBLISH.md)

### External Resources
- [Anthropic API Documentation](https://docs.anthropic.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Ink React Renderer](https://github.com/vadimdemedes/ink)

## Support

For questions or issues:
- GitHub Issues: [Report bugs](https://github.com/shareAI-lab/kode/issues)
- Discussions: [Ask questions](https://github.com/shareAI-lab/kode/discussions)

---

This documentation represents the complete technical understanding of the Kode system as of the current version. It serves as the authoritative reference for developers working on or with the Kode codebase.
