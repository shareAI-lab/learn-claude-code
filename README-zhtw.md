# Learn Claude Code -- 從 0 到 1 打造 nano Claude Code-like agent

[English](./README.md) | [簡體中文](./README-zh.md) | [日本語](./README-ja.md) | [繁體中文](./README-zhtw.md)

```
                    THE AGENT PATTERN
                    =================

    User --> messages[] --> LLM --> response
                                      |
                            stop_reason == "tool_use"?
                           /                          \
                         yes                           no
                          |                             |
                    execute tools                    return text
                    append results
                    loop back -----------------> messages[]


    這就是最小迴圈。每個 AI coding agent 都離不開它。
    Production agents 還會疊加 policy、permissions 與 lifecycle layers。
```

**12 個循序漸進的章節，從簡單迴圈一路到隔離式自主執行。**
**每個章節只新增一個機制。每個機制都有一句格言。**

> **s01** &nbsp; *"One loop & Bash is all you need"* &mdash; 一個工具 + 一個迴圈 = 一個 agent
>
> **s02** &nbsp; *"Adding a tool means adding one handler"* &mdash; 主迴圈不變；新工具只要註冊進 dispatch map
>
> **s03** &nbsp; *"An agent without a plan drifts"* &mdash; 先列步驟，再執行；完成率翻倍
>
> **s04** &nbsp; *"Break big tasks down; each subtask gets a clean context"* &mdash; subagents 使用獨立 messages[]，讓主對話保持乾淨
>
> **s05** &nbsp; *"Load knowledge when you need it, not upfront"* &mdash; 透過 tool_result 注入，而不是放進 system prompt
>
> **s06** &nbsp; *"Context will fill up; you need a way to make room"* &mdash; 三層壓縮策略，換來幾乎無限的 sessions
>
> **s07** &nbsp; *"Break big goals into small tasks, order them, persist to disk"* &mdash; 以檔案為基礎、含 dependencies 的 task graph，為 multi-agent 協作打下基礎
>
> **s08** &nbsp; *"Run slow operations in the background; the agent keeps thinking"* &mdash; 透過背景執行緒執行任務，完成後再發送通知

> **s09** &nbsp; *"When the task is too big for one, delegate to teammates"* &mdash; 永遠存在的隊友 + 非同步信件
>
> **s10** &nbsp; *"Teammates need shared communication rules"* &mdash; 一套 request-response pattern 驅動所有溝通
>
> **s11** &nbsp; *"Teammates scan the board and claim tasks themselves"* &mdash; 不需要逐一指派，而是主動認領工作去執行
>
> **s12** &nbsp; *"Each works in its own directory, no interference"* &mdash; tasks 管理 goals，worktrees 管理 directories，以 ID 綁定

---

## 核心模式

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant",
                         "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

每個章節都在這個迴圈上疊加一個機制 -- 但迴圈本身始終不變。

## 範圍（重要）

此 repository 是一個 0->1 學習型專案，用來建構 nano Claude Code-like agent。
為了讓學習路徑更清晰，這個 repository 刻意簡化或省略了部分 production 機制：

- 完整的 event/hook buses（例如 PreToolUse、SessionStart/End、ConfigChange）。  
  s12 僅提供教學用途的最小 append-only lifecycle event stream。
- 以規則為基礎的 permission governance 與 trust workflows
- Session lifecycle controls（resume/fork）與更完整的 worktree lifecycle controls
- 完整 MCP runtime 細節（transport/OAuth/resource subscribe/polling）

此 repository 中的 team JSONL mailbox protocol 僅為教學實作，不代表任何特定 production internals。

## 快速開始

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env                          # 編輯 .env 並填入你的 ANTHROPIC_API_KEY

python agents/s01_agent_loop.py               # 從這裡開始
python agents/s12_worktree_task_isolation.py  # 完整學習終點
python agents/s_full.py                       # 總結：把全部機制整合在一起
```

### Web 平台

互動式視覺化、逐步圖解、原始碼檢視器，以及對應文件。

```sh
cd web && npm install && npm run dev   # http://localhost:3000
```

## 學習路徑

```
第一階段：THE LOOP                    第二階段：PLANNING & KNOWLEDGE
==================                   ==============================
s01  The Agent Loop          [1]      s03  TodoWrite               [5]
     while + stop_reason                  TodoManager + nag reminder
     |                                    |
     +-> s02  Tool Use            [4]     s04  Subagents            [5]
              dispatch map: name->handler     fresh messages[] per child
                                              |
                                         s05  Skills               [5]
                                              SKILL.md via tool_result
                                              |
                                         s06  Context Compact      [5]
                                              3-layer compression

第三階段：PERSISTENCE                 第四階段：TEAMS
==================                   =====================
s07  Tasks                   [8]      s09  Agent Teams             [9]
     file-based CRUD + deps graph         teammates + JSONL mailboxes
     |                                    |
s08  Background Tasks        [6]      s10  Team Protocols          [12]
     daemon threads + notify queue        shutdown + plan approval FSM
                                          |
                                     s11  Autonomous Agents       [14]
                                          idle cycle + auto-claim
                                     |
                                     s12  Worktree Isolation      [16]
                                          task coordination + optional isolated execution lanes

                                     [N] = number of tools
```

## 架構

```
learn-claude-code/
|
|-- agents/                        # Python 參考實作 (s01-s12 + s_full capstone)
|-- docs/{en,zh,ja}/               # Mental-model-first 文件 (3 種語言)
|-- web/                           # 互動式學習平台 (Next.js)
|-- skills/                        # s05 的 Skill 檔案
+-- .github/workflows/ci.yml       # CI: 檢查型別 + 建制專案
```

## 文件

Mental-model-first：問題、解法、ASCII 圖、最小化程式碼。
提供 [English](./docs/en/) | [中文](./docs/zh/) | [日本語](./docs/ja/)。

| Session | Topic | Motto |
|---------|-------|-------|
| [s01](./docs/en/s01-the-agent-loop.md) | The Agent Loop | *One loop & Bash is all you need* |
| [s02](./docs/en/s02-tool-use.md) | Tool Use | *Adding a tool means adding one handler* |
| [s03](./docs/en/s03-todo-write.md) | TodoWrite | *An agent without a plan drifts* |
| [s04](./docs/en/s04-subagent.md) | Subagents | *Break big tasks down; each subtask gets a clean context* |
| [s05](./docs/en/s05-skill-loading.md) | Skills | *Load knowledge when you need it, not upfront* |
| [s06](./docs/en/s06-context-compact.md) | Context Compact | *Context will fill up; you need a way to make room* |
| [s07](./docs/en/s07-task-system.md) | Tasks | *Break big goals into small tasks, order them, persist to disk* |
| [s08](./docs/en/s08-background-tasks.md) | Background Tasks | *Run slow operations in the background; the agent keeps thinking* |
| [s09](./docs/en/s09-agent-teams.md) | Agent Teams | *When the task is too big for one, delegate to teammates* |
| [s10](./docs/en/s10-team-protocols.md) | Team Protocols | *Teammates need shared communication rules* |
| [s11](./docs/en/s11-autonomous-agents.md) | Autonomous Agents | *Teammates scan the board and claim tasks themselves* |
| [s12](./docs/en/s12-worktree-task-isolation.md) | Worktree + Task Isolation | *Each works in its own directory, no interference* |

## 接下來 -- 從理解到落地

完成 12 個章節後，你已經由內到外掌握 agent 的運作原理。把這些知識化為產品有兩種方式：

### Kode Agent CLI -- Open-Source Coding Agent CLI

> `npm i -g @shareai-lab/kode`

支援 Skill 與 LSP，適用於 Windows，並可串接 GLM / MiniMax / DeepSeek 等開放模型。安裝後即可上手。

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK -- 將 Agent 能力嵌入你的 App

官方 Claude Code Agent SDK 底層會與完整 CLI process 通訊 -- 每個並發使用者都會對應一個獨立 terminal process。Kode SDK 是獨立 library，沒有 per-user process 負擔，可嵌入 backends、browser extensions、embedded devices，或任何 runtime。

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## 姊妹 Repo：從 *on-demand sessions* 到 *always-on assistant*

本 repository 教的 agent 屬於 **use-and-discard** 模式 -- 開 terminal、交付任務、完成後關閉；下次重開就是全新 session。這就是 Claude Code 的模式。

[OpenClaw](https://github.com/openclaw/openclaw) 證明了另一種可能：在同樣的 agent core 上再加兩個機制，就能讓 agent 從「推一下才動」變成「每 30 秒自動醒來找事做」：

- **Heartbeat** -- 系統每 30 秒會送一則訊息給 agent，讓它檢查是否有事可做。沒事就繼續休眠；有事就立刻處理。
- **Cron** -- agent 可以替自己安排未來任務，到點自動執行。

再加上多通道 IM routing（WhatsApp / Telegram / Slack / Discord，13+ 平台）、持久化 context memory，以及 Soul personality system，agent 就會從一次性工具進化為 always-on 的個人 AI 助手。

**[claw0](https://github.com/shareAI-lab/claw0)** 是我們的姊妹教學 repository，從零拆解這些機制：

```
claw agent = agent core + heartbeat + cron + IM chat + memory + soul
```

```
learn-claude-code                   claw0
(agent runtime core:                (proactive always-on assistant:
 loop, tools, planning,              heartbeat, cron, IM channels,
 teams, worktree isolation)          memory, soul personality)
```

## About
<img width="260" src="https://github.com/user-attachments/assets/fe8b852b-97da-4061-a467-9694906b5edf" /><br>

使用 WeChat 掃描即可追蹤我們，  
或在 X 追蹤：[shareAI-Lab](https://x.com/baicai003)  

## 授權

MIT

---
**模型就是 agent。我們的工作，是給它工具，然後讓開。**