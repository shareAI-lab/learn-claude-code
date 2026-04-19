# Kode - AI Coding
<img width="991" height="479" alt="image" src="https://github.com/user-attachments/assets/c1751e92-94dc-4e4a-9558-8cd2d058c1a1" />  <br> 
[![npm version](https://badge.fury.io/js/@shareai-lab%2Fkode.svg)](https://www.npmjs.com/package/@shareai-lab/kode)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![AGENTS.md](https://img.shields.io/badge/AGENTS.md-Compatible-brightgreen)](https://agents.md)

[中文文档](README.zh-CN.md) | [Contributing](CONTRIBUTING.md) | [Documentation](docs/README.md)

<img width="90%" alt="image" src="https://github.com/user-attachments/assets/fdce7017-8095-429d-b74e-07f43a6919e1" />

<img width="90%" alt="2c0ad8540f2872d197c7b17ae23d74f5" src="https://github.com/user-attachments/assets/f220cc27-084d-468e-a3f4-d5bc44d84fac" />

<img width="90%" alt="f266d316d90ddd0db5a3d640c1126930" src="https://github.com/user-attachments/assets/90ec7399-1349-4607-b689-96613b3dc3e2" />


<img width="90%" alt="image" src="https://github.com/user-attachments/assets/b30696ce-5ab1-40a0-b741-c7ef3945dba0" />


## 📢 Update Log

**2025-12-22**: Native-first distribution (Windows OOTB). Kode prefers a cached native binary and falls back to the Node.js runtime when needed. See `docs/binary-distribution.md`.


## 🤝 AGENTS.md Standard Support

Kode supports the [AGENTS.md standard](https://agents.md): a simple, open format for guiding coding agents, used by 60k+ open-source projects.

### Full Compatibility with Multiple Standards

- ✅ **AGENTS.md** - Native support for the OpenAI-initiated standard format
- ✅ **Legacy `.claude` compatibility** - Reads `.claude` directories and `CLAUDE.md` when present (see `docs/compatibility.md`)
- ✅ **Subagent System** - Advanced agent delegation and task orchestration
- ✅ **Cross-platform** - Works with 20+ AI models and providers

Use `# Your documentation request` to generate and maintain your AGENTS.md file automatically, while preserving compatibility with existing `.claude` workflows.

### Instruction Discovery (Codex-compatible)

- Kode reads project instructions by walking from the Git repo root → current working directory.
- In each directory, it prefers `AGENTS.override.md` over `AGENTS.md` (at most one file per directory).
- Discovered files are concatenated root → leaf (combined size capped at 32 KiB by default; override with `KODE_PROJECT_DOC_MAX_BYTES`).
- If `CLAUDE.md` exists in the current directory, Kode also reads it as a legacy instruction file.

## Overview

Kode is a powerful AI assistant that lives in your terminal. It can understand your codebase, edit files, run commands, and handle entire workflows for you.

> **⚠️ Security Notice**: Kode runs in YOLO mode by default (equivalent to the `--dangerously-skip-permissions` flag), bypassing all permission checks for maximum productivity. YOLO mode is recommended only for trusted, secure environments when working on non-critical projects. If you're working with important files or using models of questionable capability, we strongly recommend using `kode --safe` to enable permission checks and manual approval for all operations.
> 
> **📊 Model Performance**: For optimal performance, we recommend using newer, more capable models designed for autonomous task completion. Avoid older Q&A-focused models like GPT-4o or Gemini 2.5 Pro, which are optimized for answering questions rather than sustained independent task execution. Choose models specifically trained for agentic workflows and extended reasoning capabilities.

## Network & Privacy

- Kode does not send product telemetry/analytics by default.
- Network requests happen only when you explicitly use networked features:
  - Model provider requests (Anthropic/OpenAI-compatible endpoints you configure)
  - Web tools (`WebFetch`, `WebSearch`)
  - Plugin marketplace downloads (GitHub/URL sources) and OAuth flows (when used)
  - Optional update checks (opt-in via `autoUpdaterStatus: enabled`)

<img width="600" height="577" alt="image" src="https://github.com/user-attachments/assets/8b46a39d-1ab6-4669-9391-14ccc6c5234c" />

## Features

### Core Capabilities
- 🤖 **AI-Powered Assistance** - Uses advanced AI models to understand and respond to your requests
- 🔄 **Multi-Model Collaboration** - Flexibly switch and combine multiple AI models to leverage their unique strengths
- 🦜 **Expert Model Consultation** - Use `@ask-model-name` to consult specific AI models for specialized analysis
- 👤 **Intelligent Agent System** - Use `@run-agent-name` to delegate tasks to specialized subagents
- 📝 **Code Editing** - Directly edit files with intelligent suggestions and improvements
- 🔍 **Codebase Understanding** - Analyzes your project structure and code relationships
- 🚀 **Command Execution** - Run shell commands and see results in real-time
- 🛠️ **Workflow Automation** - Handle complex development tasks with simple prompts

### Authoring Comfort
- `Option+G` (Alt+G) opens your message in your preferred editor (respects `$EDITOR`/`$VISUAL`; falls back to code/nano/vim/notepad) and returns the text to the prompt when you close it.
- `Option+Enter` inserts a newline inside the prompt without sending; plain Enter submits. `Option+M` cycles the active model.

### 🎯 Advanced Intelligent Completion System
Our state-of-the-art completion system provides unparalleled coding assistance:

#### Smart Fuzzy Matching
- **Hyphen-Aware Matching** - Type `dao` to match `run-agent-dao-qi-harmony-designer`
- **Abbreviation Support** - `dq` matches `dao-qi`, `nde` matches `node`
- **Numeric Suffix Handling** - `py3` intelligently matches `python3`
- **Multi-Algorithm Fusion** - Combines 7+ matching algorithms for best results

#### Intelligent Context Detection
- **No @ Required** - Type `gp5` directly to match `@ask-gpt-5`
- **Auto-Prefix Addition** - Tab/Enter automatically adds `@` for agents and models
- **Mixed Completion** - Seamlessly switch between commands, files, agents, and models
- **Smart Prioritization** - Results ranked by relevance and usage frequency

#### Unix Command Optimization
- **500+ Common Commands** - Curated database of frequently used Unix/Linux commands
- **System Intersection** - Only shows commands that actually exist on your system
- **Priority Scoring** - Common commands appear first (git, npm, docker, etc.)
- **Real-time Loading** - Dynamic command discovery from system PATH

### User Experience
- 🎨 **Interactive UI** - Beautiful terminal interface with syntax highlighting
- 🔌 **Tool System** - Extensible architecture with specialized tools for different tasks
- 💾 **Context Management** - Smart context handling to maintain conversation continuity
- 📋 **AGENTS.md Integration** - Use `# documentation requests` to auto-generate and maintain project documentation

## Installation

```bash
npm install -g @shareai-lab/kode
```

> **🇨🇳 For users in China**: If you encounter network issues, use a mirror registry:
> ```bash
> npm install -g @shareai-lab/kode --registry=https://registry.npmmirror.com
> ```

Dev channel (latest features):

```bash
npm install -g @shareai-lab/kode@dev
```

After installation, you can use any of these commands:
- `kode` - Primary command
- `kwa` - Kode With Agent (alternative)
- `kd` - Ultra-short alias

### Native binaries (Windows OOTB)

- No WSL/Git Bash required.
- On `postinstall`, Kode will best-effort download a native binary from GitHub Releases into `${KODE_BIN_DIR:-~/.kode/bin}/<version>/<platform>-<arch>/kode(.exe)`.
- The wrapper (`cli.js`) prefers the native binary and falls back to the Node.js runtime (`node dist/index.js`) when needed.

Overrides:
- Mirror downloads: `KODE_BINARY_BASE_URL`
- Disable download: `KODE_SKIP_BINARY_DOWNLOAD=1`
- Cache directory: `KODE_BIN_DIR`

See `docs/binary-distribution.md`.

### Configuration / API keys

- Global config (models, pointers, theme, etc): `~/.kode.json` (or `<KODE_CONFIG_DIR>/config.json` when `KODE_CONFIG_DIR`/`CLAUDE_CONFIG_DIR` is set).
- Project/local settings (output style, etc): `./.kode/settings.json` and `./.kode/settings.local.json` (legacy `.claude` is supported for some features).
- Configure models via `/model` (UI) or `kode models import/export` (YAML). Details: `docs/develop/configuration.md`.

## Usage

### Interactive Mode
Start an interactive session:
```bash
kode
# or
kwa
# or
kd
```

### Non-Interactive Mode
Get a quick response:
```bash
kode -p "explain this function" path/to/file.js
# or
kwa -p "explain this function" path/to/file.js
```

### ACP (Agent Client Protocol)

Run Kode as an ACP agent server (stdio JSON-RPC), for clients like Toad/Zed:

```bash
kode-acp
# or
kode --acp
```

Toad example:

```bash
toad acp "kode-acp"
```

More: `docs/acp.md`.

### Using the @ Mention System

Kode supports a powerful @ mention system for intelligent completions:

#### 🦜 Expert Model Consultation
```bash
# Consult specific AI models for expert opinions
@ask-claude-sonnet-4 How should I optimize this React component for performance?
@ask-gpt-5 What are the security implications of this authentication method?
@ask-o1-preview Analyze the complexity of this algorithm
```

#### 👤 Specialized Agent Delegation  
```bash
# Delegate tasks to specialized subagents
@run-agent-simplicity-auditor Review this code for over-engineering
@run-agent-architect Design a microservices architecture for this system
@run-agent-test-writer Create comprehensive tests for these modules
```

#### 📁 Smart File References
```bash
# Reference files and directories with auto-completion
@packages/core/src/query/index.ts
@docs/README.md
@.env.example
```

The @ mention system provides intelligent completions as you type, showing available models, agents, and files.

### MCP Servers (Extensions)

Kode can connect to MCP servers to extend tools and context.

- Config files: `.mcp.json` (recommended) or `.mcprc` in your project root. See `docs/mcp.md`.
- CLI:

```bash
kode mcp add
kode mcp list
kode mcp get <name>
kode mcp remove <name>
```

Example `.mcprc`:

```json
{
  "my-sse-server": { "type": "sse", "url": "http://127.0.0.1:3333/sse" }
}
```

### Permissions & Approvals

- Default mode skips most prompts for speed.
- Safe mode: `kode --safe` requires approval for Bash commands and file writes/edits.
- Plan mode: the assistant may ask to enter plan mode to draft a plan file; while in plan mode, only read-only/planning tools (and the plan file) are allowed until you approve exiting plan mode.

### Paste & Images

- Multi-line/large paste is inserted as a placeholder and expanded on submit.
- Pasting multiple existing file paths inserts `@path` mentions automatically (quoted when needed).
- Image paste (macOS): press `Ctrl+V` to attach clipboard images; you can paste multiple images before sending.

### System Sandbox (Linux)

- In safe mode (or with `KODE_SYSTEM_SANDBOX=1`), agent-triggered Bash tool calls try to run inside a `bwrap` sandbox when available.
- Network is disabled by default; set `KODE_SYSTEM_SANDBOX_NETWORK=inherit` to allow network.
- Set `KODE_SYSTEM_SANDBOX=required` to fail closed if sandbox cannot be started.
- See `docs/system-sandbox.md` for details and platform notes.

### Troubleshooting

- Models: use `/model`, or `kode models import kode-models.yaml`, and ensure required API key env vars exist.
- Windows: if the native binary download is blocked/offline, set `KODE_BINARY_BASE_URL` (mirror) or `KODE_SKIP_BINARY_DOWNLOAD=1` (skip download); the wrapper will fall back to the Node.js runtime (`dist/index.js`).
- MCP: use `kode mcp list` to check server status; tune `MCP_CONNECTION_TIMEOUT_MS`, `MCP_SERVER_CONNECTION_BATCH_SIZE`, and `MCP_TOOL_TIMEOUT` if servers are slow.
- Sandbox: install `bwrap` (bubblewrap) on Linux, or set `KODE_SYSTEM_SANDBOX=0` to disable.

### AGENTS.md Documentation Mode

Use the `#` prefix to generate and maintain your AGENTS.md documentation:

```bash
# Generate setup instructions
# How do I set up the development environment?

# Create testing documentation  
# What are the testing procedures for this project?

# Document deployment process
# Explain the deployment pipeline and requirements
```

This mode automatically formats responses as structured documentation and appends them to your AGENTS.md file.

### Docker Usage

#### Alternative: Build from local source

```bash
# Clone the repository
git clone https://github.com/shareAI-lab/Kode.git
cd Kode

# Build the image locally
docker build --no-cache -t kode .

# Run in your project directory
cd your-project
docker run -it --rm \
  -v $(pwd):/workspace \
  -v ~/.kode:/root/.kode \
  -v ~/.kode.json:/root/.kode.json \
  -w /workspace \
  kode
```

#### Docker Configuration Details

The Docker setup includes:

- **Volume Mounts**:
  - `$(pwd):/workspace` - Mounts your current project directory
  - `~/.kode:/root/.kode` - Preserves your kode configuration directory between runs
  - `~/.kode.json:/root/.kode.json` - Preserves your kode global configuration file between runs

- **Working Directory**: Set to `/workspace` inside the container

- **Interactive Mode**: Uses `-it` flags for interactive terminal access

- **Cleanup**: `--rm` flag removes the container after exit

**Note**: Kode uses both `~/.kode` directory for additional data (like memory files) and `~/.kode.json` file for global configuration.

The first time you run the Docker command, it will build the image. Subsequent runs will use the cached image for faster startup.

You can use the onboarding to set up the model, or `/model`.
If you don't see the models you want on the list, you can manually set them in `/config`
As long as you have an openai-like endpoint, it should work.

### Commands

- `/help` - Show available commands
- `/model` - Change AI model settings
- `/config` - Open configuration panel
- `/agents` - Manage subagents
- `/output-style` - Set the output style
- `/statusline` - Configure a custom status line command
- `/cost` - Show token usage and costs
- `/clear` - Clear conversation history
- `/init` - Initialize project context
- `/plugin` - Manage plugins/marketplaces (skills, commands)

## Agents / Subagents

Kode supports subagents (agent templates) for delegation and task orchestration.

- Agents are loaded from `.kode/agents` and `.claude/agents` (user + project), plus plugins/policy and `--agents`.
- Manage in the UI: `/agents` (creates new agents under `./.claude/agents` / `~/.claude/agents` by default).
- Run via mentions: `@run-agent-<agentType> ...`
- Run via tooling: `Task(subagent_type: "<agentType>", ...)`
- CLI flags: `--agents <json>` (inject agents for this run), `--setting-sources user,project,local` (control which sources are loaded)

Minimal agent file example (`./.kode/agents/reviewer.md`):

```md
---
name: reviewer
description: "Review diffs for correctness, security, and simplicity"
tools: ["Read", "Grep"]
model: inherit
---

Be strict. Point out bugs and risky changes. Prefer small, targeted fixes.
```

Model field notes:
- Compatibility aliases: `inherit`, `opus`, `sonnet`, `haiku` (mapped to model pointers)
- Kode selectors (via `/model`): pointers (`main|task|compact|quick`), profile name, modelName, or `provider:modelName` (e.g. `openai:o3`)

Validate agent templates:

```bash
kode agents validate
```

See `docs/agents-system.md`.

## Skills & Plugins

Kode supports the [Agent Skills](https://agentskills.io) open format for extending agent capabilities:
- **Agent Skills** format (`SKILL.md`) - see [specification](https://agentskills.io/specification)
- **Marketplace compatibility** (`.kode-plugin/marketplace.json`, legacy `.claude-plugin/marketplace.json`)
- **Install from any repository** using [`add-skill` CLI](https://github.com/vercel-labs/add-skill)

### Quick install with add-skill

Install skills from any git repository:

```bash
# Install from GitHub
npx add-skill vercel-labs/agent-skills -a kode

# Install to global directory
npx add-skill vercel-labs/agent-skills -a kode -g

# Install specific skills
npx add-skill vercel-labs/agent-skills -a kode -s pdf -s xlsx
```

### Install skills from a marketplace

```bash
# Add a marketplace (local path, GitHub owner/repo, or URL)
kode plugin marketplace add ./path/to/marketplace-repo
kode plugin marketplace add owner/repo
kode plugin marketplace list

# Install a plugin pack (installs skills/commands)
kode plugin install document-skills@anthropic-agent-skills --scope user

# Project-scoped install (writes to ./.kode/...)
kode plugin install document-skills@anthropic-agent-skills --scope project

# Disable/enable an installed plugin
kode plugin disable document-skills@anthropic-agent-skills --scope user
kode plugin enable document-skills@anthropic-agent-skills --scope user
```

Interactive equivalents:

```text
/plugin marketplace add owner/repo
/plugin install document-skills@anthropic-agent-skills --scope user
```

### Use skills

- In interactive mode, run a skill as a slash command: `/pdf`, `/xlsx`, etc.
- Kode can also invoke skills automatically via the `Skill` tool when relevant.

### Create a skill (Agent Skills)

Create `./.kode/skills/<skill-name>/SKILL.md` (project) or `~/.kode/skills/<skill-name>/SKILL.md` (user):

```md
---
name: my-skill
description: Describe what this skill does and when to use it.
allowed-tools: Read Bash(git:*) Bash(jq:*)
---

# Skill instructions
```

Naming rules:
- `name` must match the folder name
- Lowercase letters/numbers/hyphens only, 1–64 chars

Compatibility:
- Kode also discovers `.claude/skills` and `.claude/commands` for legacy compatibility.

### Distribute skills

- Marketplace repo: publish a repo containing `.kode-plugin/marketplace.json` listing plugin packs and their `skills` directories (legacy `.claude-plugin/marketplace.json` is also supported).
- Plugin repo: for full plugins (beyond skills), include `.kode-plugin/plugin.json` at the plugin root and keep all paths relative (`./...`).

See `docs/skills.md` for a compact reference and examples.

### Output styles

Use output styles to switch system-prompt behavior.

- Select: `/output-style` (menu) or `/output-style <style>`
- Built-ins: `default`, `Explanatory`, `Learning`
- Stored per-project in `./.kode/settings.local.json` as `outputStyle` (legacy `.claude/settings.local.json` is supported)
- Custom styles: Markdown files under `output-styles/` in `.claude`/`.kode` user + project locations
- Plugins can provide styles under `output-styles/` (or manifest `outputStyles`); plugin styles are namespaced as `<plugin>:<style>`

See `docs/output-styles.md`.

## Multi-Model Intelligent Collaboration

Unlike single-model CLIs, Kode implements **true multi-model collaboration**, allowing you to fully leverage the unique strengths of different AI models.

### 🏗️ Core Technical Architecture

#### 1. **ModelManager Multi-Model Manager**
We designed a unified `ModelManager` system that supports:
- **Model Profiles**: Each model has an independent configuration file containing API endpoints, authentication, context window size, cost parameters, etc.
- **Model Pointers**: Users can configure default models for different purposes in the `/model` command:
  - `main`: Default model for main Agent
  - `task`: Default model for SubAgent
  - `compact`: Model used for automatic context compression when nearing the context window
  - `quick`: Fast model for simple operations and utilities
- **Dynamic Model Switching**: Support runtime model switching without restarting sessions, maintaining context continuity

#### 📦 Shareable Model Config (YAML)

You can export/import model profiles + pointers as a team-shareable YAML file. By default, exports do **not** include plaintext API keys (use env vars instead).

```bash
# Export to a file (or omit --output to print to stdout)
kode models export --output kode-models.yaml

# Import (merge by default)
kode models import kode-models.yaml

# Replace existing profiles instead of merging
kode models import --replace kode-models.yaml

# List configured profiles + pointers
kode models list
```

Example `kode-models.yaml`:

```yaml
version: 1
profiles:
  - name: OpenAI Main
    provider: openai
    modelName: gpt-4o
    maxTokens: 8192
    contextLength: 128000
    apiKey:
      fromEnv: OPENAI_API_KEY
pointers:
  main: gpt-4o
  task: gpt-4o
  compact: gpt-4o
  quick: gpt-4o
```

#### 2. **TaskTool Intelligent Task Distribution**
Our specially designed `TaskTool` (Architect tool) implements:
- **Subagent Mechanism**: Can launch multiple sub-agents to process tasks in parallel
- **Model Parameter Passing**: Users can specify which model SubAgents should use in their requests
- **Default Model Configuration**: SubAgents use the model configured by the `task` pointer by default

#### 3. **AskExpertModel Expert Consultation Tool**
We specially designed the `AskExpertModel` tool:
- **Expert Model Invocation**: Allows temporarily calling specific expert models to solve difficult problems during conversations
- **Model Isolation Execution**: Expert model responses are processed independently without affecting the main conversation flow
- **Knowledge Integration**: Integrates expert model insights into the current task

#### 🎯 Flexible Model Switching
- **Option+M Quick Switch**: Press Option+M in the input box to cycle the main conversation model
- **`/model` Command**: Use `/model` command to configure and manage multiple model profiles, set default models for different purposes
- **User Control**: Users can specify specific models for task processing at any time

#### 🔄 Intelligent Work Allocation Strategy

**Architecture Design Phase**
- Use **o3 model** or **GPT-5 model** to explore system architecture and formulate sharp and clear technical solutions
- These models excel in abstract thinking and system design

**Solution Refinement Phase**
- Use **gemini model** to deeply explore production environment design details
- Leverage its deep accumulation in practical engineering and balanced reasoning capabilities

**Code Implementation Phase**
- Use **Qwen Coder model**, **Kimi k2 model**, **GLM-4.5 model**, or **Claude Sonnet 4 model** for specific code writing
- These models have strong performance in code generation, file editing, and engineering implementation
- Support parallel processing of multiple coding tasks through subagents

**Problem Solving**
- When encountering complex problems, consult expert models like **o3 model**, **Claude Opus 4.1 model**, or **Grok 4 model**
- Obtain deep technical insights and innovative solutions

#### 💡 Practical Application Scenarios

```bash
# Example 1: Architecture Design
"Use o3 model to help me design a high-concurrency message queue system architecture"

# Example 2: Multi-Model Collaboration
"First use GPT-5 model to analyze the root cause of this performance issue, then use Claude Sonnet 4 model to write optimization code"

# Example 3: Parallel Task Processing
"Use Qwen Coder model as subagent to refactor these three modules simultaneously"

# Example 4: Expert Consultation
"This memory leak issue is tricky, ask Claude Opus 4.1 model separately for solutions"

# Example 5: Code Review
"Have Kimi k2 model review the code quality of this PR"

# Example 6: Complex Reasoning
"Use Grok 4 model to help me derive the time complexity of this algorithm"

# Example 7: Solution Design
"Have GLM-4.5 model design a microservice decomposition plan"
```

### 🛠️ Key Implementation Mechanisms

#### **Configuration System**
```typescript
// Example of multi-model configuration support
{
  "modelProfiles": [
    { "name": "o3", "provider": "openai", "modelName": "o3", "apiKey": "...", "maxTokens": 1024, "contextLength": 128000, "isActive": true, "createdAt": 1710000000000 },
    { "name": "qwen", "provider": "alibaba", "modelName": "qwen-coder", "apiKey": "...", "maxTokens": 1024, "contextLength": 128000, "isActive": true, "createdAt": 1710000000001 }
  ],
  "modelPointers": {
    "main": "o3",           // Main conversation model
    "task": "qwen-coder",   // Sub-agent model
    "compact": "o3",        // Context compression model
    "quick": "o3"           // Quick operations model
  }
}
```

#### **Cost Tracking System**
- **Usage Statistics**: Use `/cost` command to view token usage and costs for each model
- **Multi-Model Cost Comparison**: Track usage costs of different models in real-time
- **History Records**: Save cost data for each session

#### **Context Manager**
- **Context Inheritance**: Maintain conversation continuity when switching models
- **Context Window Adaptation**: Automatically adjust based on different models' context window sizes
- **Session State Preservation**: Ensure information consistency during multi-model collaboration

### 🚀 Advantages of Multi-Model Collaboration

1. **Maximized Efficiency**: Each task is handled by the most suitable model
2. **Cost Optimization**: Use lightweight models for simple tasks, powerful models for complex tasks
3. **Parallel Processing**: Multiple models can work on different subtasks simultaneously
4. **Flexible Switching**: Switch models based on task requirements without restarting sessions
5. **Leveraging Strengths**: Combine advantages of different models for optimal overall results

### 📊 Comparison (Single-model CLI)

| Feature | Kode | Single-model CLI |
|---------|------|-----------------|
| Number of Supported Models | Unlimited, configurable for any model | Only supports one model |
| Model Switching | ✅ Option+M quick switch | ❌ Requires session restart |
| Parallel Processing | ✅ Multiple SubAgents work in parallel | ❌ Single-threaded processing |
| Cost Tracking | ✅ Separate statistics for multiple models | ❌ Single model cost |
| Task Model Configuration | ✅ Different default models for different purposes | ❌ Same model for all tasks |
| Expert Consultation | ✅ AskExpertModel tool | ❌ Not supported |

This multi-model collaboration capability makes Kode a true **AI Development Workbench**, not just a single AI assistant.

## Development

Kode is built with modern tools and requires [Bun](https://bun.sh) for development.

### Install Bun

```bash
# macOS/Linux
curl -fsSL https://bun.sh/install | bash

# Windows
powershell -c "irm bun.sh/install.ps1 | iex"
```

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/shareAI-lab/kode.git
cd kode

# Install dependencies
bun install

# Run in development mode
bun run dev
```

### Build

```bash
bun run build
```

### Testing

```bash
# Run tests
bun test

# Test the CLI
./cli.js --help
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

Apache 2.0 License - see [LICENSE](LICENSE) for details.

## Thanks

- Some code from @dnakov's anonkode
- Some UI learned from gemini-cli  
- Some system design learned from upstream agent CLIs

## Support

- 📚 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/shareAI-lab/kode/issues)
- 💬 [Discussions](https://github.com/shareAI-lab/kode/discussions)
