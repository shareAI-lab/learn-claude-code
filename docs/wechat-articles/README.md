# 微信公众号文章合集（渲染后 HTML）

本目录收录「学习使郑快乐」公众号发布的 Claude Code 源码拆解系列文章，以公众号渲染后的 HTML 格式保存。

## CC 源码拆解系列（共 23 篇）

### 正片 EP01–EP20

| 期数 | 文章 | 对应源码 |
|---|---|---|
| EP01 | [30行代码，我搞懂了AI编程智能体的全部秘密](EP01-30行代码，我搞懂了AI编程智能体的全部秘密.html) | s01_agent_loop |
| EP02 | [给AI一套专业工具，循环代码一行没改](EP02-给AI一套专业工具，循环代码一行没改.html) | s02_tool_use |
| EP03 | [让AI碰你的文件前，先过这3道门](EP03-让AI碰你的文件前，先过这3道门.html) | s03_permission |
| EP04 | [给AI加心眼：在它动手前后偷偷挂一层逻辑](EP04-给AI加心眼：在它动手前后偷偷挂一层逻辑.html) | s04_hooks |
| EP05 | [Agent也会列TODO清单：让AI先想清楚再动手](EP05-Agent也会列TODO清单：让AI先想清楚再动手.html) | s05_todo_write |
| EP06 | [派个子Agent去干活：大任务拆小，上下文不污染](EP06-派个子Agent去干活：大任务拆小，上下文不污染.html) | s06_subagent |
| EP07 | [用到时才加载：给AI一张按需知识卡片](EP07-用到时才加载：给AI一张按需知识卡片.html) | s07_skill_loading |
| EP08 | [上下文满了腾地方：四层压缩管线](EP08-上下文满了腾地方：四层压缩管线.html) | s08_context_compact |
| EP09 | [压缩会丢细节，要有一层不丢的：记忆系统](EP09-压缩会丢细节，要有一层不丢的：记忆系统.html) | s09_memory |
| EP10 | [prompt写死了9节课，s10终于让它动起来](EP10-prompt写死了9节课，s10终于让它动起来.html) | s10_system_prompt |
| EP11 | [错误不是终点：Claude Code怎么让Agent自己站起来](EP11-错误不是终点：Claude Code怎么让Agent自己站起来.html) | s11_error_recovery |
| EP12 | [盖房子不能先盖屋顶：Claude Code 的任务依赖系统](EP12-盖房子不能先盖屋顶：Claude%20Code%20的任务依赖系统.html) | s12_task_system |
| EP13 | [别让AI守着进度条：慢命令该进后台](EP13-别让AI守着进度条：慢命令该进后台.html) | s13_background_tasks |
| EP14 | [没人发消息，AI也会自己开工：Cron调度器](EP14-没人发消息，AI也会自己开工：Cron调度器.html) | s14_cron_scheduler |
| EP15 | [子Agent只是临时工：Claude Code怎样组队](EP15-子Agent只是临时工：Claude%20Code怎样组队.html) | s15_agent_teams |
| EP16 | [邮箱有了为什么还会乱发邮件](EP16-邮箱有了为什么还会乱发邮件.html) | s16_team_protocols |
| EP17 | [s17新增的是会找活](EP17-s17新增的是会找活.html) | s17_autonomous_agents |
| EP18 | [owner分开了文件为什么还会互相覆盖](EP18-owner分开了文件为什么还会互相覆盖.html) | s18_worktree_isolation |
| EP19 | [MCP到底是什么大模型的外挂知识库](EP19-MCP到底是什么大模型的外挂知识库.html) | s19_mcp_plugin |
| EP20 | [20节课走了一条什么路](EP20-20节课走了一条什么路.html) | s20_comprehensive |

### 衍生文章

| 文章 | 主题 |
|---|---|
| [衍生01 - 提示词工程](衍生01-从ClaudeCode取经如何写出高效的提示词.html) | 系统提示词 vs 需求提示词 |
| [衍生02 - Prompt Cache](衍生02-AI工具这么成熟还需要关注promptcache吗.html) | SDD + 缓存优化 |
| [衍生03 - Pi 介绍](衍生03-又一个AI编码工具Pi到底有什么不一样.html) | Pi vs CC/Codex/OpenClaw/QwenPaw 对比 |

## Pi 源码拆解系列（规划中）

- [排期清单](pi-series-publish-schedule.md) — 15 期 + 2 衍生

## 说明

- HTML 内容为微信公众号渲染后的格式，包含完整的 CSS 样式
- EP01-EP15 从公众号文章链接抓取，EP16-EP20 + 衍生文章从本地 HTML 存档
- `source-md/` 目录保存部分文章的 Markdown 源文件
