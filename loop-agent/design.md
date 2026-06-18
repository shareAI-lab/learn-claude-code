# Loop Engineering Coding Agent — 实施计划

> **⚠️ 本文档已重构**
>
> 本设计文档记录了 loop-agent 的初始设计。当前实现已重构为以 s20_comprehensive 为基座的架构。
>
> - **最新任务清单：** [task.md](task.md)
> - **最新架构：** [README.md](README.md)
>
> 重构要点：
> - 删除了 `agent_loop.py`、`worktree_manager.py`、`skills.py`、`maker.py`、`checker.py`
> - 新增 `loop_agent.py` 作为 s20 封装层
> - 直接调用 s20_comprehensive/code.py 的核心函数

## Context

基于 Addy Osmani 的 Loop Engineering 理念，以 learn-claude-code 仓库的 s01-s20 代码模式为基座，构建一个支持循环工程的独立编码代理系统。

**用户决策：**
- 项目形式：独立项目（新目录 `loop-agent/`）
- 触发源：手动触发 + Goal 模式 + CI/CD 失败 + Cron 定时任务
- 验证策略：Maker-Checker 子代理模式
- 迭代范围：最小可行循环（核心骨架 + mock 数据）

---

## 执行指引

### 使用方式

在 Claude Code 中输入以下 /goal 提示词：

```
/goal 请打开 loop-agent/task.md，找到所有标记为"待处理"的条目。按从上到下的顺序（Phase 1 → Phase 10）逐条执行每个任务。执行每个任务前，先读取 loop-agent/design.md 中对应章节的详细设计（函数签名、数据结构、复用来源），确认你理解了要做什么。每完成一个任务后，立即将该条目的状态从"待处理"改为"已完成"并保存文件。如果某个任务遇到问题无法完成（比如依赖缺失、实现复杂度过高），将该条目标记为"需人工处理"并在备注栏写一句原因说明，然后跳到下一个。参考 s01_agent_loop/code.py 到 s20_comprehensive/code.py 的代码模式实现。全部条目都不再是"待处理"状态时停止。或者超过 30 轮未全部完成也请停止。
```

### 执行规则

1. **顺序执行** — 按 Phase 1 → Phase 10 的顺序，同一 Phase 内按 ID 顺序
2. **即时更新** — 每完成一个任务，立即修改 task.md 中该条目的状态为"已完成"
3. **失败跳过** — 遇到问题无法完成的任务，标记"需人工处理"并写原因，不阻塞后续任务
4. **30 轮上限** — 超过 30 轮仍未全部完成则停止，避免无限循环
5. **设计参考** — 每个任务执行前读取 design.md 对应章节确认细节

### 任务状态说明

| 状态 | 含义 |
|------|------|
| 待处理 | 尚未开始 |
| 已完成 | 实现完毕并保存 |
| 需人工处理 | 遇到阻塞，需人工介入，原因见备注栏 |

### 文件关系

```
loop-agent/
├── task.md     ← 进度追踪（/goal 的锚点，状态标记）
├── design.md   ← 详细设计（函数签名、数据结构、本文件）
└── (实现代码)  ← /goal 执行过程中生成
```

---

## 目录结构

```
loop-agent/
├── main.py                  # 入口：REPL + CLI 参数解析
├── orchestrator.py          # 外层循环：触发→发现→分配→执行→验证→集成→持久化
├── agent_loop.py            # 核心 while 循环（s01 模式），maker/checker 共用
├── triggers.py              # 手动、Goal、Cron、CI 失败四种触发源
├── task_discovery.py        # 将触发事件转换为具体任务项
├── maker.py                 # Maker 子代理：在 worktree 中实现代码
├── checker.py               # Checker 子代理：审查代码，只读工具
├── worktree_manager.py      # Git worktree 生命周期管理（s18 模式）
├── state.py                 # 持久化状态文件 .loop-state.json
├── github_mock.py           # Mock GitHub API（issues, PRs, CI）
├── skills.py                # 技能加载（s07 两层注入模式）
├── config.py                # 配置集中管理，环境变量加载
├── skills/
│   └── loop-engineering/
│       └── SKILL.md         # 项目知识：架构、约定、模式
├── mock_data/
│   ├── issues.json          # Mock GitHub issues
│   ├── ci_results.json      # Mock CI 失败结果
│   └── pr_template.json     # Mock PR 创建响应
└── tests/
    ├── test_orchestrator.py
    ├── test_maker_checker.py
    ├── test_state.py
    ├── test_triggers.py
    └── test_github_mock.py
```

---

## 核心架构：七阶段循环

```
┌─────────────────────────────────────────────────────────┐
│                    orchestrator.py                        │
│                                                          │
│  Phase 1: TRIGGER   ← triggers.py                       │
│    check_ci_failure() / check_cron() / check_manual()   │
│    check_goal()                                          │
│         ↓                                                │
│  Phase 2: DISCOVER  ← task_discovery.py                  │
│    TriggerEvent → TaskItem[], 过滤已处理项                │
│         ↓                                                │
│  Phase 3: ALLOCATE  ← worktree_manager.py                │
│    create_worktree(task.branch_hint) → 隔离目录           │
│         ↓                                                │
│  Phase 4: EXECUTE   ← maker.py                           │
│    run_maker(task) → MakerResult                         │
│    fresh messages[], 读写工具, 50 轮上限                  │
│         ↓                                                │
│  Phase 5: VERIFY    ← checker.py                         │
│    run_checker(maker_result) → CheckerResult             │
│    fresh messages[], 只读工具, 20 轮上限                  │
│         ↓                                                │
│  Phase 6: INTEGRATE                                     │
│    approved → 创建 PR / rejected → 记录反馈供下次重试     │
│         ↓                                                │
│  Phase 7: PERSIST   ← state.py                           │
│    save_state() → .loop-state.json                       │
└─────────────────────────────────────────────────────────┘
```

---

## 各文件详细设计

### 1. config.py — 配置集中管理

```python
WORKDIR: Path          # loop-agent 目录绝对路径
REPO_ROOT: Path        # 父仓库根目录（worktree 操作用）
MODEL: str             # 从 .env 加载
FALLBACK_MODEL: str    # 备用模型
MAKER_MAX_TURNS = 50   # Maker 子代理轮次上限
CHECKER_MAX_TURNS = 20 # Checker 子代理轮次上限
STATE_FILE             # .loop-state.json 路径
SKILLS_DIR             # skills/ 路径
MOCK_DATA_DIR          # mock_data/ 路径
```

### 2. agent_loop.py — 参数化核心循环

从 s01/s02 提取，参数化使其可被 maker 和 checker 共用：

```python
def run_agent(
    system: str,
    messages: list,
    tools: list[dict],
    handlers: dict[str, Callable],
    max_turns: int = 30,
    cwd: Path | None = None,  # 工作目录（worktree 路径）
) -> str:
    # s01 的 while True 循环，加 max_turns 安全限制
    # 返回最终文本响应
```

关键复用：
- s01 的 `while stop_reason == "tool_use"` 循环结构
- s02 的 `TOOL_HANDLERS` 分发模式
- s02 的 `safe_path()` 工作区隔离
- s06 的 `extract_text()` 辅助函数

### 3. triggers.py — 四种触发源

```python
@dataclass
class TriggerEvent:
    source: str        # "manual" | "goal" | "cron" | "ci_failure"
    prompt: str        # 任务描述
    goal_condition: str | None  # Goal 模式的验证条件
    metadata: dict     # issue 编号、CI run ID 等
```

| 触发源 | 实现方式 | 复用来源 |
|--------|----------|----------|
| Manual | `queue.Queue`，REPL 线程写入 | 新实现 |
| Goal | `subprocess.run(verify_command)`，非零退出=仍需工作 | Osmani 的 "keep working until condition met" |
| Cron | 守护线程 + 5 字段 cron 匹配 | s14 `_cron_field_matches`、`cron_matches` |
| CI Failure | `github_mock.get_failed_ci_runs()` + 已处理过滤 | 新实现（mock） |

### 4. task_discovery.py — 任务发现

```python
@dataclass
class TaskItem:
    id: str            # "issue_42" | "ci_run_789"
    source: str        # 来源类型
    title: str
    description: str
    branch_hint: str   # 建议的 worktree 分支名
    files_hint: list[str]  # 可能涉及的文件
```

- `discover_from_trigger(event)` → 将 TriggerEvent 转换为 TaskItem
- `filter_already_processed(items, state)` → 过滤 state 中已处理的项

### 5. maker.py — Maker 子代理

```python
@dataclass
class MakerResult:
    task_id: str
    success: bool
    files_changed: list[str]
    branch: str
    summary: str
    test_output: str

def run_maker(task: TaskItem) -> MakerResult:
    # 1. 创建 worktree
    # 2. 构建系统提示（含任务描述 + 技能目录）
    # 3. 定义工具：bash, read_file, write_file, edit_file, glob
    # 4. 调用 agent_loop.run_agent(cwd=worktree_path, max_turns=50)
    # 5. 收集 git diff --stat
    # 6. 运行测试
    # 7. 返回 MakerResult
```

**复用模式：**
- s06 的 fresh messages[] 上下文隔离
- s02 的文件工具 + safe_path
- s10 的系统提示组装

### 6. checker.py — Checker 子代理

```python
@dataclass
class CheckerResult:
    task_id: str
    approved: bool
    issues: list[str]
    suggestions: list[str]
    summary: str

def run_checker(maker_result: MakerResult) -> CheckerResult:
    # 1. 获取 worktree 路径
    # 2. 运行 git diff 获取完整变更集
    # 3. 构建审查系统提示（含 diff + 编码规范）
    # 4. 定义只读工具：bash(受限), read_file（无 write_file/edit_file）
    # 5. 调用 agent_loop.run_agent(max_turns=20)
    # 6. 解析 APPROVED/REJECTED 关键字
    # 7. 返回 CheckerResult
```

**关键安全约束：** Checker 的工具集故意排除 `write_file` 和 `edit_file`，强制只读。

**输出协议：** 最终响应必须包含：
- `APPROVED: <summary>` 或
- `REJECTED: <问题列表>`

### 7. worktree_manager.py — Worktree 管理

从 s18 提取，去除 teammate/protocol 耦合：

```python
def create_worktree(name: str) -> Path     # 验证名称 + git worktree add
def remove_worktree(name: str, discard=False) -> str  # 安全检查 + 删除
def list_worktrees() -> list[dict]         # 列出活跃 worktree
def get_worktree_path(name: str) -> Path   # 获取路径
```

- 分支命名：`wt/{name}`
- 名称验证：正则拒绝路径遍历（s18 line 153）
- 删除前检查未提交变更

### 8. state.py — 持久化状态

```json
{
    "version": 1,
    "last_run_ts": 1750000000.0,
    "active_goals": [
        {
            "goal": "all tests pass",
            "verify_command": "pytest tests/",
            "attempts": 2,
            "last_error": "test_auth_timeout FAILED"
        }
    ],
    "processed_items": ["issue_42", "ci_run_789"],
    "active_worktrees": [
        {"name": "fix-auth-timeout", "task_id": "issue_42", "branch": "wt/fix-auth-timeout"}
    ],
    "history": [
        {
            "cycle_ts": 1750000000.0,
            "trigger_source": "ci_failure",
            "tasks": ["ci_run_789"],
            "outcomes": [{"task_id": "ci_run_789", "checker_result": "approved", "integration": "PR #15 created"}]
        }
    ],
    "cron_jobs": [{"id": "cron_001", "cron": "*/5 * * * *", "prompt": "Check CI"}],
    "error_log": [{"ts": 1750000100.0, "phase": "execute", "error": "TimeoutError"}]
}
```

关键函数：
- `load_state()` / `save_state()` — 原子写入（写临时文件 + rename）
- `record_cycle()` — 追加历史记录
- `mark_processed()` / `is_processed()` — 已处理项管理

### 9. github_mock.py — Mock GitHub API

接口签名与真实 GitHub API 一致，替换时只需改一个文件：

```python
class GitHubMock:
    def list_open_issues(self) -> list[dict]
    def get_issue(self, number: int) -> dict
    def get_failed_ci_runs(self, since: float = 0) -> list[dict]
    def create_pull_request(self, title, body, head, base) -> dict
    def add_pr_comment(self, pr_number, body) -> dict
    def get_ci_logs(self, run_id: int) -> str
```

### 10. skills.py — 技能加载

复用 s07 的两层注入模式：
- Layer 1：技能名 + 描述放入系统提示（~100 tokens/技能）
- Layer 2：`load_skill(name)` 按需加载完整内容（~2000 tokens/技能）

---

## Osmani 六大组件映射

| 组件 | 代码文件 | 实现方式 |
|------|----------|----------|
| **Automations** | triggers.py | Cron 守护线程 + Goal 验证循环 + CI 轮询 |
| **Worktrees** | worktree_manager.py | s18 提取，每个任务独立分支和目录 |
| **Skills** | skills.py + SKILL.md | s07 两层注入，项目知识编码化 |
| **Plugins** | github_mock.py | Mock 实现，接口兼容真实 GitHub API |
| **Sub-agents** | maker.py + checker.py | s06 上下文隔离，Maker 写 + Checker 审 |
| **State** | state.py | 单文件 .loop-state.json，原子写入 |

---

## 与现有 s01-s20 的关系

**直接复用：**
- s01 的 while 循环 → agent_loop.py
- s02 的 TOOL_HANDLERS + safe_path → agent_loop.py
- s06 的 fresh messages[] 隔离 → maker.py, checker.py
- s07 的两层技能加载 → skills.py
- s10 的系统提示组装 → maker.py, checker.py
- s14 的 cron 匹配函数 → triggers.py
- s18 的 worktree 管理 → worktree_manager.py

**关键差异：**
- 无 MessageBus（s15-s17）— 用同步编排器代替异步邮箱
- 无自主代理（s17）— 编排器显式分配，代理不自取任务
- 无后台任务（s13）— 任务在周期内顺序执行
- 单状态文件 — 替代 s12 的每任务 JSON 文件
- Mock 优先 — 无需外部服务即可运行
- Goal 模式 — 新增，运行验证命令直到通过

---

## 分阶段实施顺序

### Phase 1: 基础层
**文件：** config.py, agent_loop.py, state.py
**目标：** 核心循环可运行，状态可读写

### Phase 2: Mock 数据 + 技能
**文件：** github_mock.py, skills.py, mock_data/*.json, skills/loop-engineering/SKILL.md
**目标：** Mock API 返回真实数据，技能可加载

### Phase 3: Worktree 管理
**文件：** worktree_manager.py
**目标：** 可编程创建/删除 worktree

### Phase 4: Maker 子代理
**文件：** maker.py
**目标：** Maker 在 worktree 中实现代码变更

### Phase 5: Checker 子代理
**文件：** checker.py
**目标：** Checker 审查 diff 并输出 APPROVED/REJECTED

### Phase 6: 触发系统
**文件：** triggers.py
**目标：** 四种触发源独立工作

### Phase 7: 任务发现
**文件：** task_discovery.py
**目标：** 触发事件 → TaskItem 转换

### Phase 8: 编排器
**文件：** orchestrator.py
**目标：** 七阶段循环端到端运行

### Phase 9: 入口
**文件：** main.py
**目标：** REPL + CLI 模式（--once, --daemon, --goal）

### Phase 10: 测试
**文件：** tests/*.py
**目标：** 每个模块的 pytest 测试

---

## 验证方式

1. **单元测试：** 每个模块独立测试（mock LLM 调用）
2. **集成测试：** 手动触发 → 完整周期 → 检查状态文件
3. **端到端：** `python main.py --goal "all tests pass" --verify "pytest tests/"` 验证 Goal 模式
4. **Mock 验证：** 用 mock_data 中的 issue 和 CI 数据运行完整循环

---

## 关键文件（按重要性）

1. `orchestrator.py` — 七阶段循环的核心协调器
2. `agent_loop.py` — 参数化核心循环，maker/checker 共用
3. `maker.py` — Maker 子代理，在隔离 worktree 中实现代码
4. `checker.py` — Checker 子代理，只读审查
5. `state.py` — 持久化状态，循环的"记忆"
