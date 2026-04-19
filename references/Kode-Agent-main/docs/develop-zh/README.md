# Kode 开发文档

本文档为开发者提供了 Kode 代码库架构、设计模式和实现细节的完整理解。

## 文档结构

### 核心文档

- **[系统概述](./overview.md)** - Kode 的设计理念、功能和核心原则介绍
- **[架构设计](./architecture.md)** - 高层系统架构、组件关系和数据流
- **[安全模型](./security-model.md)** - 全面的安全架构、权限系统和威胁模型
- **[配置系统](./configuration.md)** - 多层级配置管理和设置

### 系统组件

- **[工具系统](./tools-system.md)** - Kode 功能的核心，标准化工具接口和实现
- **[模型管理](./modules/model-management.md)** - 多提供商 AI 模型集成和智能切换
- **[MCP 集成](./modules/mcp-integration.md)** - 用于第三方工具集成的模型上下文协议
- **[自定义命令](./modules/custom-commands.md)** - 基于 Markdown 的可扩展命令系统

### 核心模块

- **[查询引擎](./modules/query-engine.md)** - AI 对话编排和流式响应处理
- **[REPL 界面](./modules/repl-interface.md)** - 交互式终端 UI 和用户交互管理
- **[上下文系统](./modules/context-system.md)** - 项目上下文收集和智能注入

## 快速导航

### 新贡献者入门

1. 从[系统概述](./overview.md)开始，了解 Kode 的目的和设计
2. 阅读[架构设计](./architecture.md)文档，理解组件关系
3. 查看[工具系统](./tools-system.md)，了解功能是如何实现的
4. 检查[安全模型](./security-model.md)，了解权限和安全考虑

### 功能开发指南

- **添加新工具**：参见[工具系统](./tools-system.md#创建新工具)
- **添加新 AI 提供商**：参见[模型管理](./modules/model-management.md#提供商集成)
- **创建自定义命令**：参见[自定义命令](./modules/custom-commands.md#示例)
- **集成 MCP 服务器**：参见[MCP 集成](./modules/mcp-integration.md#服务器管理)

### 系统理解指南

- **对话如何工作**：[查询引擎](./modules/query-engine.md#对话流程)
- **UI 如何渲染**：[REPL 界面](./modules/repl-interface.md#消息渲染)
- **上下文如何管理**：[上下文系统](./modules/context-system.md#上下文注入)
- **安全如何执行**：[安全模型](./security-model.md#权限系统架构)

## 核心概念

### 工具优先架构
Kode 中的所有功能都作为工具实现，具有标准化的验证、权限和执行接口。这提供了无限的可扩展性，同时保持一致性。

### 多模型协同系统
与官方实现不同，Kode 支持多个 AI 模型的灵活切换和协同工作：
- **模型配置文件系统**：支持定义多个模型配置，包括不同的提供商（Anthropic、OpenAI、Gemini 等）
- **智能模型选择**：根据任务类型自动选择最适合的模型
- **并行处理能力**：不同模型可以同时处理不同的子任务
- **成本优化策略**：根据任务复杂度选择性价比最优的模型

### 上下文感知 AI
系统自动收集并注入相关的项目上下文（git 状态、目录结构、文档）以提高 AI 响应质量。

### 安全层
多个安全层包括权限系统、命令验证、路径遍历防护和资源限制，确保安全操作。

### 流式架构
所有长时间运行的操作都使用异步生成器，支持实时进度更新和取消。

## 开发工作流

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/shareAI-lab/kode.git
cd kode

# 安装依赖
bun install

# 以开发模式运行
bun run dev
```

### 运行测试

```bash
# 运行所有测试
bun test

# 运行特定测试文件
bun test src/tools/BashTool.test.ts

# 运行覆盖率测试
bun test --coverage
```

### 构建生产版本

```bash
# 构建 CLI
bun run build

# 运行类型检查
bun run typecheck

# 格式化代码
bun run format
```

## 架构原则

### 1. 模块化设计
每个组件都有单一职责，具有清晰的接口和最小的依赖关系。

### 2. 可扩展性
可以通过工具、命令或 MCP 服务器添加新功能，而无需修改核心代码。

### 3. 默认安全
所有操作都需要适当的权限，具有安全的默认值和明确的用户同意。

### 4. 性能意识
流式响应、延迟加载和智能缓存确保响应式交互。

### 5. 用户体验优先
原生终端设计，具有键盘快捷键、语法高亮和清晰的错误消息。

## 代码组织

```
src/
├── entrypoints/        # 应用程序入口点
│   ├── cli.tsx        # 主 CLI 入口
│   └── mcp.ts         # MCP 服务器入口
├── screens/           # 全屏 UI 组件
│   ├── REPL.tsx       # 主交互界面
│   └── Doctor.tsx     # 系统诊断
├── components/        # 可重用 UI 组件
│   ├── messages/      # 消息渲染
│   └── permissions/   # 权限对话框
├── tools/            # 工具实现
│   ├── BashTool.ts   # Shell 执行
│   └── FileEditTool.ts # 文件操作
├── services/         # 外部服务集成
│   ├── claude.ts     # Anthropic API
│   └── mcpClient.ts  # MCP 客户端
├── utils/            # 实用函数
│   ├── config.ts     # 配置管理
│   └── model.ts      # 模型管理
└── Tool.ts           # 基础工具类
```

## 贡献指南

### 代码风格
- 使用宽松严格模式的 TypeScript
- 2 空格缩进
- 无分号（Prettier 强制）
- 描述性变量名
- 全面的错误处理

### 测试要求
- 为新工具编写单元测试
- 为命令流程编写集成测试
- 模拟外部依赖
- 测试错误条件

### 文档标准
- 更新相关文档
- 包含代码示例
- 记录破坏性更改
- 为复杂逻辑添加内联注释

### Pull Request 流程
1. 创建功能分支
2. 实现并编写测试
3. 更新文档
4. 运行 `bun test` 和 `bun run typecheck`
5. 提交带有清晰描述的 PR

## 高级主题

### 性能优化
- 对大型操作使用流式处理
- 策略性地实现缓存
- 延迟加载重型依赖
- 使用 Chrome DevTools 进行性能分析

### 调试
- 启用调试模式：`kode --debug`
- 检查日志：`kode error`
- 使用详细输出：`kode --verbose`
- 使用 Node 调试器检查

### 安全考虑
- 始终验证用户输入
- 对文件操作使用 path.resolve
- 实现速率限制
- 记录安全事件

## 资源

### 内部文档
- [项目结构](../PROJECT_STRUCTURE.md)
- [自定义命令指南](../custom-commands.md)
- [发布指南](../PUBLISH.md)

### 外部资源
- [Anthropic API 文档](https://docs.anthropic.com)
- [模型上下文协议](https://modelcontextprotocol.io)
- [Ink React 渲染器](https://github.com/vadimdemedes/ink)

## 支持

如有问题或疑问：
- GitHub Issues：[报告错误](https://github.com/shareAI-lab/kode/issues)
- Discussions：[提问](https://github.com/shareAI-lab/kode/discussions)

---

本文档代表了当前版本 Kode 系统的完整技术理解。它作为开发 Kode 代码库的开发人员的权威参考。