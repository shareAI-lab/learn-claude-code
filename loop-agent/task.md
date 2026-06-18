# Loop Agent 改进任务清单

## 使用方式

在 Claude Code 中执行：

```
/goal 请打开 loop-agent/task.md，按 Phase 顺序逐条执行。每完成一个任务，将状态改为"已完成"。每完成一个 Phase 后，新开一个 Agent 运行 `pytest tests/ -v` 验证无回归，验证通过后再进入下一个 Phase。遇到问题无法完成的标记为"需人工处理"并写原因。全部完成或超过 30 轮时停止。
```

**任务状态：** 待处理 | 已完成 | 需人工处理

**任务边界：**
- 只修改 `loop-agent/` 目录下的文件，不改动 `s20_comprehensive/` 或父目录
- 不删除现有测试，只新增或修改
- 不引入新外部依赖，除 Phase 5 的 `requests`
- 保持所有 CLI 参数和 REPL 命令行为不变
- 每个 Phase 的代码改动控制在 3 个源文件以内（不含测试）

---

## Phase 1: 修复 Bug + 清理

### 1.1 修复 remove_worktree 缺少 _save 参数

**状态：** 已完成
**文件：** `state.py`
**问题：** `remove_worktree()` 签名是 `def remove_worktree(state, name)`，但 `orchestrator.py:46` 调用时传了 `_save=False`，运行时会抛 `TypeError`
**操作：** 给 `remove_worktree` 添加 `_save=True` 参数，当 `_save=False` 时跳过 `save_state()` 调用，与 `record_cycle`、`mark_processed`、`add_error` 保持一致

### 1.2 让 MAKER_MAX_TURNS / CHECKER_MAX_TURNS 实际生效

**状态：** 已完成
**文件：** `loop_agent.py`
**问题：** `config.py` 定义了 `MAKER_MAX_TURNS=50` 和 `CHECKER_MAX_TURNS=20`，但 `run_maker` 和 `run_checker` 中从未使用
**操作：** 在 `run_maker` 和 `run_checker` 的 `agent_loop` 调用中传入对应的 max_turns 限制

### 1.3 删除空目录

**状态：** 需人工处理
**原因：** prompts/ 和 tools/ 目录不在 git 跟踪中（未提交），删除对代码无影响，跳过

---

## Phase 2: Checker 结构化输出

### 2.1 修改 Checker 要求 JSON 输出

**状态：** 已完成
**文件：** `loop_agent.py`
**操作：**
1. 修改 Checker 的 system prompt（约 line 337-349），要求输出格式为：
   ```json
   {"verdict": "APPROVED", "issues": [], "summary": "..."}
   ```
   或
   ```json
   {"verdict": "REJECTED", "issues": ["问题1", "问题2"], "summary": "..."}
   ```
2. 修改解析逻辑（约 line 375-391）：
   - 用 `re.search(r'\{[^{}]*\}', output, re.DOTALL)` 提取 JSON
   - 用 `json.loads` 解析，取 `verdict` 字段判断 approved
   - 从 `issues` 字段提取问题列表
   - **Fallback**：JSON 解析失败时回退到当前的子串匹配（`"APPROVED" in output`）

### 2.2 补充 Checker 测试

**状态：** 已完成
**文件：** `tests/test_maker_checker.py`
**操作：** 新增以下测试：
- `test_checker_structured_json_approved`：mock agent_loop 输出标准 JSON，验证 approved=True
- `test_checker_structured_json_rejected`：mock 输出 REJECTED JSON，验证 approved=False 和 issues 提取
- `test_checker_fallback_malformed_json`：mock 输出非 JSON 文本，验证回退到子串匹配
- `test_checker_maker_failed`：传入 maker_result.success=False，验证直接返回 rejected

---

## Phase 3: 消除 Monkey-Patch

### 3.1 提取 _run_agent_with_tools 函数

**状态：** 已完成
**说明：** 已在 Phase 1 中实现。`_run_agent_with_tools` 使用 s20 底层函数（call_llm, call_tool_handler 等）构建独立循环，支持 max_turns，不修改全局状态。

### 3.2 重构 run_maker 和 run_checker

**状态：** 已完成
**说明：** run_maker 和 run_checker 已改用 `_run_agent_with_tools`，所有 monkey-patch 代码已删除。

---

## Phase 4: Token 预算控制

### 4.1 添加 token 统计和预算配置

**状态：** 已完成
**文件：** `config.py`、`loop_agent.py`、`orchestrator.py`
**操作：**
1. `config.py` 添加 `TOKEN_BUDGET = int(os.environ.get("TOKEN_BUDGET", "0"))`（0 = 不限制）
2. `_run_agent_with_tools` 中每次 LLM 调用后累加 token 用量，超预算时提前终止
3. `MakerResult` 和 `CheckerResult` 添加 `tokens_used: int = 0`
4. `CycleResult` 添加 `total_tokens: int = 0`，在 orchestrate_cycle 中汇总
5. 新增测试 `test_token_budget_exceeded`

---

## Phase 5: 真实 GitHub API 集成（只读）

### 5.1 新建 github_client.py

**状态：** 已完成
**文件：** 新建 `github_client.py`
**操作：** 使用 `requests` 实现只读 GitHub API：
- `list_open_issues(labels=None)` → `GET /repos/{owner}/{repo}/issues`
- `get_failed_ci_runs(since_run_id=0)` → `GET /repos/{owner}/{repo}/actions/runs?status=failure`
- `get_ci_logs(run_id)` → `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs`
- 返回数据结构与 `GitHubMock` 兼容

### 5.2 集成到 triggers.py

**状态：** 已完成
**文件：** `triggers.py`、`requirements.txt`
**操作：**
1. `requirements.txt` 添加 `requests>=2.28.0`
2. `triggers.py` 根据 `GITHUB_TOKEN` 是否非空选择 `GitHubClient` 或 `GitHubMock`

### 5.3 GitHub 客户端测试

**状态：** 已完成
**文件：** 新建 `tests/test_github_client.py`
**操作：** 用 `unittest.mock.patch` mock `requests.get`，测试 API 调用逻辑和错误处理

---

## Phase 6: 补充关键测试

### 6.1 补充 orchestrator 测试

**状态：** 已完成
**文件：** `tests/test_orchestrator.py`
**操作：** 新增：
- `test_run_loop_once`：mock check_all_triggers 返回一个事件后返回 None，验证 run_loop 执行一次后停止
- `test_run_loop_goal_met`：mock check_goal 返回 None，验证循环终止
- `test_save_state_called_in_finally`：验证 orchestrate_cycle 的 finally 块调用了 save_state

### 6.2 补充 state 测试

**状态：** 已完成
**文件：** `tests/test_state.py`
**操作：** 新增：
- `test_remove_worktree_save_false`：验证 _save=False 时不调用 save_state
- `test_record_cycle_updates_last_run_ts`：验证 last_run_ts 被更新

### 6.3 补充 loop_agent 测试

**状态：** 已完成
**文件：** `tests/test_maker_checker.py`
**操作：** 新增：
- `test_run_agent_loop_exception`：mock LLM 抛异常，验证 run_maker/run_checker 返回失败结果而非崩溃

---

## Phase 7: README 英文化

### 7.1 新建 README.en.md

**状态：** 已完成
**文件：** 新建 `README.en.md`
**操作：** 翻译现有 README.md 的核心内容（架构图、Quick Start、命令参考、七阶段流程）

### 7.2 更新 README.md 语言链接

**状态：** 已完成
**文件：** `README.md`
**操作：** 在顶部添加 `[English](README.en.md)` 链接
