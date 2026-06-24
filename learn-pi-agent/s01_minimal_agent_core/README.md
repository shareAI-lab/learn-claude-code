# s01: Agent Core — 先存住一轮对话

> *把一轮对话，先存下来。*
> **Pi Agent 核心的边界**： provider 输入边界 —— core 的内部状态和 provider 调用之间的第一道隔断。

`s01` → [下一节：s02](../s02_tool_contract/)

---

## 问题

你让模型回答一个问题，模型给了回复，然后就停了。

如果只是一轮问答，这没问题。但你想让它"接着刚才的话继续"，就会遇到第一个麻烦：**每一次调用都是独立的，模型自己并不记得上一句说了什么。**

所以 core 要做的第一件事，不是让模型变得更聪明，而是**先把这一轮对话记下来**——用户说了什么、模型回了什么，按顺序存在 core 里。有了这份记录，模型才接得上"刚才的对话"，下一轮才有继续的基础。

s01 从存一轮对话开始，同时建立起 core 和 provider 的界线。

---

## 解决方案

一轮对话进入 core，中间要经过一条边界：

```text
AgentState（core 内部） ── ProviderInput ──> Provider
```

core 内部怎么存，是 core 自己的事；provider 能看到什么，由 ProviderInput 决定。这两边**故意不同**：provider 拿不到 core 的内部状态，只能拿到一份为它准备好的输入信息。

用 `runOneTurn` 函数串起这轮流程：

| 步骤 | 动作 |
| --- | --- |
| 1 | 用户消息进入 AgentState |
| 2 | 从 AgentState 构造 ProviderInput |
| 3 | 调 Provider，拿到 assistant 消息 |
| 4 | 把 assistant 消息存回 AgentState |

另外有两处设计先提一下，后面会用到：

  1. assistant 消息带一个**停止原因**（这一轮是正常结束，还是出了错）；
  2. core 的输出统一走一层 **Output**，不直接打印。

---

## 工作原理

从 core 内部往外，一步步把这条边界搭出来。

**core 先存什么。** 一条消息要么来自用户，要么来自 provider 。provider 的回复还要带停止原因，这样 core 才知道这一轮是正常结束，还是出了错。

```ts
export type StopReason = "stop" | "error";

export type UserMessage = { role: "user"; content: string };
export type AssistantMessage = { role: "assistant"; content: string; stopReason: StopReason };
export type AgentMessage = UserMessage | AssistantMessage;
```

core 用一个数组按顺序把它们存起来。现在 state 只有一个字段，但后面所有的对话历史都会从这里长出来。

```ts
export type AgentState = { messages: AgentMessage[] };

export function createInitialState(): AgentState { return { messages: [] }; }
export function createUserMessage(content: string): UserMessage { return { role: "user", content }; }
```

**然后是边界。** provider 不会直接拿到 AgentState，而是把每条消息转成 provider 需要的 role 和 content，组成 ProviderInput。这一步看起来只是做了格式转换，但它就是那道墙 —— core 的内部结构不会漏给 provider 。

```ts
export type ProviderMessage = { role: "user" | "assistant"; content: string };
export type ProviderInput = { messages: ProviderMessage[] };

export function buildProviderInput(state: AgentState): ProviderInput {
  return {
    messages: state.messages.map((m) => ({ role: m.role, content: m.content })),
  };
}
```

provider 这边的约定就一句话：给我 ProviderInput，我还你 AssistantMessage 。

```ts
export interface Provider {
  complete(input: ProviderInput): Promise<AssistantMessage>;
}
```

**最后收口。** core 不直接决定结果怎么展示，先留一层 Output，现在只包了一层 console，但把这层单独拎出来，后面有用。

```ts
export type Output = { log(line: string): void };
export function createConsoleOutput(): Output { return { log: (line) => console.log(line) }; }
```

每一轮的推进就是把上面几步连起来：存入用户消息 → 构造输入 → 调 provider → 存回 assistant 消息。

```ts
export async function runOneTurn(
  state: AgentState, provider: Provider, userInput: string,
): Promise<AssistantMessage> {
  state.messages.push(createUserMessage(userInput));
  const providerInput = buildProviderInput(state);
  const assistantMessage = await provider.complete(providerInput);
  state.messages.push(assistantMessage);
  return assistantMessage;
}
```

> 这一节真正要讲的，不是 `runOneTurn` 这个函数，而是 AgentState 和 ProviderInput 之间那条边界：格式转换。后面每一节都会往 ProviderInput 里加入新东西，但“ core 的内部状态永远不会直接暴露给 provider ”这条规矩，从 s01 定下来就不会再变。

---

## 试一下

运行：

```sh
npm run s01
```

输出类似：

```text
s01: Agent Core

[user]
你好，mini Pi

[provider input]
messages: 1
last.role: user
last.content: 你好，mini Pi

[assistant]
content: 收到：你好，mini Pi
stopReason: stop

[state]
messages: 2
last.role: assistant
last.stopReason: stop
```

观察重点：`[provider input]` 里 provider 拿到的是 ProviderInput（只有 role / content），拿不到 core 的 AgentState；`[state]` 里一轮结束后有两条消息。

### 错误情况

```sh
npm run s01 -- --case error
```

即使 provider 完不成这一轮，core 也照样把结果存成一条 AssistantMessage（stopReason 是 error）。state 的结构不会因为出错而变形——永远是一对 user / assistant 消息。

---

## 接入主线

s01 是 mini Pi 的起点，是后面 11 节的地基。本节定下来的类型和接口，后面**只扩展不改写**：

| 基础 | 后续怎么演化 |
| --- | --- |
| `UserMessage` / `AssistantMessage` / `AgentMessage` | 消息三类型，union 只增（s04 加 ToolResultMessage） |
| `AssistantMessage.stopReason` | 字段不变，取值只增（s04 加 toolUse） |
| `AgentState.messages` | 先是数组，s07 升级为 SessionTree（U1） |
| `ProviderInput` | 字段只增（s02 加 tools、s08 加 systemPrompt）；对齐 Pi Context，model 在 AgentState 不进 input |
| `Provider` | s03 从 complete 升级为 stream（U1） |
| `Output` | s10 升级为 RuntimeMode（R7 收获） |

---

## 接下来

现在 ProviderInput 里只有 messages ，下一节会加入其他东西，让 provider 看到的不只是对话，还有 core 能提供的本地能力。进入下一节：[s02](../s02_tool_contract/)。

---

<details>
<summary>Pi 源码溯源：Agent Core 一轮的完整设计</summary>

教学版的 `runOneTurn` 只"存两条消息"。Pi 的 `packages/agent` 里，一轮远不止于此。

### 源码在哪

- [`packages/agent/src/types.ts:317`](https://github.com/earendil-works/pi/blob/main/packages/agent/src/types.ts#L317) — `AgentState` 类型
- [`packages/agent/src/agent.ts:166`](https://github.com/earendil-works/pi/blob/main/packages/agent/src/agent.ts#L166) — `Agent` 类（状态持有 + 生命周期）
- [`packages/agent/src/agent-loop.ts:155`](https://github.com/earendil-works/pi/blob/main/packages/agent/src/agent-loop.ts#L155) — `runAgentLoop`（核心循环）

### AgentState 的真实形状

教学版只有一个 `messages` 数组。Pi 的 `AgentState`（`types.ts:317`）要多得多：

```ts
interface AgentState {
  systemPrompt: string;              // 系统提示（s08 方向）
  model: Model;                      // 当前模型（跨轮配置，在 AgentState；教学版 s06 引入）
  thinkingLevel: ThinkingLevel;      // 推理强度
  tools: AgentTool[];                // 工具（s02）
  messages: AgentMessage[];          // 消息历史
  isStreaming: boolean;              // 正在流式输出？
  streamingMessage?: AgentMessage;   // 当前正在生成的那条
  pendingToolCalls: Set<string>;     // 待执行的工具调用
  errorMessage?: string;             // 出错信息
}
```

一个"状态"承载的不只是消息，还有模型、工具、流式进度、错误——一轮里要用到的东西全在这里。教学版只留了 `messages` 一个字段。

### 一轮的真实推进：runWithLifecycle

教学版 `runOneTurn` 是一个 async 函数跑完就结束。Pi 用 `runWithLifecycle`（`agent.ts:451`）包了一层生命周期：

```ts
private async runWithLifecycle(executor) {
  const abortController = new AbortController();
  this.activeRun = { promise, resolve, abortController };
  this._state.isStreaming = true;
  try {
    await executor(abortController.signal);          // 真正的循环
  } catch (error) {
    await this.handleRunFailure(error, signal.aborted);
  } finally {
    this.finishRun();
  }
}
```

三个教学版没有的东西：

- **AbortController**：用户随时能中断一轮（教学版一轮跑完才停）。
- **activeRun**：防止重入——上一轮没跑完，下一轮进不来（`waitForIdle` 配合）。教学版没这个保护。
- **handleRunFailure**：出错不崩，转成错误消息写回状态，对应教学版的 `stopReason = error`，但 Pi 有完整的失败恢复路径。

### 双队列：steering 和 follow-up

`runAgentLoop`（`agent-loop.ts:155`）其实是**两层循环**：

- **outer loop**：消费 follow-up 消息队列（用户后续追加的话）。
- **inner loop**：处理工具调用，以及 steering 消息（执行中途插入、用来"引导"方向的）。

教学版的循环只有"工具来回"一条线；Pi 把"用户中途插话"和"工具来回"分成两个队列，各有优先级，这是真实交互场景必须的（用户不会老老实实等工具跑完）。

### 消息带时间戳，内容是数组

教学版 `content` 是字符串。Pi 的 `AgentMessage` 是 `content: Array<TextContent | ImageContent | ToolCall>` 加 `timestamp`，一条消息能同时含文本、图片、工具调用，且按时间排序。教学版先把 content 简化成 string，s04 加 tool_call 时才会碰到"一条消息多种内容"的真实形态。

### 一句话

`buildProviderInput` + `Provider.complete` 看似平淡，立的是 core 最重要的一堵墙。但 Pi 在墙两侧都加了教学版没有的工程层：墙这边是带生命周期的可变状态（model / tools / streaming / abort），墙那边是多 provider 的统一事件流（s03）。s01 先立最小骨架，这些层在后面陆续长出来。

</details>
