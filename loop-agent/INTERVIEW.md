# Loop Agent 面试准备文档

## 第一部分：项目概述

### 30 秒版本

> 我做了一个自主编码 Agent 系统，核心理念是 **Agent = Model + Harness**。Model 用 Claude API 提供推理能力，Harness 是我设计的七阶段编排流水线：触发 → 发现 → 分配 → 执行 → 验证 → 集成 → 持久化。关键设计是 **Maker-Checker 模式**：Maker 有读写工具负责编码，Checker 只有只读工具负责审查，通过**工具隔离**（而非提示词约束）保证安全性。系统支持手动触发、Goal 模式（持续执行直到条件满足）、Cron 定时任务和 CI 失败触发四种方式。

### 2 分钟版本

> 这个项目基于 learn-claude-code 教学仓库（s01-s20）的核心模式构建，但不是简单复用，而是在其基座上实现了完整的自主编码工作流。
>
> **架构分层**：底层是 s20_comprehensive 提供的 agent_loop（while 循环 + tool_use 驱动）、上下文管理、技能加载等 26 个基础工具。我在其上封装了 loop_agent.py 作为适配层，通过 `importlib` 动态导入 s20，实现工具集的临时替换和恢复。最上层是 orchestrator.py 的七阶段编排器。
>
> **核心创新**：Maker-Checker 模式。Maker 拥有 bash、read_file、write_file 等读写工具，在 Git Worktree 隔离环境中执行编码（最多 50 轮）。完成后，Checker 拥有只读 bash（白名单机制：只允许 git diff、cat、grep 等命令，显式拒绝 rm、mv 等危险操作）和 read_file、glob 工具，审查代码并输出 APPROVED 或 REJECTED。被拒绝的任务最多重试 3 次，超过则升级为 needs_human。
>
> **触发系统**：支持四种触发源（手动队列、Goal 命令、Cron 表达式、CI 失败），通过优先级链（手动 > CI > Cron）调度。Goal 模式区分 shell 命令（检查退出码循环执行）和自然语言（单次执行）。
>
> **工程实践**：57 个测试用例全部通过，覆盖状态管理、触发器、工具隔离、编排器等核心模块。状态文件使用原子写入（write-then-rename）防止损坏。

### 核心理念

```
Agent = Model + Harness
```

- **Model**：Claude API 提供推理和代码生成能力
- **Harness**：七阶段循环 + Maker-Checker 模式 + 工具隔离

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | 使用 dataclass、type hints |
| API | Anthropic Claude | 支持自定义 base_url（兼容 Moonshot/Kimi） |
| 版本控制 | Git Worktree | 每个 Maker 任务一个隔离工作区 |
| 测试 | pytest | 57 个测试用例 |
| 状态管理 | JSON + 原子写入 | write-then-rename 防损坏 |

### 与 learn-claude-code s01-s20 的关系

| 维度 | s01-s20（开源） | loop-agent（增量） |
|------|----------------|-------------------|
| 定位 | 教学仓库，每课一个独立主题 | 生产级自主编码系统 |
| 复用方式 | 作为基座（s20_comprehensive） | 通过 importlib 动态导入 |
| 增量内容 | — | Maker-Checker、七阶段编排、触发系统、状态管理 |
| 关系 | 站在巨人肩膀上 | 专注增量逻辑，保持架构边界清晰 |

---

## 第二部分：技术深度问答

### 2.1 Agent Loop 核心循环

**面试官问题：**

1. 为什么用 `while True` 而不是递归？
2. `stop_reason == "tool_use"` 这个判断为什么重要？
3. `messages` 列表为什么在循环外维护？

**参考答案：**

```python
# s20_comprehensive/code.py 中的 agent_loop 核心逻辑
def agent_loop(messages, context):
    while True:
        response = client.messages.create(
            model=model_id,
            system=system_prompt,
            messages=messages,
            tools=tool_pool,
        )
        # 追加 assistant 响应到消息历史
        messages.append({"role": "assistant", "content": response.content})

        # 关键判断：模型是否要求调用工具
        if response.stop_reason != "tool_use":
            return  # 模型认为任务完成，退出循环

        # 执行所有工具调用，追加结果
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                ]})
```

**为什么用 while True 而不是递归？**
- 递归会导致调用栈增长，Python 默认递归深度限制 1000
- while 循环是尾递归优化的等价形式，内存效率更高
- 消息列表在循环外维护，自然累积上下文

**为什么 `stop_reason` 判断是关键？**
- 这是**模型驱动**的循环终止，不是代码硬编码的退出条件
- 模型通过 `stop_reason` 告诉 Harness："我需要更多信息"（tool_use）或"我完成了"（end_turn）
- 这体现了 Agent 的核心特征：**模型决定何时停止，代码只负责执行**

**为什么 messages 在循环外？**
- 每次 API 调用需要完整的对话历史（多轮对话的上下文）
- 工具调用的结果需要追加到历史中，供下一轮推理使用
- 这是"消息累积模式"——每轮循环都带着完整的上下文

**加分回答：**
- 能画出完整流程图：用户输入 → 模型推理 → tool_use? → 执行工具 → 追加结果 → 循环
- 理解 stop_reason 的多种值（end_turn、tool_use、max_tokens）及其含义
- 能解释为什么工具结果以 `role: "user"` 的形式追加（Anthropic API 的设计约定）

**红旗信号：**
- 认为是代码决定何时停止（而非模型）
- 不理解 messages 累积的作用
- 认为 while True 是"死循环"而不知道它靠 stop_reason 退出

---

### 2.2 Maker-Checker 模式

**面试官问题：**

1. 为什么 Checker 用工具隔离而不是提示词约束？
2. `read_only_bash` 的白名单机制怎么实现？
3. 最多重试 3 次的依据是什么？

**参考答案：**

```python
# loop_agent.py 中的 read_only_bash 实现
_READ_ONLY_PREFIXES = (
    "git diff", "git log", "git show", "git status",
    "cat", "head", "tail", "grep", "find", "ls",
    "wc", "python -m pytest", "pytest", "mypy", "ruff",
)
_DANGEROUS_PREFIXES = ("rm", "mv", "cp", "chmod", "chown", "dd", "mkfs")

def read_only_bash(command: str) -> str:
    cmd_lower = command.lower().strip()

    # 分割链式命令（&&、||、;、|），逐一检查
    parts = _re.split(r'\s*(?:&&|\|\||;)\s*', cmd_lower)

    for part in parts:
        part = part.strip()
        # 检查危险命令前缀（黑名单）
        if any(part.startswith(p) for p in _DANGEROUS_PREFIXES):
            return f"Permission denied: dangerous command blocked: {command}"
        # 检查 find -exec 危险操作
        if "find" in part and "-exec" in part:
            exec_section = part.split("-exec", 1)[1].strip()
            if any(exec_section.lstrip().startswith(p) for p in _DANGEROUS_PREFIXES):
                return f"Permission denied: dangerous find -exec blocked: {command}"

    # 取第一个命令判断是否在白名单
    first_cmd = parts[0].strip()
    if any(first_cmd.startswith(p) for p in _READ_ONLY_PREFIXES):
        return _s20_code.run_bash(command, cwd=wt_path)
    return f"Permission denied: read-only mode. Command not allowed: {command}"
```

**为什么用工具隔离而不是提示词约束？**

这是**安全设计的核心问题**。两种方案对比：

| 方案 | 原理 | 可靠性 | 绕过方式 |
|------|------|--------|----------|
| 提示词约束 | "你不能执行写入命令" | 低 | prompt injection、模型忽略指令 |
| 工具隔离 | Checker 根本没有 write_file 工具 | 高 | 物理上无法调用 |

**关键洞察**：模型可以忽略提示词，但调用不了不存在的工具。这是 **defense-in-depth**（纵深防御）的体现。

**白名单 + 黑名单双重检查**：
- **白名单**：只允许 `git diff`、`cat`、`grep` 等只读命令
- **黑名单**：显式拒绝 `rm`、`mv`、`chmod` 等危险命令
- **链式命令分割**：`rm -rf / && cat file` 会被 `&&` 分割后逐一检查
- **find -exec 检查**：防止 `find . -exec rm {} \;` 这种间接执行

**为什么最多重试 3 次？**
- 这是一个**经验值**：太少（1次）可能因为 Checker 过于严格而误拒；太多（5+次）浪费 API 调用
- 3 次提供了合理的"给 Maker 修正机会"的窗口
- 超过 3 次说明问题可能是系统性的，需要人工介入
- 实现上通过 `state.history` 中的 rejected 记录计数

**加分回答：**
- 能提到 prompt injection 风险（恶意代码中嵌入"忽略之前的指令"）
- 理解 defense-in-depth 原则（多层防御，不依赖单一机制）
- 能讨论更高级的沙箱方案（Docker 容器、seccomp、namespace 隔离）

**红旗信号：**
- 认为提示词约束足够安全
- 不理解白名单和黑名单的区别
- 说不清楚为什么需要链式命令分割

---

### 2.3 七阶段编排器

**面试官问题：**

1. 为什么是七阶段而不是更少？
2. `orchestrate_cycle` 的 try/finally 块保证了什么？
3. `final_status` 的四种终态分别在什么情况下触发？

**参考答案：**

```python
# orchestrator.py 的核心编排逻辑
def orchestrate_cycle(event: TriggerEvent, state: LoopState) -> CycleResult:
    """
    Phase 1: TRIGGER   — 接收触发事件（在函数外完成）
    Phase 2: DISCOVER  — 转换为任务项，过滤已处理
    Phase 3: ALLOCATE  — 创建 worktree（在 maker 中完成）
    Phase 4: EXECUTE   — Maker 子代理实现代码
    Phase 5: VERIFY    — Checker 子代理审查代码
    Phase 6: INTEGRATE — approved→记录, rejected→反馈
    Phase 7: PERSIST   — 保存状态（单次原子写入）
    """
    start_time = time.time()
    maker_result = None

    try:
        # Phase 2: DISCOVER
        task = discover_from_trigger(event)
        if task.id in state.processed_items:
            return CycleResult(final_status="skipped", ...)

        # Phase 4: EXECUTE (Maker)
        maker_result = run_maker(task_description=task.description, ...)
        if not maker_result.success:
            return CycleResult(final_status="needs_human", ...)

        # Phase 5: VERIFY (Checker)
        checker_result = run_checker(maker_result)

        # Phase 6: INTEGRATE
        if checker_result.approved:
            mark_processed(state, task.id, _save=False)
            return CycleResult(final_status="approved", ...)
        else:
            reject_count = sum(1 for h in state.history
                             if h.get("task_id") == task.id
                             and h.get("status") == "rejected")
            if reject_count >= MAX_CHECKER_RETRIES:
                return CycleResult(final_status="needs_human", ...)
            else:
                return CycleResult(final_status="rejected", ...)
    finally:
        # Phase 7: PERSIST — 无论成功失败都执行
        if maker_result:
            _cleanup_worktree(maker_result.worktree_name, state)
        save_state(state)  # 单次原子写入
```

**为什么是七阶段？**

每个阶段有明确的**单一职责**：

| 阶段 | 职责 | 如果合并会怎样 |
|------|------|---------------|
| Trigger | 接收事件 | 与 Discover 混在一起，难以支持多种触发源 |
| Discover | 任务提取 + 去重 | 与 Trigger 合并会违反单一职责 |
| Allocate | 创建隔离环境 | 在 Maker 内部完成，但逻辑上是独立阶段 |
| Execute | Maker 编码 | 核心阶段，不可合并 |
| Verify | Checker 审查 | 与 Execute 合并会失去"审查独立性" |
| Integrate | 状态更新 + 重试逻辑 | 与 Verify 合并会使 Checker 变复杂 |
| Persist | 原子写入 | 与 Integrate 合并可能丢失状态 |

**try/finally 保证了什么？**

- **资源清理**：无论 Maker/Checker 成功还是失败，worktree 都会被清理
- **状态持久化**：`save_state(state)` 在 finally 中执行，保证每次 cycle 结束时状态都被保存
- **异常安全**：即使 Maker 抛出异常，状态文件也会被正确更新（记录为 needs_human）

**四种终态：**

| 状态 | 触发条件 | 含义 |
|------|----------|------|
| `approved` | Checker 输出 APPROVED | 任务完成，代码审查通过 |
| `rejected` | Checker 输出 REJECTED，且重试次数 < 3 | 需要 Maker 修正后重试 |
| `needs_human` | Maker 失败 或 重试次数 >= 3 | 自动化流程无法解决，需人工介入 |
| `skipped` | 任务已在 processed_items 中 | 幂等性保证，跳过重复任务 |

**加分回答：**
- 能讨论每个阶段的独立失败处理（Maker 失败不影响 Checker，Checker 拒绝不影响状态持久化）
- 理解 `_save=False` 参数的作用（批量更新，减少磁盘 I/O）
- 能提出改进方案（如：阶段间加日志、加指标收集）

**红旗信号：**
- 说不清楚持久化为什么放在 finally 里
- 认为七阶段"太多了"但说不出哪些可以合并
- 不理解"跳过已处理任务"的幂等性设计

---

### 2.4 四种触发源

**面试官问题：**

1. 四种触发源的优先级是怎么设计的？
2. `_is_shell_command` 如何区分自然语言和 shell 命令？
3. Cron 的守护线程怎么保证不阻塞主循环？

**参考答案：**

```python
# triggers.py 的优先级链
def check_all_triggers() -> TriggerEvent | None:
    """按优先级检查所有触发源。"""
    # 1. 手动触发（最高优先级）
    event = check_manual()
    if event:
        return event
    # 2. CI 失败
    event = check_ci_failure()
    if event:
        return event
    # 3. Cron
    event = check_cron()
    if event:
        return event
    return None

# _is_shell_command 的 4 层检测
def _is_shell_command(text: str) -> bool:
    # 第1层：shell 操作符 → 命令
    if any(op in text for op in ["&&", "||", "|", ">", ">>", "$("]):
        return True
    # 第2层：路径分隔符 + 文件扩展名 → 命令
    if _re.search(r'[/\\]\S+\.\w+', text):
        return True
    # 第3层：自然语言特征（冠词、介词）→ 非命令
    _nl_words = {" the ", " a ", " an ", " to ", " is ", " are ", ...}
    if " " in text_lower and any(w in text_with_spaces for w in _nl_words):
        return False
    # 第4层：shell 前缀匹配 → 命令
    if any(text_lower.startswith(p) for p in shell_prefixes):
        return True
    return False

# Cron 守护线程（daemon=True 不阻塞退出）
def _cron_scheduler_loop() -> None:
    while True:
        now = datetime.now()
        for job in _cron_jobs:
            if cron_matches(job["cron"], now):
                _cron_queue.put(TriggerEvent(source="cron", ...))
        time.sleep(CRON_CHECK_INTERVAL)  # 每 60 秒检查一次
```

**优先级设计**：手动 > CI 失败 > Cron。手动触发是用户显式意图，优先级最高；CI 失败需要及时修复；Cron 是定期检查。

**_is_shell_command 的 4 层检测**：
1. **shell 操作符**（`&&`、`||`、`|`）→ 一定是命令
2. **路径 + 扩展名**（`./test.py`）→ 一定是命令
3. **自然语言特征**（冠词、介词）→ 一定不是命令
4. **shell 前缀**（`python`、`pytest`）→ 是命令

**Cron 守护线程**：`daemon=True` 表示主线程退出时自动终止，不阻塞进程。通过 `Queue` 实现线程间通信，主循环从队列中取消息。

**加分回答：**
- 能讨论优先级冲突场景（手动和 Cron 同时触发）
- 理解 daemon 线程的生命周期
- 能提出改进（Webhook 替代轮询）

**红旗信号：**
- 不理解 Queue 的线程安全作用
- 认为 _is_shell_command 的检测顺序不重要

---

### 2.5 Goal 模式

**面试官问题：**

1. "持续执行直到条件满足"的核心循环是什么？
2. 自然语言目标和 shell 命令目标的处理有什么区别？
3. pytest 的 "no tests collected" 为什么要特殊处理？

**参考答案：**

```python
# triggers.py 的 check_goal 实现
def check_goal(verify_command: str) -> TriggerEvent | None:
    # 自然语言目标：直接作为任务交给 Maker
    if not _is_shell_command(verify_command):
        return TriggerEvent(
            source="goal",
            prompt=verify_command,
            goal_condition=verify_command,
        )

    # Shell 命令目标：执行并检查退出码
    r = subprocess.run(verify_command, shell=True, cwd=REPO_ROOT, ...)
    output = r.stdout + r.stderr

    # 非零退出 = 需要继续工作
    if r.returncode != 0:
        return TriggerEvent(source="goal",
            prompt=f"Goal not yet met. Verification output:\n{output}", ...)

    # pytest 特殊处理：没有收集到测试也视为失败
    if "no tests collected" in output.lower() or "no test ran" in output.lower():
        return TriggerEvent(source="goal",
            prompt=f"Goal not yet met: no tests found.\n{output}", ...)

    # 退出码 0 且有测试通过 → 返回 None，停止循环
    return None
```

**核心循环**：`orchestrator.py` 的 `run_loop(mode="goal")` 中，每次循环调用 `check_goal`：
- 返回 `TriggerEvent` → 继续执行
- 返回 `None` → 条件满足，停止

**两种目标的区别**：

| 类型 | 判断方式 | 执行次数 | 示例 |
|------|----------|----------|------|
| Shell 命令 | 检查退出码 | 循环直到退出码 0 | `pytest tests/` |
| 自然语言 | 直接交给 Maker | 只执行一次 | "修复登录 bug" |

**为什么 pytest "no tests collected" 需要特殊处理？**
- pytest 在没有找到测试文件时返回退出码 0（成功）
- 但实际上"没有测试"应该被视为失败（Goal 未达成）
- 这是一个**边界情况**，不处理会导致循环提前退出

**加分回答：**
- 理解"持续执行直到条件满足"是 Osmani Loop Engineering 的核心模式
- 能讨论超时保护（max_cycles）的必要性
- 能提出更复杂的 Goal 条件（如：代码覆盖率 > 80%）

**红旗信号：**
- 不理解退出码 0 和"成功"的区别
- 认为自然语言目标也应该循环执行

---

### 2.6 状态管理

**面试官问题：**

1. 原子写入（write-then-rename）怎么防止状态损坏？
2. `_save=False` 参数的作用是什么？
3. 损坏的 JSON 文件怎么处理？

**参考答案：**

```python
# state.py 的原子写入实现
def save_state(state: LoopState) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    data = { ... }
    # 步骤1：写入临时文件
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    # 步骤2：原子重命名（操作系统保证原子性）
    tmp.replace(STATE_FILE)

# _save=False 的批量更新
def orchestrate_cycle(event, state):
    try:
        # ... 多次状态更新，都用 _save=False
        mark_processed(state, task.id, _save=False)
        record_cycle(state, task.id, "approved", ..., _save=False)
    finally:
        # 最后统一保存一次
        save_state(state)

# 损坏文件的容错处理
def load_state() -> LoopState:
    if not STATE_FILE.exists():
        return LoopState()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return LoopState(...)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[Warning] State file corrupted, starting fresh: {e}")
        return LoopState()  # 返回空状态，不崩溃
```

**原子写入原理**：
- `tmp.replace(STATE_FILE)` 在 POSIX 系统上是 `rename()` 系统调用
- `rename()` 是原子操作：要么完全成功，要么完全失败
- 不会出现"写了一半"的中间状态

**_save=False 的作用**：
- orchestrator 的一次 cycle 可能有多次状态更新（mark_processed、record_cycle、add_error）
- 每次都写磁盘会浪费 I/O
- 用 `_save=False` 标记"暂不保存"，在 finally 中统一保存一次
- 这是**批量更新模式**的体现

**损坏文件处理**：
- `try/except` 捕获 JSON 解析错误
- 返回空的 `LoopState()` 而不是崩溃
- 打印警告但继续运行（graceful degradation）

**加分回答：**
- 能讨论 Windows 和 Linux 的 rename 语义差异
- 理解"防御性编程"的原则
- 能提出改进（如：备份旧状态文件、版本迁移）

**红旗信号：**
- 不理解原子写入的作用
- 认为 _save=False 是"不保存"
- 不知道如何处理损坏的 JSON 文件

---

### 2.7 s20 基座复用

**面试官问题：**

1. 为什么用 `importlib` 而不是直接 `import`？
2. 工具集隔离怎么实现（临时替换 + finally 恢复）？
3. s20 的上下文压缩有几层？每层解决什么问题？

**参考答案：**

```python
# loop_agent.py 的动态导入
_spec = importlib.util.spec_from_file_location("s20_code", S20_DIR / "code.py")
_s20_code = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s20_code)

# 工具集隔离（临时替换 + finally 恢复）
def run_maker(task_description, branch_hint=""):
    orig_tools = _s20_code.BUILTIN_TOOLS
    orig_handlers = _s20_code.BUILTIN_HANDLERS
    maker_tools = [t for t in orig_tools if t["name"] in (
        "bash", "read_file", "write_file", "edit_file", "glob")]

    try:
        _s20_code.BUILTIN_TOOLS = maker_tools
        _s20_code.BUILTIN_HANDLERS = maker_handlers
        agent_loop(messages, context)
    finally:
        _s20_code.BUILTIN_TOOLS = orig_tools
        _s20_code.BUILTIN_HANDLERS = orig_handlers
```

**为什么用 importlib？**
- s20 的文件名是 `code.py`，与 Python 标准库的 `code` 模块冲突
- 直接 `import code` 会导入标准库而不是 s20
- `importlib` 允许指定文件路径，避免命名冲突

**工具集隔离的实现**：
1. 保存原始工具集：`orig_tools = _s20_code.BUILTIN_TOOLS`
2. 创建限定工具集：`maker_tools = [t for t in orig_tools if t["name"] in (...)]`
3. 临时替换：`_s20_code.BUILTIN_TOOLS = maker_tools`
4. 执行 agent_loop
5. finally 恢复：`_s20_code.BUILTIN_TOOLS = orig_tools`

**这是"猴子补丁"（Monkey Patching）模式**：在运行时修改全局状态，用完后恢复。

**加分回答：**
- 理解模块导入的命名空间隔离
- 能讨论猴子补丁的风险（线程安全、异常恢复）
- 能提出更好的方案（依赖注入、接口抽象）

**红旗信号：**
- 不理解 importlib 的作用
- 认为 finally 可以省略
- 不知道什么是猴子补丁

---

## 第三部分：系统设计问答

### 3.1 并发 Maker 场景

**问题**：当前 orchestrator 的 for 循环是串行执行的，如何支持 10 个任务同时处理？

**局限性**：
```python
# orchestrator.py 的串行循环
for i in range(max_cycles):
    result = orchestrate_cycle(event, state)  # 一次只处理一个
    results.append(result)
```

**改进方案**：
```python
# 使用线程池 + 状态锁
from concurrent.futures import ThreadPoolExecutor
import threading

state_lock = threading.Lock()

def parallel_orchestrate(events, state):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for event in events:
            # 每个任务在独立 worktree 中执行
            futures.append(executor.submit(
                orchestrate_cycle_safe, event, state, state_lock
            ))
        return [f.result() for f in futures]

def orchestrate_cycle_safe(event, state, lock):
    with lock:  # 状态更新需要加锁
        return orchestrate_cycle(event, state)
```

**关键挑战**：
- 状态文件的并发写入需要锁保护
- 每个 Maker 需要独立的 worktree（已支持）
- Checker 审查需要访问 Maker 的 worktree（需要路径传递）

---

### 3.2 真实 GitHub API 场景

**问题**：当前使用 `GitHubMock`，如何替换为真实 API？

**局限性**：
- Mock 数据硬编码，无法处理真实的 API 错误
- 没有认证、限流、重试机制
- 无法接收 Webhook 推送

**改进方案**：
```python
# 接口兼容设计
class GitHubAPI:
    def get_failed_ci_runs(self, since_run_id: int) -> list[dict]:
        """真实 API 调用"""
        response = requests.get(
            f"https://api.github.com/repos/{REPO}/actions/runs",
            headers={"Authorization": f"token {TOKEN}"},
            params={"status": "failure", "since": since_run_id}
        )
        response.raise_for_status()
        return response.json()["workflow_runs"]

# 错误重试
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def call_github_api():
    ...
```

**Webhook 触发**：
```python
# Flask 接收 Webhook
@app.route("/webhook", methods=["POST"])
def github_webhook():
    event = request.json
    if event["action"] == "completed" and event["conclusion"] == "failure":
        enqueue_ci_failure(event)
    return "OK"
```

---

### 3.3 CI/CD 集成场景

**问题**：如何在 GitHub Actions 中运行 loop-agent？

**局限性**：
- 当前是本地 REPL 模式，没有 CLI 入口
- 没有退出码（exit code）机制
- 无法自动创建 PR

**改进方案**：
```yaml
# .github/workflows/agent-fix.yml
name: Auto-fix CI failures
on:
  workflow_run:
    workflows: ["Tests"]
    types: [completed]

jobs:
  auto-fix:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run loop-agent
        run: |
          python loop-agent/main.py --once --exit-code
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Create PR if changes
        if: success()
        uses: peter-evans/create-pull-request@v5
        with:
          title: "Auto-fix: CI failure"
          body: "Automated fix by loop-agent"
```

**CLI 入口设计**：
```python
# main.py 的命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--once", action="store_true", help="单次执行")
parser.add_argument("--goal", type=str, help="Goal 模式")
parser.add_argument("--exit-code", action="store_true", help="返回退出码")
args = parser.parse_args()

# 退出码机制
results = run_loop(mode="once" if args.once else "goal", ...)
if args.exit_code:
    sys.exit(0 if all(r.final_status == "approved" for r in results) else 1)
```

---

## 第四部分：工程实践问答

### 4.1 测试策略

**最有价值的测试用例：**

| 排名 | 测试 | 文件 | 为什么重要 |
|------|------|------|-----------|
| 1 | `test_checker_read_only_bash_blocks_chained_commands` | test_maker_checker.py | 验证安全机制：链式命令、find -exec 都被阻止 |
| 2 | `test_orchestrate_three_rejections` | test_orchestrator.py | 验证重试上限：3 次拒绝后升级为 needs_human |
| 3 | `test_load_state_corrupted` | test_state.py | 验证容错：损坏的 JSON 文件返回默认状态 |
| 4 | `test_filter_already_processed` | test_orchestrator.py | 验证幂等性：已处理任务不重复执行 |
| 5 | `test_atomic_write` | test_state.py | 验证原子性：不留下 .tmp 临时文件 |

**测试覆盖范围：**

| 测试文件 | 测试数量 | 覆盖场景 |
|----------|----------|----------|
| test_state.py | 11 | 原子写入、损坏恢复、去重操作、worktree 管理 |
| test_triggers.py | 12 | cron 匹配、shell/NL 检测、优先级链 |
| test_github_mock.py | 9 | Mock API 覆盖 |
| test_maker_checker.py | 8 | 工具隔离、只读 bash 白名单 |
| test_orchestrator.py | 5 | 端到端循环、重试逻辑、跳过去重 |
| test_task_discovery.py | 7 | 任务生成、内容哈希 |
| test_config.py | 5 | 配置加载 |
| **总计** | **57** | **全部通过** |

**关键测试代码片段：**

```python
# test_maker_checker.py — 验证只读 bash 的安全性
def test_checker_read_only_bash_blocks_chained_commands():
    # 危险命令被阻止
    assert "BLOCKED" in read_only_bash("rm -rf /")
    assert "BLOCKED" in read_only_bash("ls; rm -rf /")        # 分号链式
    assert "BLOCKED" in read_only_bash("git log; rm -rf /")   # 看似安全+危险
    assert "BLOCKED" in read_only_bash("cat x && rm -rf /")   # && 链式
    assert "BLOCKED" in read_only_bash("find / -exec rm -rf {} +")  # find -exec

    # 只读命令被允许
    assert "ALLOWED" in read_only_bash("git diff")
    assert "ALLOWED" in read_only_bash("cat README.md")
```

```python
# test_state.py — 验证损坏文件容错
def test_load_state_corrupted(tmp_path):
    state_file = tmp_path / ".loop-state.json"
    state_file.write_text("not valid json{{{", encoding="utf-8")
    state = load_state()
    assert state.version == 1
    assert state.processed_items == []
    # 不崩溃，返回默认状态
```

---

### 4.2 错误处理

| 场景 | 处理方式 | 代码位置 |
|------|----------|----------|
| Maker 执行异常 | try/except 捕获，返回 MakerResult(success=False) | loop_agent.py:178 |
| Checker 执行异常 | try/except 捕获，返回 CheckerResult(approved=False) | loop_agent.py:365 |
| Worktree 清理失败 | try/except 捕获，打印警告但不崩溃 | orchestrator.py:47 |
| 状态文件损坏 | try/except 捕获 JSONDecodeError，返回空状态 | state.py:57 |
| API 超时 | subprocess.TimeoutExpired 捕获，返回 TriggerEvent | triggers.py:124 |
| pytest 未安装 | FileNotFoundError 捕获，返回 "(pytest not available)" | loop_agent.py:219 |

**关键设计原则**：
- **Graceful Degradation**：出错时返回安全的默认值，而不是崩溃
- **finally 保证清理**：无论成功失败，worktree 和状态都会被正确处理
- **错误日志**：`add_error()` 记录错误到 `state.error_log`，便于排查

---

### 4.3 状态一致性

**原子写入防止半写状态**：
```python
# state.py — write-then-rename 模式
tmp = STATE_FILE.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
tmp.replace(STATE_FILE)  # 原子操作
```

**_save=False 允许批量更新**：
```python
# orchestrator.py — 一次 cycle 中多次状态更新，最后统一保存
try:
    mark_processed(state, task.id, _save=False)
    record_cycle(state, task.id, "approved", ..., _save=False)
finally:
    save_state(state)  # 只写一次磁盘
```

**幂等操作（mark_processed 去重）**：
```python
# state.py — 防止重复添加
def mark_processed(state, item_id, _save=True):
    if item_id not in state.processed_items:
        state.processed_items.append(item_id)
```

---

## 第五部分：不足和改进

### 5.1 主要不足

| 不足 | 具体表现 | 影响 | 改进方向 |
|------|----------|------|----------|
| **串行执行** | orchestrator 的 for 循环一次只处理一个任务 | 吞吐量低 | 线程池 + 状态锁 |
| **Mock 数据** | GitHubMock 硬编码数据，无法处理真实 API | 无法生产使用 | 接口兼容 + Webhook |
| **Checker 判断粗糙** | 靠关键词匹配 APPROVED/REJECTED | 可能误判 | 结构化输出 + JSON Schema |
| **没有增量学习** | 每次 cycle 独立，不从历史学习 | 重复犯错 | 向量数据库 + 经验库 |
| **没有人工审核** | 自动化程度过高，缺乏 human-in-the-loop | 风险不可控 | 暂停点 + 审批流 |

### 5.2 面试中如何主动暴露

**话术模板**：

> "如果重做这个项目，我会在三个方面改进：
> 1. **并发执行**：当前 orchestrator 是串行的，用线程池可以并行处理多个任务
> 2. **真实 API**：当前用 Mock 数据，替换为真实 GitHub API 需要处理认证、限流、Webhook
> 3. **结构化输出**：Checker 的 APPROVED/REJECTED 靠关键词匹配，用 JSON Schema 可以更可靠"

> "当前最大的局限是 **串行执行**。一次只能处理一个任务，如果有 10 个 issue 需要修复，得排队。这是架构设计时的取舍——先保证正确性，再优化性能。"

> "如果时间充裕，我会添加 **人工审核环节**。自动化程度过高是风险——Maker 生成的代码可能有安全隐患，需要 human-in-the-loop 做最终判断。"

**主动暴露的好处**：
- 展示**自我认知**：知道自己项目的不足
- 展示**改进能力**：能提出具体的改进方案
- 展示**工程判断**：理解"先正确后优化"的取舍

---

## 第六部分：行为面试准备

### Q1: 遇到最大的技术挑战是什么？

**STAR 框架回答**：

> **Situation**：在设计 Checker 子代理时，需要确保它只能审查代码，不能修改文件。
>
> **Task**：最初想用提示词约束（"你不能执行写入命令"），但意识到这不够安全。
>
> **Action**：改为**工具隔离**方案——Checker 根本没有 `write_file`、`edit_file` 工具，bash 也用白名单限制为只读命令。同时设计了链式命令分割和 find -exec 检查，防止绕过。
>
> **Result**：测试验证了所有危险命令都被阻止，只读命令正常工作。这个设计体现了 **defense-in-depth** 原则——模型可以忽略提示词，但调用不了不存在的工具。

### Q2: 为什么选择这个架构？

**回答要点**：

> 1. **复用 s20 作为基座**：s20 已经实现了 agent_loop、上下文管理、技能加载等 26 个基础工具，我不需要重新发明轮子
> 2. **importlib 动态导入**：避免与标准库的 `code` 模块冲突，同时实现工具集的临时替换
> 3. **七阶段编排**：每个阶段单一职责，便于测试和维护
> 4. **Maker-Checker 模式**：实现"编码-审查"分离，通过工具隔离保证安全性
>
> 核心原则是：**站在巨人肩膀上，专注增量逻辑**。s20 是"巨人"，loop-agent 是"增量"。

### Q3: 从这个项目学到最重要的经验？

**回答**：

> "**工具隔离比提示词约束更可靠。**"
>
> 模型可以忽略提示词（prompt injection、指令遗忘），但调用不了不存在的工具。这个洞察改变了我对 AI 安全的理解——不要依赖模型的"自律"，要从物理层面限制它的能力。
>
> 这个经验可以推广到其他场景：
> - API 权限控制：只授予必要的权限
> - 容器隔离：限制系统调用
> - 网络策略：限制出站连接

### Q4: 如何调试 Maker-Checker 的问题？

**回答**：

> 1. **查看 state.json**：`history` 字段记录了每次 cycle 的状态（approved/rejected/needs_human）
> 2. **查看 error_log**：`error_log` 字段记录了错误详情
> 3. **查看 worktree**：如果 worktree 没有被清理，可以手动检查代码变更
> 4. **查看 diff**：Maker 的 `diff_stat` 和 Checker 的 `diff_content` 都会打印
> 5. **单步调试**：用 `--once` 模式单次执行，而不是 daemon 循环

### Q5: 如何扩展支持新的触发源？

**回答**：

> 1. 在 `triggers.py` 中添加新的 `check_xxx()` 函数
> 2. 在 `check_all_triggers()` 中按优先级添加调用
> 3. 在 `task_discovery.py` 的 `discover_from_trigger()` 中添加新的分支
> 4. 编写对应的测试用例
>
> 例如，添加 Slack 触发源：
> ```python
> def check_slack() -> TriggerEvent | None:
>     # 轮询 Slack API 获取新消息
>     messages = slack_api.get_messages(channel="#bugs")
>     if messages:
>         return TriggerEvent(source="slack", prompt=messages[0]["text"])
>     return None
> ```

---

## 第七部分：代码速查表

### 核心函数位置

| 函数 | 文件 | 行号 | 说明 |
|------|------|------|------|
| `agent_loop` | s20_comprehensive/code.py | ~1956 | 核心 while 循环，stop_reason 驱动 |
| `run_maker` | loop_agent.py | 112 | Maker 子代理：创建 worktree + 执行编码 |
| `run_checker` | loop_agent.py | 235 | Checker 子代理：只读审查 + 输出 APPROVED/REJECTED |
| `read_only_bash` | loop_agent.py | 283 | 只读安全沙箱：白名单 + 黑名单双重检查 |
| `orchestrate_cycle` | orchestrator.py | 51 | 七阶段编排：try/finally 保证清理和持久化 |
| `run_loop` | orchestrator.py | 164 | 持续运行循环：once/goal/daemon 三种模式 |
| `check_all_triggers` | triggers.py | 252 | 优先级链：手动 > CI > Cron |
| `_is_shell_command` | triggers.py | 51 | 4 层检测：操作符→路径→NL特征→前缀 |
| `check_goal` | triggers.py | 83 | Goal 触发：shell 检查退出码，NL 单次执行 |
| `save_state` | state.py | 62 | 原子写入：write-then-rename |
| `load_state` | state.py | 41 | 防御性加载：损坏文件返回默认状态 |
| `discover_from_trigger` | task_discovery.py | 29 | 任务发现：TriggerEvent → TaskItem |

### 关键代码片段（面试中最值得引用的）

**片段 1：Agent Loop 核心循环**
```python
def agent_loop(messages, context):
    while True:
        response = client.messages.create(
            model=model_id, system=system_prompt,
            messages=messages, tools=tool_pool,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return  # 模型决定停止
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                ]})
```
**引用时机**：解释 Agent 的核心特征——模型驱动循环终止。

**片段 2：read_only_bash 安全沙箱**
```python
def read_only_bash(command: str) -> str:
    parts = _re.split(r'\s*(?:&&|\|\||;)\s*', command.lower())
    for part in parts:
        if any(part.startswith(p) for p in _DANGEROUS_PREFIXES):
            return f"Permission denied: dangerous command blocked"
    first_cmd = parts[0].strip()
    if any(first_cmd.startswith(p) for p in _READ_ONLY_PREFIXES):
        return _s20_code.run_bash(command, cwd=wt_path)
    return f"Permission denied: read-only mode"
```
**引用时机**：解释工具隔离 vs 提示词约束的安全设计。

**片段 3：原子写入**
```python
def save_state(state: LoopState) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)  # 原子操作
```
**引用时机**：解释状态管理的一致性保证。

**片段 4：try/finally 资源清理**
```python
def orchestrate_cycle(event, state):
    try:
        maker_result = run_maker(...)
        checker_result = run_checker(maker_result)
        # ... 状态更新
    finally:
        _cleanup_worktree(maker_result.worktree_name, state)
        save_state(state)  # 无论成功失败都保存
```
**引用时机**：解释异常安全和资源清理。

**片段 5：工具集隔离（猴子补丁）**
```python
orig_tools = _s20_code.BUILTIN_TOOLS
try:
    _s20_code.BUILTIN_TOOLS = maker_tools  # 临时替换
    agent_loop(messages, context)
finally:
    _s20_code.BUILTIN_TOOLS = orig_tools  # 恢复
```
**引用时机**：解释 s20 基座复用和工具集隔离。

---

## 第八部分：面试官视角

### 重点考察维度

| 维度 | 考察点 | 如何验证 |
|------|--------|----------|
| **技术深度** | Agent Loop 的 while + stop_reason 机制 | "为什么用 while True 而不是递归？" |
| **安全意识** | 工具隔离 vs 提示词约束的区别 | "为什么 Checker 不用提示词约束？" |
| **系统设计** | 七阶段编排的职责分离 | "为什么是七阶段而不是更少？" |
| **工程素养** | 测试覆盖、原子写入、资源清理 | "损坏的 JSON 文件怎么处理？" |
| **复用判断** | 为什么选择 s20 作为基座 | "为什么用 importlib 而不是直接 import？" |

### 面试官会追问的方向

| 问题 | 追问方向 | 考察能力 |
|------|----------|----------|
| "为什么用 while True？" | 递归深度限制、内存效率 | 基础知识 |
| "read_only_bash 怎么实现？" | 链式命令分割、find -exec 检查 | 安全意识 |
| "为什么用 importlib？" | 命名空间冲突、猴子补丁风险 | 工程经验 |
| "如何支持并发？" | 线程池、状态锁、Worktree 隔离 | 系统设计 |
| "如何替换 Mock？" | 接口兼容、错误重试、Webhook | 架构能力 |

### 综合评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术深度 | ⭐⭐⭐⭐ | 对 Agent Loop、工具隔离有扎实理解 |
| 系统设计 | ⭐⭐⭐⭐ | 七阶段编排清晰，职责分离合理 |
| 工程素养 | ⭐⭐⭐⭐ | 57 个测试通过，有原子写入、资源清理 |
| 创新性 | ⭐⭐⭐ | Goal 模式是亮点，但整体是方法论落地 |
| 完成度 | ⭐⭐⭐⭐ | 三种模式可用，文档完整 |

### 一句话评语

> "候选人展现了扎实的 Agent 工程能力，架构设计清晰，安全意识强。对 s20 基座的理解需要进一步验证，但整体是暑期实习的合格候选人。"

### 面试官可能的顾虑

| 顾虑 | 候选人应对策略 |
|------|---------------|
| "s20 是开源的，你自己做了多少？" | 强调增量部分：Maker-Checker、七阶段编排、触发系统、状态管理 |
| "为什么用 Mock 而不是真实 API？" | 坦诚说明：先保证功能正确，再替换真实 API |
| "串行执行怎么解决？" | 提出改进方案：线程池 + 状态锁 + Worktree 隔离 |
| "Checker 判断太粗糙？" | 提出改进：JSON Schema 结构化输出替代关键词匹配 |

---

## 附录：面试流程建议

### 面试前准备

1. **通读本文档**，重点记忆代码片段和关键数字（57 个测试、七阶段、三种模式）
2. **画一遍架构图**：Trigger → Discover → Allocate → Execute → Verify → Integrate → Persist
3. **准备 3 个故事**：技术挑战（工具隔离）、架构决策（s20 复用）、工程实践（测试覆盖）

### 面试中策略

1. **先说结论**：用 30 秒版本开场
2. **画图辅助**：七阶段流程图、Maker-Checker 流程图
3. **代码示例**：被问到具体实现时，引用代码片段
4. **主动暴露不足**：展示自我认知和改进能力

### 面试后复盘

1. 哪些问题没答好？→ 补充到本文档
2. 哪些追问没预料到？→ 更新"面试官会追问的方向"
3. 哪些答案需要优化？→ 完善"参考答案"

---

**文档版本**：v1.0
**生成时间**：2026-06-17
**适用岗位**：Agent 应用工程师暑期实习生
