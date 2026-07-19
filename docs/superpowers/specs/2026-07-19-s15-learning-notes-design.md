# s15 Agent Teams 学习笔记设计

## 目标

在 `s15_agent_teams/LEARNING_NOTES.md` 中新增一份约 400–500 行的中文学习笔记，延续 s11–s14 学习笔记的表达方式，帮助学习者复习 s15 的团队协作机制，并针对本轮五道检测题中的理解偏差进行纠正。

## 范围

笔记包含以下内容：

1. s15 的核心问题与整体数据流。
2. 对五道检测题逐题评价，给出正确点、需修正点和准确表述。
3. s15 相比 s14 的新增能力，以及 s15 队友与 s06 子 Agent 的区别。
4. `MessageBus` 的发送、消费式读取和文件邮箱设计。
5. `spawn_teammate_thread()` 的独立 system prompt、messages、工具集和最多 10 轮限制。
6. Lead inbox 的两种触发路径：外层自动注入与 `check_inbox` 工具主动读取。
7. 队友最终 `summary` 的提取流程，包括内层 `for ... else` 和两个 `break`。
8. 异步时序、`read_text() + unlink()` 竞态、无文件锁等教学版局限。
9. 关键代码定位、重点理解、复习问题和记忆口诀。

不修改 `s15_agent_teams/code.py`、README 或其他课程文件，不运行真实 LLM 请求。

## 重点纠错

- 队友的初始任务通过 `prompt` 放入自己的 `messages`，不是先从 inbox 读取。
- inbox 消息追加到 `messages` 或 Lead 的 `history`，不注入固定的 system prompt。
- 外层 inbox 检查只负责注入历史，不会自动唤醒 Lead；消息到达时机可能造成一轮以上延迟。
- `check_inbox` 的返回值作为当前工具调用的 `tool_result` 参与同一轮处理。
- `unlink()` 实现消费式读取，但 `read_text()` 与 `unlink()` 之间存在消息丢失窗口；无锁追加还可能产生写入竞争。

## 文档结构

文档按以下顺序组织：

1. 本节核心
2. 你的回答评价
3. s15 相比 s14 的变化
4. s15 队友与 s06 子 Agent
5. 整体架构与完整数据流
6. MessageBus
7. Teammate Thread
8. Lead 的两种 inbox 触发路径
9. summary 提取
10. 异步时序与并发风险
11. 教学版局限
12. 关键代码定位
13. 重点理解
14. 复习问题
15. 记忆口诀

## 验收

- 目标文件位于 `s15_agent_teams/LEARNING_NOTES.md`。
- 总行数约 400–500 行。
- 五道回答都有逐题评价。
- 上述五项重点纠错均有明确说明。
- Markdown 标题层级一致，没有未完成占位标记或空章节。
- Git diff 只包含本次新增的设计记录和学习笔记。
