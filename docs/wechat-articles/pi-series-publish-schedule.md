# 「动手学 Pi」公众号拆解系列 · 排期清单

> 参考之前的 Claude Code 系列风格（学习笔记 + 源码注释 + demo 验证 + 对比真实产品）
> 项目地址：https://github.com/hahhforest/pi-textbook
> 课程代码：https://github.com/hahhforest/pi/tree/course/build-your-own-pi

---

## 系列定位

**一句话**：Pi 是一个 TypeScript 写的 Agent Harness（和 learn-claude-code 用 Python 教同样的事，但 Pi 更接近生产级——真正的 SSE 流式、多 Provider、JSONL 会话树、独立 Eval）。

**和 CC 系列的差异化卖点**：
- CC 系列：Python 教学版，30 行起步，适合理解概念
- Pi 系列：TypeScript 工程级，真实 commit 历史，每章有聚焦测试和故障实验
- 两套对照着看，概念更扎实

---

## 排期总览（15 期 + 2 篇衍生）

| 期数 | Checkpoint | 主题 | 钩子标题（候选） | 预计字数 | 配套小绿书 |
|---|---|---|---|---|---|
| EP01 | 00 | 一次请求怎样走完 Agent 闭环 | 一条消息的七步旅程 | 3000 | ✅ |
| EP02 | 01-02 | TypeScript 类型协议 + EventStream | 类型系统替你抓住第一个 bug | 3500 | ✅ |
| EP03 | 03-04 | 消息 IR + ScriptedModel | 模型的"剧本"：让不确定性变成可测试 | 3500 | ✅ |
| EP04 | 05 | Provider 适配器（SSE 流式翻译） | 一个适配器，四家模型 | 4000 | ✅ |
| EP05 | 06-07 | 工具契约 + Agent Loop | 闭环了：模型说→工具做→结果回 | 4000 | ✅ |
| EP06 | 08 | 四个编码工具（read/write/edit/bash） | 让 Agent 真正碰文件系统 | 3500 | ✅ |
| EP07 | 09 | 有状态 Agent（跨运行、订阅、abort） | 第二次对话，它还记得你 | 4000 | ✅ |
| EP08 | 10 | 会话树 + JSONL 持久化 | 每一行 JSONL 都是一条不可篡改的事实 | 4000 | ✅ |
| EP09 | 11 | Context Compaction（预算投影） | 上下文满了怎么办：不动历史，只重建投影 | 4000 | ✅ |
| EP10 | 12 | Resources + Extensions（Skill 按需加载） | 知识按需进门，代码先过信任关 | 3500 | ✅ |
| EP11 | 13 | Composition Root（Runtime 组装） | 把所有零件拧成一台机器 | 4000 | ✅ |
| EP12 | 14 | 独立评测 + held-out capstone | "跑完了"不等于"做对了" | 3500 | ✅ |
| 衍生01 | — | Pi vs Claude Code：两种 Agent Harness 的设计哲学 | 同一个循环，两种工程取舍 | 4000 | ✅ |
| 衍生02 | — | 从 Pi 的 TypeScript 类型系统学 Agent 设计 | 类型即文档：Agent 的不变量用类型守住 | 3500 | ✅ |

---

## 每期标准内容结构

1. **钩子开场**（100 字）：一个具体场景或痛点
2. **这一章在解决什么问题**（300 字）：为什么需要这个机制
3. **核心代码 + 中文注释**（1500 字）：关键 TypeScript 片段，注释在代码行上方
4. **跑起来看效果**（500 字）：npm test 的实际输出截图
5. **对比真实 Pi 上游**（500 字）：教学版和上游的差异
6. **小结 + 下期预告**（100 字）

---

## 逐期详细内容

### EP01 · Checkpoint 00 · 序章：一条消息的七步旅程

**钩子**：你给 Agent 发了句"读一下 README"，然后呢？背后发生了 7 步——用户消息→模型调用→工具调用→工具结果→第二次模型调用→最终回答→停止。这 7 步就是 Agent 的全部秘密。

**核心内容**：
- prologue.ts 的离线确定性轨迹：7 个 DemoEvent
- owner 概念：user / model / loop / tool 各自负责什么
- call id 的因果配对：toolCall 和 toolResult 怎么匹配
- 这是后面 14 章的主链路预告

**对比 Pi 上游**：教学版用固定轨迹（ScriptedModel），上游用真实 SSE 流式

---

### EP02 · Checkpoint 01-02 · 类型系统替你抓住第一个 bug

**钩子**：Agent 要处理的事件有 4 种，少写一个 case 会怎样？TypeScript 的编译器会直接报错——这就是 tagged union 的威力。

**核心内容**：
- DemoEvent 联合类型 + `unknown` 收窄 + `never` 穷尽检查
- EventStream：同一个对象同时提供 AsyncIterable（过程）和 result()（最终结果）
- queue / waiting / done 三态容器
- 两种时序：事件先到 vs 消费者先等

---

### EP03 · Checkpoint 03-04 · 模型的"剧本"

**钩子**：怎么测试一个需要调模型的 Agent？不能真的调——每次结果不一样。Pi 的答案：给模型写剧本。

**核心内容**：
- 消息 IR：text / toolCall / toolResult 三种内容块，五种 stop reason
- 为什么 toolResult 不能伪装成 assistant 文本
- ScriptedModel：把"模型下一回合做什么"变成可执行规格
- final message → event trace 的纯投影

---

### EP04 · Checkpoint 05 · 一个适配器，四家模型

**钩子**：OpenAI、Anthropic、Google 的 API 格式完全不同。Pi 用一个适配器层把它们的差异全部吃掉——上层只管调 Model，不管底下是谁。

**核心内容**：
- 三层翻译：出站映射 → ProviderChunk 累积 → transport 验证
- SSE 流式：按 index 累积增量参数
- 安全检查：API key 只进 Authorization header，body/日志/错误都不能含密钥
- `{"path":` 不是坏 JSON——它在等另一半

---

### EP05 · Checkpoint 06-07 · 闭环了

**钩子**：模型能声明"我要调 read 工具"了，但谁来执行？谁来把结果喂回去？Agent Loop 就是那个"谁"。

**核心内容**：
- 工具契约：validator → Registry → executor → 结构化 toolResult
- Agent Loop：model → tool calls → paired results → next model
- 五种终止语义：stop / error / aborted / length / maxSteps
- 并发工具：完成事件顺序和 transcript 顺序可以不同

---

### EP06 · Checkpoint 08 · 让 Agent 真正碰文件系统

**钩子**：loop 闭合了，但工具还是空壳。这一章让 read/write/edit/bash 真正能操作文件。

**核心内容**：
- read：续读、截断
- write：原子写（temp + rename，不会写一半）
- edit：批量精确替换，第二项失败时第一项不留痕迹
- bash：可取消、可超时、可截断
- workspace containment：课程 guardrail，不是 OS sandbox

---

### EP07 · Checkpoint 09 · 第二次对话，它还记得你

**钩子**：第一次 prompt 结束了，Agent 的状态全没了。第二次对话怎么办？这一章让 Agent 有记忆。

**核心内容**：
- reducer 模式：AgentEvent → AgentState
- 单运行、subscriber、副本管理
- abort 语义：旧运行还有没有权清理资源
- steering/follow-up：正在跑的时候用户又发了一条

---

### EP08 · Checkpoint 10 · 每一行 JSONL 都是一条事实

**钩子**：Agent 有状态了，但重启就丢了。Pi 用 JSONL 记录每条消息——不是为了好看，是为了能分支、能恢复、能审计。

**核心内容**：
- 会话树：带父指针的 JSONL 记录
- 换行是 commit marker：半行 JSON 不算事实
- pathTo：从叶子节点恢复当前对话路径
- 内存 store → JSONL recovery → 磁盘 store

---

### EP09 · Checkpoint 11 · 不动历史，只重建投影

**钩子**：对话越来越长，token 预算要爆了。Pi 的做法：历史不动，给模型看的上下文按预算重建。

**核心内容**：
- compaction 是追加到 session 的新事实，不删旧 entry
- interaction 配对：按 callId 建立集合相等关系
- 预算投影：从最新 group 向前累加，先扣 system 和安全余量
- 恢复只读最新摘要，再从 firstKeptEntryId 投影后缀

---

### EP10 · Checkpoint 12 · 知识按需进门

**钩子**：CLAUDE.md 每轮都加载太贵了。Pi 怎么做？发现规则→按需激活→送入上下文，代码先过信任门。

**核心内容**：
- 资源优先级：kind+name 身份，root 输入顺序选 winner
- skill：discovery 只收集 metadata，activation 才读正文
- 扩展原子注册：factory 注册了一个 tool 后抛错，这个 tool 不能留下
- hook 故障隔离：beforeToolCall 拒绝/抛错/超时都阻止 core executor

---

### EP11 · Checkpoint 13 · 把所有零件拧成一台机器

**钩子**：Agent、session、context、resources、extensions——每个都能独立工作了，但谁来把它们接在一起？

**核心内容**：
- Runtime 组装：依赖接线，不重新实现
- context 投影：每次请求模型前，把 suffix 临时接到 active path
- 持久化顺序：append 完成才返回；并发排队；失败进 poison 状态
- 三种 mode：interactive / print / json

---

### EP12 · Checkpoint 14 · "跑完了"不等于"做对了"

**钩子**：Runtime 跑起来了，但你怎么知道它做对了？Pi 的答案：独立评测层 + held-out capstone。

**核心内容**：
- eval.ts：每个 case 重新 prepare，独占执行、取证、dispose、cleanup
- 协议判断：同时核对 session path 和 Runtime 返回的 transcript
- held-out：三项测试只存在于 target 和最终 full gate，practice 不复制
- 安全报告：不能携带原始消息、文件内容、路径、callId、异常正文

---

### 衍生01 · Pi vs Claude Code：两种 Agent Harness 的设计哲学

**核心内容**：
| 维度 | learn-claude-code (Python) | Pi (TypeScript) |
|---|---|---|
| 语言 | Python（教学友好） | TypeScript（生产级类型安全） |
| 模型接入 | 直接调 Anthropic SDK | 多 Provider 适配器层 |
| 流式 | 无（同步） | SSE 流式 + EventStream |
| 会话存储 | 无（内存） | JSONL 会话树 + 磁盘持久化 |
| 上下文管理 | 四层压缩 | 预算投影 + compaction entry |
| 工具系统 | dispatch map | Registry + validator + executor |
| 测试 | 无 | 每章聚焦测试 + held-out eval |
| 扩展 | Hook 注册表 | 原子注册 + 信任门 |

---

### 衍生02 · 类型即文档：Agent 的不变量用类型守住

**核心内容**：
- tagged union + never 穷尽检查：少写一个 case 编译就不过
- unknown 收窄：外部 JSON 先按 unknown 验证，收窄后才能用
- call id 配对：类型系统强制 toolResult 必须有对应 toolCall
- 带宽 vs 安全：类型在编译期守住的，运行期就不用再查

---

## 发布节奏

- **频率**：每周 2-3 期
- **总周期**：约 5-6 周（15 期 + 2 衍生）
- **每期配套**：公众号长文 + 小绿书卡片 + 公众号封面
- **小绿书钩子策略**：每期一个不同的痛点钩子

## 技术准备

```bash
# 课程代码已 clone
cd ~/Desktop/github/pi-course/packages/pi-course

# 运行测试（不需要 API key，全部离线）
npm install
npm test -w @pi/course

# 查看某一章的 diff
git log --reverse --oneline -- packages/pi-course
```
