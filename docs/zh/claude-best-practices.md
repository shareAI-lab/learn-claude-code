# Claude Code 最佳实践 / Best Practices for Claude Code

> 原文链接：https://code.claude.com/docs/en/best-practices

---

## 简介 / Introduction

**English:**

Claude Code is an agentic coding environment. Unlike a chatbot that answers questions and waits, Claude Code can read your files, run commands, make changes, and autonomously work through problems while you watch, redirect, or step away entirely.

This changes how you work. Instead of writing code yourself and asking Claude to review it, you describe what you want and Claude figures out how to build it. Claude explores, plans, and implements.

But this autonomy still comes with a learning curve. Claude works within certain constraints you need to understand.

**中文：**

Claude Code 是一个代理式编码环境。与只会回答问题然后等待的聊天机器人不同，Claude Code 可以读取您的文件、运行命令、进行更改，并在您观看、重定向或完全离开时自主解决问题。

这改变了您的工作方式。您不再需要自己编写代码然后让 Claude 审查，而是描述您想要什么，Claude 会弄清楚如何构建它。Claude 会探索、规划和实现。

但这种自主性仍然存在学习曲线。Claude 在某些约束条件下工作，您需要理解这些约束。

---

## 上下文窗口管理 / Context Window Management

**English:**

Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills.

Claude's context window holds your entire conversation, including every message, every file Claude reads, and every command output. However, this can fill up fast. A single debugging session or codebase exploration might generate and consume tens of thousands of tokens.

This matters since LLM performance degrades as context fills. When the context window is getting full, Claude may start "forgetting" earlier instructions or making more mistakes. The context window is the most important resource to manage.

**中文：**

大多数最佳实践都基于一个约束：Claude 的上下文窗口填充得很快，并且随着填充性能会下降。

Claude 的上下文窗口保存您的整个对话，包括每条消息、Claude 读取的每个文件以及每个命令输出。然而，这可能会很快填满。一次调试会话或代码库探索可能会生成并消耗数万个 token。

这很重要，因为 LLM 的性能会随着上下文填充而下降。当上下文窗口快满时，Claude 可能开始"忘记"之前的指令或犯更多错误。上下文窗口是需要管理的最重要资源。

---

## 给 Claude 验证工作的方法 / Give Claude a Way to Verify Its Work

**English:**

Claude performs dramatically better when it can verify its own work, like run tests, compare screenshots, and validate outputs.

Without clear success criteria, it might produce something that looks right but actually doesn't work. You become the only feedback loop, and every mistake requires your attention.

**中文：**

当 Claude 能够验证自己的工作时，比如运行测试、比较截图和验证输出，它的表现会显著更好。

如果没有明确的成功标准，它可能会产生看起来正确但实际上不起作用的东西。您成为唯一的反馈循环，每个错误都需要您的关注。

---

### 策略对比表 / Strategy Comparison Table

| 策略 / Strategy | 之前 / Before | 之后 / After |
|-----------------|---------------|--------------|
| **提供验证标准** / Provide verification criteria | "implement a function that validates email addresses" | "write a validateEmail function. example test cases: user@example.com is true, invalid is false, user@.com is false. run the tests after implementing" |
| **视觉验证 UI 更改** / Verify UI changes visually | "make the dashboard look better" | "[paste screenshot] implement this design. take a screenshot of the result and compare it to the original. list differences and fix them" |
| **解决根本原因，而非症状** / Address root causes, not symptoms | "the build is failing" | "the build fails with this error: [paste error]. fix it and verify the build succeeds. address the root cause, don't suppress the error" |

**中文对照：**

| 策略 | 之前 | 之后 |
|------|------|------|
| **提供验证标准** | "实现一个验证电子邮件地址的函数" | "编写一个 validateEmail 函数。示例测试用例：user@example.com 为 true，invalid 为 false，user@.com 为 false。实现后运行测试" |
| **视觉验证 UI 更改** | "让仪表板看起来更好" | "[粘贴截图] 实现这个设计。截取结果截图并与原始截图比较。列出差异并修复它们" |
| **解决根本原因，而非症状** | "构建失败" | "构建失败，错误如下：[粘贴错误]。修复它并验证构建成功。解决根本原因，不要抑制错误" |

---

**English:**

UI changes can be verified using the Claude in Chrome extension. It opens new tabs in your browser, tests the UI, and iterates until the code works.

Your verification can also be a test suite, a linter, or a Bash command that checks output. Invest in making your verification rock-solid.

**中文：**

UI 更改可以使用 Claude in Chrome 扩展进行验证。它会在浏览器中打开新标签页，测试 UI，并迭代直到代码正常工作。

您的验证也可以是测试套件、linter 或检查输出的 Bash 命令。投入精力使您的验证坚如磐石。

---

## 先探索，再规划，最后编码 / Explore First, Then Plan, Then Code

**English:**

Letting Claude jump straight to coding can produce code that solves the wrong problem. Use Plan Mode to separate exploration from execution.

The recommended workflow has four phases:

1. **Explore** - Understand the codebase
2. **Plan** - Design the solution
3. **Code** - Implement the solution
4. **Verify** - Test and validate

**中文：**

让 Claude 直接开始编码可能会产生解决错误问题的代码。使用计划模式将探索与执行分开。

推荐的工作流程有四个阶段：

1. **探索 / Explore** - 理解代码库
2. **规划 / Plan** - 设计解决方案
3. **编码 / Code** - 实现解决方案
4. **验证 / Verify** - 测试和验证

---

## 在提示中提供具体上下文 / Provide Specific Context in Your Prompts

**English:**

Claude can infer intent, but it can't read your mind. Reference specific files, mention constraints, and point to example patterns.

**中文：**

Claude 可以推断意图，但它无法读懂您的想法。引用具体文件，提及约束条件，并指向示例模式。

---

### 策略对比表 / Strategy Comparison Table

| 策略 / Strategy | 之前 / Before | 之后 / After |
|-----------------|---------------|--------------|
| **界定任务范围** / Scope the task | "add tests for foo.py" | "write a test for foo.py covering the edge case where the user is logged out. avoid mocks." |
| **指向来源** / Point to sources | "why does ExecutionFactory have such a weird api?" | "look through ExecutionFactory's git history and summarize how its api came to be" |
| **引用现有模式** / Reference existing patterns | "add a calendar widget" | "look at how existing widgets are implemented on the home page to understand the patterns. HotDogWidget.php is a good example. follow the pattern to implement a new calendar widget that lets the user select a month and paginate forwards/backwards to pick a year. build from scratch without libraries other than the ones already used in the codebase." |
| **描述症状** / Describe the symptom | "fix the login bug" | "users report that login fails after session timeout. check the auth flow in src/auth/, especially token refresh. write a failing test that reproduces the issue, then fix it" |

**中文对照：**

| 策略 | 之前 | 之后 |
|------|------|------|
| **界定任务范围** | "为 foo.py 添加测试" | "为 foo.py 编写测试，覆盖用户登出的边缘情况。避免使用 mock。" |
| **指向来源** | "为什么 ExecutionFactory 的 API 这么奇怪？" | "查看 ExecutionFactory 的 git 历史，总结其 API 是如何形成的" |
| **引用现有模式** | "添加一个日历小部件" | "查看主页上现有小部件的实现方式来理解模式。HotDogWidget.php 是一个很好的例子。按照该模式实现一个新的日历小部件，让用户可以选择月份并向前/向后翻页选择年份。从头构建，不使用代码库中已有的库之外的其他库。" |
| **描述症状** | "修复登录 bug" | "用户报告会话超时后登录失败。检查 src/auth/ 中的认证流程，特别是 token 刷新。编写一个失败的测试来重现问题，然后修复它" |

---

**English:**

Vague prompts can be useful when you're exploring and can afford to course-correct. A prompt like "what would you improve in this file?" can surface things you wouldn't have thought to ask about.

**中文：**

当您在探索并且可以承受纠正方向时，模糊的提示可能很有用。像"你会在这个文件中改进什么？"这样的提示可以发现您没想到要询问的事情。

---

## 提供丰富内容 / Provide Rich Content

**English:**

You can provide rich data to Claude in several ways:

- Reference files with `@` instead of describing where code lives. Claude reads the file before responding.
- Paste images directly. Copy/paste or drag and drop images into the prompt.
- Give URLs for documentation and API references. Use `/permissions` to allowlist frequently-used domains.
- Pipe in data by running `cat error.log | claude` to send file contents directly.
- Let Claude fetch what it needs. Tell Claude to pull context itself using Bash commands, MCP tools, or by reading files.

**中文：**

您可以通过多种方式向 Claude 提供丰富的数据：

- 使用 `@` 引用文件，而不是描述代码在哪里。Claude 会在响应之前读取文件。
- 直接粘贴图像。复制/粘贴或将图像拖放到提示中。
- 提供文档和 API 参考的 URL。使用 `/permissions` 将常用域名加入白名单。
- 通过运行 `cat error.log | claude` 管道传输数据，直接发送文件内容。
- 让 Claude 获取它需要的内容。告诉 Claude 使用 Bash 命令、MCP 工具或读取文件来自己拉取上下文。

---

## 配置环境 / Configure Your Environment

**English:**

A few setup steps make Claude Code significantly more effective across all your sessions. For a full overview of extension features and when to use each one, see Extend Claude Code.

**中文：**

几个设置步骤可以让 Claude Code 在您的所有会话中显著更有效。有关扩展功能的完整概述以及何时使用每个功能，请参阅 Extend Claude Code。

---

## 编写有效的 CLAUDE.md / Write an Effective CLAUDE.md

**English:**

CLAUDE.md is a special file that Claude reads at the start of every conversation. Include Bash commands, code style, and workflow rules. This gives Claude persistent context it can't infer from code alone.

The `/init` command analyzes your codebase to detect build systems, test frameworks, and code patterns, giving you a solid foundation to refine.

There's no required format for CLAUDE.md files, but keep it short and human-readable.

**中文：**

CLAUDE.md 是一个特殊文件，Claude 在每次对话开始时都会读取它。包含 Bash 命令、代码风格和工作流规则。这为 Claude 提供了无法仅从代码推断的持久上下文。

`/init` 命令分析您的代码库以检测构建系统、测试框架和代码模式，为您提供一个坚实的基础进行完善。

CLAUDE.md 文件没有必需的格式，但请保持简短和人类可读。

---

### CLAUDE.md 示例 / Example

```markdown
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance
```

---

**English:**

CLAUDE.md is loaded every session, so only include things that apply broadly. For domain knowledge or workflows that are only relevant sometimes, use skills instead. Claude loads them on demand without bloating every conversation.

Keep it concise. For each line, ask: "Would removing this cause Claude to make mistakes?" If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!

**中文：**

CLAUDE.md 在每个会话中都会加载，所以只包含广泛适用的内容。对于仅有时相关的领域知识或工作流，请改用 skills。Claude 按需加载它们，不会使每次对话膨胀。

保持简洁。对于每一行，问自己："删除这行会导致 Claude 犯错吗？"如果不会，就删掉它。臃肿的 CLAUDE.md 文件会导致 Claude 忽略您的实际指令！

---

### 应包含 vs 不应包含 / Include vs Exclude

| ✅ 应包含 / Include | ❌ 不应包含 / Exclude |
|---------------------|------------------------|
| Claude 无法猜测的 Bash 命令 / Bash commands Claude can't guess | Claude 可以通过阅读代码弄清楚的内容 / Anything Claude can figure out by reading code |
| 与默认值不同的代码风格规则 / Code style rules that differ from defaults | Claude 已经知道的标准语言约定 / Standard language conventions Claude already knows |
| 测试说明和首选测试运行器 / Testing instructions and preferred test runners | 详细的 API 文档（改为链接到文档）/ Detailed API documentation (link to docs instead) |
| 仓库礼仪（分支命名、PR 约定）/ Repository etiquette (branch naming, PR conventions) | 频繁变化的信息 / Information that changes frequently |
| 特定于项目的架构决策 / Architectural decisions specific to your project | 长篇解释或教程 / Long explanations or tutorials |
| 开发环境 quirks（必需的环境变量）/ Developer environment quirks (required env vars) | 逐文件描述代码库 / File-by-file descriptions of the codebase |
| 常见的陷阱或不明显的行为 / Common gotchas or non-obvious behaviors | 显而易见的做法，如"编写干净的代码" / Self-evident practices like "write clean code" |

---

**English:**

If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost. If Claude asks you questions that are answered in CLAUDE.md, the phrasing might be ambiguous. Treat CLAUDE.md like code: review it when things go wrong, prune it regularly, and test changes by observing whether Claude's behavior actually shifts.

You can tune instructions by adding emphasis (e.g., "IMPORTANT" or "YOU MUST") to improve adherence. Check CLAUDE.md into git so your team can contribute. The file compounds in value over time.

**中文：**

如果 Claude 尽管有禁止规则但仍然做您不想要的事情，文件可能太长了，规则被淹没了。如果 Claude 问您在 CLAUDE.md 中已经回答的问题，措辞可能模糊。把 CLAUDE.md 当作代码对待：出问题时审查它，定期修剪它，并通过观察 Claude 的行为是否实际改变来测试更改。

您可以通过添加强调（例如"IMPORTANT"或"YOU MUST"）来调整指令以提高遵守度。将 CLAUDE.md 提交到 git，以便您的团队可以贡献。这个文件的价值会随时间复利增长。

---

### CLAUDE.md 文件位置 / CLAUDE.md File Locations

**English:**

You can place CLAUDE.md files in several locations:

- **Home folder** (`~/.claude/CLAUDE.md`): applies to all Claude sessions
- **Project root** (`./CLAUDE.md`): check into git to share with your team
- **Parent directories**: useful for monorepos where both root/CLAUDE.md and root/foo/CLAUDE.md are pulled in automatically
- **Child directories**: Claude pulls in child CLAUDE.md files on demand when working with files in those directories

**中文：**

您可以将 CLAUDE.md 文件放在多个位置：

- **主文件夹** (`~/.claude/CLAUDE.md`): 适用于所有 Claude 会话
- **项目根目录** (`./CLAUDE.md`): 提交到 git 与团队共享
- **父目录**: 对于 monorepo 很有用，root/CLAUDE.md 和 root/foo/CLAUDE.md 都会自动被拉入
- **子目录**: Claude 在处理这些目录中的文件时按需拉入子 CLAUDE.md 文件

---

### CLAUDE.md 导入语法 / Import Syntax

**English:**

CLAUDE.md files can import additional files using `@path/to/import` syntax:

```markdown
See @README.md for project overview and @package.json for available npm commands.

# Additional Instructions
- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

**中文：**

CLAUDE.md 文件可以使用 `@path/to/import` 语法导入其他文件：

```markdown
参见 @README.md 了解项目概述，@package.json 了解可用的 npm 命令。

# 附加说明
- Git 工作流: @docs/git-instructions.md
- 个人覆盖: @~/.claude/my-project-instructions.md
```

---

## 配置权限 / Configure Permissions

**English:**

By default, Claude Code requests permission for actions that might modify your system: file writes, Bash commands, MCP tools, etc. This is safe but tedious. After the tenth approval you're not really reviewing anymore, you're just clicking through. There are two ways to reduce these interruptions:

- **Permission allowlists**: permit specific tools you know are safe (like `npm run lint` or `git commit`)
- **Sandboxing**: enable OS-level isolation that restricts filesystem and network access, allowing Claude to work more freely within defined boundaries

Alternatively, use `--dangerously-skip-permissions` to bypass all permission checks for contained workflows like fixing lint errors or generating boilerplate.

**中文：**

默认情况下，Claude Code 会请求可能修改您系统的操作的权限：文件写入、Bash 命令、MCP 工具等。这很安全但很繁琐。第十次批准后，您实际上不再审查，只是点击通过。有两种方法可以减少这些中断：

- **权限白名单 / Permission allowlists**: 允许您知道安全的特定工具（如 `npm run lint` 或 `git commit`）
- **沙盒 / Sandboxing**: 启用操作系统级别的隔离，限制文件系统和网络访问，允许 Claude 在定义的边界内更自由地工作

或者，使用 `--dangerously-skip-permissions` 绕过所有权限检查，用于修复 lint 错误或生成样板代码等受限工作流。

---

## 使用 CLI 工具 / Use CLI Tools

**English:**

CLI tools are the most context-efficient way to interact with external services. If you use GitHub, install the `gh` CLI. Claude knows how to use it for creating issues, opening pull requests, and reading comments. Without `gh`, Claude can still use the GitHub API, but unauthenticated requests often hit rate limits.

Claude is also effective at learning CLI tools it doesn't already know. Try prompts like "Use 'foo-cli-tool --help' to learn about foo tool, then use it to solve A, B, C."

**中文：**

CLI 工具是与外部服务交互的最节省上下文的方式。如果您使用 GitHub，请安装 `gh` CLI。Claude 知道如何使用它来创建 issue、打开 pull request 和阅读评论。没有 `gh`，Claude 仍然可以使用 GitHub API，但未经身份验证的请求经常会达到速率限制。

Claude 也擅长学习它还不知道的 CLI 工具。尝试这样的提示："使用 'foo-cli-tool --help' 了解 foo 工具，然后用它来解决 A、B、C。"

---

## 连接 MCP 服务器 / Connect MCP Servers

**English:**

With MCP servers, you can ask Claude to implement features from issue trackers, query databases, analyze monitoring data, integrate designs from Figma, and automate workflows.

**中文：**

使用 MCP 服务器，您可以要求 Claude 从 issue 跟踪器实现功能、查询数据库、分析监控数据、集成 Figma 设计以及自动化工作流。

---

## 设置 Hooks / Set Up Hooks

**English:**

Hooks run scripts automatically at specific points in Claude's workflow. Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens.

Claude can write hooks for you. Try prompts like "Write a hook that runs eslint after every file edit" or "Write a hook that blocks writes to the migrations folder." Run `/hooks` for interactive configuration, or edit `.claude/settings.json` directly.

**中文：**

Hooks 在 Claude 工作流的特定点自动运行脚本。与建议性的 CLAUDE.md 指令不同，hooks 是确定性的，保证操作发生。

Claude 可以为您编写 hooks。尝试这样的提示："编写一个在每次文件编辑后运行 eslint 的 hook"或"编写一个阻止写入 migrations 文件夹的 hook"。运行 `/hooks` 进行交互式配置，或直接编辑 `.claude/settings.json`。

---

## 创建 Skills / Create Skills

**English:**

Skills extend Claude's knowledge with information specific to your project, team, or domain. Claude applies them automatically when relevant, or you can invoke them directly with `/skill-name`.

Create a skill by adding a directory with a SKILL.md to `.claude/skills/`:

**中文：**

Skills 用特定于您的项目、团队或领域的信息扩展 Claude 的知识。Claude 在相关时自动应用它们，或者您可以直接使用 `/skill-name` 调用它们。

通过在 `.claude/skills/` 中添加带有 SKILL.md 的目录来创建 skill：

---

### Skill 示例 / Example

```markdown
---
name: api-conventions
description: REST API design conventions for our services
---
# API Conventions
- Use kebab-case for URL paths
- Use camelCase for JSON properties
- Always include pagination for list endpoints
- Version APIs in the URL path (/v1/, /v2/)
```

---

**English:**

Skills can also define repeatable workflows you invoke directly. Use `disable-model-invocation: true` for workflows with side effects that you want to trigger manually.

Run `/fix-issue 1234` to invoke it.

**中文：**

Skills 也可以定义您直接调用的可重复工作流。对于有副作用且您想手动触发的工作流，使用 `disable-model-invocation: true`。

运行 `/fix-issue 1234` 来调用它。

---

### 可重复工作流 Skill 示例 / Repeatable Workflow Example

```markdown
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix the GitHub issue: $ARGUMENTS.

1. Use `gh issue view` to get the issue details
2. Understand the problem described in the issue
3. Search the codebase for relevant files
4. Implement the necessary changes to fix the issue
5. Write and run tests to verify the fix
6. Ensure code passes linting and type checking
7. Create a descriptive commit message
8. Push and create a PR
```

---

## 创建自定义 Subagents / Create Custom Subagents

**English:**

Subagents run in their own context with their own set of allowed tools. They're useful for tasks that read many files or need specialized focus without cluttering your main conversation.

**中文：**

Subagents 在自己的上下文中运行，拥有自己的一组允许工具。它们对于读取许多文件或需要专门关注而不混乱主对话的任务很有用。

---

### Subagent 示例 / Example

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review code for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure data handling

Provide specific line references and suggested fixes.
```

---

**English:**

Tell Claude to use subagents explicitly: "Use a subagent to review this code for security issues."

**中文：**

明确告诉 Claude 使用 subagents："使用 subagent 审查此代码的安全问题。"

---

## 安装插件 / Install Plugins

**English:**

Plugins bundle skills, hooks, subagents, and MCP servers into a single installable unit from the community and Anthropic. If you work with a typed language, install a code intelligence plugin to give Claude precise symbol navigation and automatic error detection after edits.

**中文：**

插件将 skills、hooks、subagents 和 MCP 服务器打包成来自社区和 Anthropic 的单个可安装单元。如果您使用类型化语言，请安装代码智能插件，为 Claude 提供精确的符号导航和编辑后的自动错误检测。

---

## 有效沟通 / Communicate Effectively

**English:**

The way you communicate with Claude Code significantly impacts the quality of results.

**中文：**

您与 Claude Code 沟通的方式显著影响结果的质量。

---

### 询问代码库问题 / Ask Codebase Questions

**English:**

When onboarding to a new codebase, use Claude Code for learning and exploration. You can ask Claude the same sorts of questions you would ask another engineer:

- How does logging work?
- How do I make a new API endpoint?
- What does `async move { ... }` do on line 134 of foo.rs?
- What edge cases does CustomerOnboardingFlowImpl handle?
- Why does this code call `foo()` instead of `bar()` on line 333?

Using Claude Code this way is an effective onboarding workflow, improving ramp-up time and reducing load on other engineers. No special prompting required: ask questions directly.

**中文：**

当入职新代码库时，使用 Claude Code 进行学习和探索。您可以向 Claude 询问您会问另一位工程师的同类问题：

- 日志是如何工作的？
- 如何创建新的 API 端点？
- foo.rs 第 134 行的 `async move { ... }` 做什么？
- CustomerOnboardingFlowImpl 处理哪些边缘情况？
- 为什么这段代码在第 333 行调用 `foo()` 而不是 `bar()`？

以这种方式使用 Claude Code 是一种有效的入职工作流，可以缩短上手时间并减少其他工程师的负担。不需要特殊提示：直接提问即可。

---

### 让 Claude 采访您 / Let Claude Interview You

**English:**

Claude asks about things you might not have considered yet, including technical implementation, UI/UX, edge cases, and tradeoffs.

```
I want to build [introduction]. Interview me in detail using the AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs. Don't ask obvious questions, dig into the hard parts I might not have considered.

Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```

Once the spec is complete, start a fresh session to execute it. The new session has clean context focused entirely on implementation, and you have a written spec to reference.

**中文：**

Claude 会询问您可能还没有考虑过的事情，包括技术实现、UI/UX、边缘情况和权衡。

```
我想构建[简要描述]。使用 AskUserQuestion 工具详细采访我。

询问技术实现、UI/UX、边缘情况、关注点和权衡。不要问显而易见的问题，深入挖掘我可能没有考虑过的难点。

继续采访直到我们涵盖所有内容，然后将完整的规范写入 SPEC.md。
```

规范完成后，开始一个新会话来执行它。新会话有干净的上下文，完全专注于实现，并且您有书面规范可以参考。

---

## 管理会话 / Manage Your Session

**English:**

Conversations are persistent and reversible. Use this to your advantage!

**中文：**

对话是持久且可逆的。利用这一点！

---

### 尽早且经常纠正方向 / Course-correct Early and Often

**English:**

The best results come from tight feedback loops. Though Claude occasionally solves problems perfectly on the first attempt, correcting it quickly generally produces better solutions faster.

- **Esc**: stop Claude mid-action with the Esc key. Context is preserved, so you can redirect.
- **Esc + Esc or /rewind**: press Esc twice or run `/rewind` to open the rewind menu and restore previous conversation and code state, or summarize from a selected message.
- **"Undo that"**: have Claude revert its changes.
- **/clear**: reset context between unrelated tasks. Long sessions with irrelevant context can reduce performance.

If you've corrected Claude more than twice on the same issue in one session, the context is cluttered with failed approaches. Run `/clear` and start fresh with a more specific prompt that incorporates what you learned. A clean session with a better prompt almost always outperforms a long session with accumulated corrections.

**中文：**

最好的结果来自紧密的反馈循环。虽然 Claude 偶尔会在第一次尝试时完美解决问题，但快速纠正通常能更快地产生更好的解决方案。

- **Esc**: 使用 Esc 键中途停止 Claude。上下文被保留，因此您可以重定向。
- **Esc + Esc 或 /rewind**: 按两次 Esc 或运行 `/rewind` 打开回退菜单，恢复之前的对话和代码状态，或从选定的消息开始总结。
- **"Undo that"**: 让 Claude 撤销其更改。
- **/clear**: 在不相关的任务之间重置上下文。有不相关上下文的长会话可能会降低性能。

如果您在一个会话中对同一问题纠正 Claude 超过两次，上下文就会充斥着失败的方法。运行 `/clear` 并使用更具体的提示重新开始，该提示包含您学到的内容。带有更好提示的干净会话几乎总是优于有累积纠正的长会话。

---

### 积极管理上下文 / Manage Context Aggressively

**English:**

Claude Code automatically compacts conversation history when you approach context limits, which preserves important code and decisions while freeing space.

During long sessions, Claude's context window can fill with irrelevant conversation, file contents, and commands. This can reduce performance and sometimes distract Claude.

- Use `/clear` frequently between tasks to reset the context window entirely
- When auto compaction triggers, Claude summarizes what matters most, including code patterns, file states, and key decisions
- For more control, run `/compact <instructions>`, like `/compact Focus on the API changes`
- To compact only part of the conversation, use Esc + Esc or `/rewind`, select a message checkpoint, and choose Summarize from here
- Customize compaction behavior in CLAUDE.md with instructions like "When compacting, always preserve the full list of modified files and any test commands"
- For quick questions that don't need to stay in context, use `/btw`. The answer appears in a dismissible overlay and never enters conversation history

**中文：**

当您接近上下文限制时，Claude Code 会自动压缩对话历史，这会保留重要的代码和决策，同时释放空间。

在长会话期间，Claude 的上下文窗口可能会充满不相关的对话、文件内容和命令。这可能会降低性能，有时会分散 Claude 的注意力。

- 在任务之间频繁使用 `/clear` 完全重置上下文窗口
- 当自动压缩触发时，Claude 会总结最重要的内容，包括代码模式、文件状态和关键决策
- 要获得更多控制，运行 `/compact <instructions>`，如 `/compact Focus on the API changes`
- 要仅压缩对话的一部分，使用 Esc + Esc 或 `/rewind`，选择消息检查点，然后选择"从这里开始总结"
- 在 CLAUDE.md 中自定义压缩行为，使用类似"压缩时，始终保留修改文件的完整列表和任何测试命令"的指令
- 对于不需要保留在上下文中的快速问题，使用 `/btw`。答案出现在可关闭的覆盖层中，永远不会进入对话历史

---

### 使用 Subagents 进行调查 / Use Subagents for Investigation

**English:**

Since context is your fundamental constraint, subagents are one of the most powerful tools available. When Claude researches a codebase it reads lots of files, all of which consume your context. Subagents run in separate context windows and report back summaries:

```
Use subagents to investigate how our authentication system handles token
refresh, and whether we have any existing OAuth utilities I should reuse.
```

The subagent explores the codebase, reads relevant files, and reports back with findings, all without cluttering your main conversation.

You can also use subagents for verification after Claude implements something:

```
use a subagent to review this code for edge cases
```

**中文：**

由于上下文是您的基本约束，subagents 是最强大的工具之一。当 Claude 研究代码库时，它会读取大量文件，所有这些都会消耗您的上下文。Subagents 在单独的上下文窗口中运行并报告摘要：

```
使用 subagents 调查我们的认证系统如何处理 token 刷新，
以及是否有任何现有的 OAuth 工具我应该重用。
```

Subagent 探索代码库，读取相关文件，并报告发现，所有这些都不会混乱您的主对话。

您也可以在 Claude 实现某些东西后使用 subagents 进行验证：

```
使用 subagent 审查此代码的边缘情况
```

---

### 使用检查点回退 / Rewind with Checkpoints

**English:**

Claude automatically checkpoints before changes. Double-tap Escape or run `/rewind` to open the rewind menu. You can restore conversation only, restore code only, restore both, or summarize from a selected message.

Instead of carefully planning every move, you can tell Claude to try something risky. If it doesn't work, rewind and try a different approach. Checkpoints persist across sessions, so you can close your terminal and still rewind later.

**中文：**

Claude 会在更改之前自动创建检查点。双击 Escape 或运行 `/rewind` 打开回退菜单。您可以仅恢复对话、仅恢复代码、恢复两者，或从选定的消息开始总结。

与其仔细规划每一步，您可以告诉 Claude 尝试一些有风险的事情。如果不起作用，回退并尝试不同的方法。检查点在会话之间持久存在，因此您可以关闭终端并稍后仍然回退。

---

### 恢复对话 / Resume Conversations

**English:**

Claude Code saves conversations locally. When a task spans multiple sessions, you don't have to re-explain the context:

```bash
claude --continue    # Resume the most recent conversation
claude --resume      # Select from recent conversations
```

Use `/rename` to give sessions descriptive names like "oauth-migration" or "debugging-memory-leak" so you can find them later. Treat sessions like branches: different workstreams can have separate, persistent contexts.

**中文：**

Claude Code 在本地保存对话。当任务跨越多个会话时，您不必重新解释上下文：

```bash
claude --continue    # 恢复最近的对话
claude --resume      # 从最近的对话中选择
```

使用 `/rename` 给会话起描述性名称，如"oauth-migration"或"debugging-memory-leak"，以便您以后可以找到它们。将会话视为分支：不同的工作流可以有独立、持久的上下文。

---

## 自动化和扩展 / Automate and Scale

**English:**

Once you're effective with one Claude, multiply your output with parallel sessions, non-interactive mode, and fan-out patterns.

Everything so far assumes one human, one Claude, and one conversation. But Claude Code scales horizontally. The techniques in this section show how you can get more done.

**中文：**

一旦您能有效地使用一个 Claude，就可以通过并行会话、非交互模式和扇出模式来倍增您的产出。

到目前为止，一切都假设一个人、一个 Claude 和一个对话。但 Claude Code 可以水平扩展。本节的技术展示了如何完成更多工作。

---

### 运行非交互模式 / Run Non-interactive Mode

**English:**

With `claude -p "your prompt"`, you can run Claude non-interactively, without a session. Non-interactive mode is how you integrate Claude into CI pipelines, pre-commit hooks, or any automated workflow. The output formats let you parse results programmatically: plain text, JSON, or streaming JSON.

```bash
# One-off queries
claude -p "Explain what this project does"

# Structured output for scripts
claude -p "List all API endpoints" --output-format json

# Streaming for real-time processing
claude -p "Analyze this log file" --output-format stream-json
```

**中文：**

使用 `claude -p "your prompt"`，您可以在没有会话的情况下非交互式运行 Claude。非交互模式是您将 Claude 集成到 CI 管道、pre-commit hooks 或任何自动化工作流的方式。输出格式让您可以编程方式解析结果：纯文本、JSON 或流式 JSON。

```bash
# 一次性查询
claude -p "Explain what this project does"

# 用于脚本的结构化输出
claude -p "List all API endpoints" --output-format json

# 用于实时处理的流式输出
claude -p "Analyze this log file" --output-format stream-json
```

---

### 运行多个 Claude 会话 / Run Multiple Claude Sessions

**English:**

There are three main ways to run parallel sessions:

- **Claude Code desktop app**: Manage multiple local sessions visually. Each session gets its own isolated worktree.
- **Claude Code on the web**: Run on Anthropic's secure cloud infrastructure in isolated VMs.
- **Agent teams**: Automated coordination of multiple sessions with shared tasks, messaging, and a team lead.

Beyond parallelizing work, multiple sessions enable quality-focused workflows. A fresh context improves code review since Claude won't be biased toward code it just wrote.

**中文：**

运行并行会话有三种主要方式：

- **Claude Code 桌面应用**: 可视化管理多个本地会话。每个会话都有自己的隔离工作树。
- **Claude Code 网页版**: 在 Anthropic 安全云基础设施的隔离 VM 中运行。
- **Agent teams**: 多个会话的自动协调，具有共享任务、消息传递和团队负责人。

除了并行化工作外，多个会话还支持注重质量的工作流。新鲜的上下文可以改善代码审查，因为 Claude 不会偏向它刚刚编写的代码。

---

### Writer/Reviewer 模式 / Writer/Reviewer Pattern

| Session A (Writer) | Session B (Reviewer) |
|--------------------|----------------------|
| Implement a rate limiter for our API endpoints | Review the rate limiter implementation in @src/middleware/rateLimiter.ts. Look for edge cases, race conditions, and consistency with our existing middleware patterns. |
| Here's the review feedback: [Session B output]. Address these issues. | |

**中文对照：**

| 会话 A (编写者) | 会话 B (审查者) |
|----------------|----------------|
| 为我们的 API 端点实现一个速率限制器 | 审查 @src/middleware/rateLimiter.ts 中的速率限制器实现。寻找边缘情况、竞争条件以及与我们现有中间件模式的一致性。 |
| 这是审查反馈：[会话 B 输出]。解决这些问题。 | |

---

**English:**

You can do something similar with tests: have one Claude write tests, then another write code to pass them.

**中文：**

您可以用测试做类似的事情：让一个 Claude 编写测试，然后另一个编写代码来通过它们。

---

### 跨文件扇出 / Fan Out Across Files

**English:**

For large migrations or analyses, you can distribute work across many parallel Claude invocations. You can also integrate Claude into existing data/processing pipelines:

```bash
claude -p "<your prompt>" --output-format json | your_command
```

**中文：**

对于大型迁移或分析，您可以将工作分配到许多并行的 Claude 调用中。您也可以将 Claude 集成到现有的数据/处理管道中：

```bash
claude -p "<your prompt>" --output-format json | your_command
```

---

## 总结 / Summary

**English:**

The key takeaways from this guide:

1. **Context is your most precious resource** - Manage it aggressively with `/clear`, compaction, and subagents
2. **Verification improves results** - Give Claude ways to test and validate its work
3. **Be specific** - Reference files, describe constraints, point to patterns
4. **Configure your environment** - CLAUDE.md, permissions, CLI tools, and hooks multiply effectiveness
5. **Use the workflow** - Explore, plan, code, verify
6. **Communicate effectively** - Ask questions, let Claude interview you, course-correct early
7. **Scale horizontally** - Multiple sessions, non-interactive mode, fan-out patterns

**中文：**

本指南的关键要点：

1. **上下文是您最宝贵的资源** - 使用 `/clear`、压缩和 subagents 积极管理它
2. **验证改善结果** - 给 Claude 测试和验证其工作的方法
3. **要具体** - 引用文件、描述约束、指向模式
4. **配置您的环境** - CLAUDE.md、权限、CLI 工具和 hooks 倍增效果
5. **使用工作流** - 探索、规划、编码、验证
6. **有效沟通** - 提问、让 Claude 采访您、尽早纠正方向
7. **水平扩展** - 多个会话、非交互模式、扇出模式
