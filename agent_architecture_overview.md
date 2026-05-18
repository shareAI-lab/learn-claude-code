# Agent 框架演进结构图 (s01-s19)

为了帮你更好地理解整个 agent 教程的内容，我生成了这张系统架构的概念图，并将它整理成了从内到外的六个演进层级。你可以对照这个架构层级来复习后续的章节。

![Agent 架构概览图](file:///C:/Users/31239/.gemini/antigravity/brain/6fb7cb52-28ae-4d15-a43f-07730c416899/artifacts/agent_architecture_blueprint.png)

### 对应的知识层级映射：

**🟣 核心圈：单兵作战的基础 (Foundations)**
*   `s01 Agent Loop`
*   `s02 Tool Use`
*   `s03 Todo Write`

**🔵 第二层：能力扩展 (Skills & Specialization)**
*   `s04 Subagent`
*   `s05 Skill Loading`

**🟢 第三层：状态与安全管控 (State & Security)**
*   `s06 Context Compact`
*   `s07 Permission System` 
*   `s08 Hook System`
*   `s09 Memory System`

**🟡 第四层：健壮性兜底 (Robustness)**
*   `s10 System Prompt`
*   `s11 Error Recovery`

**🟠 第五层：高级任务引擎 (Advanced Task Engine)**
*   `s12 Task System`
*   `s13 Background Tasks`
*   `s14 Cron Scheduler`

**🔴 最外围：多智能体协作与生态 (Multi-Agent & Ecosystem)**
*   `s15 Agent Teams`
*   `s16 Team Protocols`
*   `s17 Autonomous Agents`
*   `s18 Worktree Isolation`
*   `s19 MCP Plugin`
