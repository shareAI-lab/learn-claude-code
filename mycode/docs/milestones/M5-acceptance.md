# M5 验收报告

| 项目 | 内容 |
|------|------|
| 里程碑 | mycode M5 |
| 交付范围 | Worktree 隔离 / MCP 真实 E2E / 队友 loop 录制回归 / UI 加固 / PyPI 发布准备 |
| 验收日期 | 2026-04 |
| 最终 Commit | `475a495` |
| **版本** | **0.1.0** |
| 验收结论 | ✅ **通过** |

---

## 1. 验收依据

- 规格真源：`docs/DESIGN.md` §9 M5、`docs/TOOLS.md`、`docs/CONFIG.md`
- 设计文档：`docs/milestones/M5.md`（实施溯源）
- 对比参考：`references/Kode-Agent-main`

---

## 2. 范围确认

### 2.1 约定交付（5 项）

| 条目 | 类别 | 交付状态 |
|------|------|---------|
| Worktree 隔离 | 新能力 | ✅ |
| MCP 真实 E2E | 质量 | ✅ |
| 队友 loop 录制回归 | 质量 | ✅ |
| UI 加固 | 体验 | ✅ |
| PyPI 发布准备（0.1.0） | 里程碑 | ✅（未推送） |

### 2.2 范围外

- 真正执行 `uv publish` —— 需要维护者用本人 Token
- LSP / WebSearch / Jupyter 工具
- Ink 式 React TUI

---

## 3. 功能验收矩阵

### 3.1 M5-1 Worktree 隔离

| # | 需求 | 期望 | 自动化测试 | 结果 |
|---|------|------|-----------|------|
| M5-1.1 | 非会话态 status 显示 "Not in" | 正确 | `test_status_without_session` | ✅ |
| M5-1.2 | EnterWorktree 创建目录 + 切 workspace | 目录存在、workspace_root 变 | `test_enter_creates_worktree_and_changes_root` | ✅ |
| M5-1.3 | 重复 Enter 拒绝 | Error: already in | `test_enter_twice_rejected` | ✅ |
| M5-1.4 | 非法 worktree 名拒绝 | Error: invalid name | `test_invalid_name_rejected` | ✅ |
| M5-1.5 | 非 git 仓库拒绝 | Error: not inside a git repo | `test_non_git_repo_rejected` | ✅ |
| M5-1.6 | Exit keep 保留目录 + 恢复 workspace | dir 仍在、root 恢复 | `test_exit_keep_preserves_dir` | ✅ |
| M5-1.7 | Exit remove 清洁 worktree | 目录消失 | `test_exit_remove_clean_worktree` | ✅ |
| M5-1.8 | Exit remove 脏 worktree 拒绝 | Error: uncommitted | `test_exit_remove_rejects_dirty` | ✅ |
| M5-1.9 | Exit remove with discard_changes | 强制删除 | `test_exit_remove_with_discard` | ✅ |
| M5-1.10 | 未 Enter 就 Exit 拒绝 | Error | `test_exit_without_enter` | ✅ |
| M5-1.11 | 非法 action 拒绝 | Error | `test_exit_invalid_action` | ✅ |
| M5-1.12 | 三个工具已注册 | registry 有 | `test_tools_registered` | ✅ |

### 3.2 M5-2 MCP 真实 E2E

| # | 需求 | 期望 | 自动化测试 | 结果 |
|---|------|------|-----------|------|
| M5-2.1 | stdio 子进程连接 + list_tools | echo / add 都出现 | `test_server_connects_and_lists_tools` | ✅ |
| M5-2.2 | call_tool 原样返回文本 | "hello world" 出现 | `test_call_echo_tool` | ✅ |
| M5-2.3 | call_tool 支持结构化参数 | 3+4=7 | `test_call_add_tool` | ✅ |
| M5-2.4 | 未知工具返回 Error | Error / not found | `test_call_unknown_tool_on_existing_server` | ✅ |
| M5-2.5 | register_into 工具可通过 registry 调用 | mcp__stub__echo 跑通 | `test_register_into_registry` | ✅ |

### 3.3 M5-3 队友 loop 录制回归

| # | 需求 | 期望 | 自动化测试 | 结果 |
|---|------|------|-----------|------|
| M5-3.1 | 完整 WORK → IDLE → SHUTDOWN 生命周期 | 线程自然退出,status=shutdown | `test_teammate_completes_work_then_idles_then_shuts_down` | ✅ |
| M5-3.2 | IDLE 中收到消息唤醒 | 状态 idle → 又执行一轮 | `test_teammate_wakes_from_idle_on_inbox` | ✅ |
| M5-3.3 | shutdown_request 立即终止 | 线程退出 | `test_teammate_shutdown_request_terminates_immediately` | ✅ |
| M5-3.4 | autonomous=True 自动认领任务 | owner=claire,status=in_progress | `test_teammate_autoclaim_task` | ✅ |

### 3.4 M5-4 UI 加固

| # | 需求 | 期望 | 自动化测试 | 结果 |
|---|------|------|-----------|------|
| M5-4.1 | TodoWrite pending 图标 | `○` 出现 | `test_render_todo_result_pending` | ✅ |
| M5-4.2 | TodoWrite in_progress 图标 | `●` 出现 | `test_render_todo_result_in_progress` | ✅ |
| M5-4.3 | TodoWrite completed 图标 | `✓` 出现 | `test_render_todo_result_completed` | ✅ |
| M5-4.4 | 三状态混合正确渲染 | 三图标 + 进度统计 | `test_render_todo_mixed` | ✅ |
| M5-4.5 | 空输入不崩 | 不抛异常 | `test_render_todo_empty` | ✅ |
| M5-4.6 | 工具调用成功显示 ✓ + 耗时 | 有 ✓ 和 ms/s | `test_on_tool_result_shows_timing_and_icon` | ✅ |
| M5-4.7 | 工具调用失败显示 ✗ | 有 ✗ 和 Error 前缀 | `test_on_tool_result_error_icon` | ✅ |
| M5-4.8 | TodoWrite 结果自动走富渲染 | `○/✓` 而非 `[ ]/[x]` | `test_on_tool_result_todowrite_uses_rich_icons` | ✅ |

### 3.5 M5-5 PyPI 发布准备

| # | 需求 | 期望 | 验证方式 | 结果 |
|---|------|------|---------|------|
| M5-5.1 | 包名 `mycode` 可用 | PyPI 404 | `httpx.get pypi/pypi/mycode/json` | ✅ |
| M5-5.2 | 版本号 0.1.0 | pyproject + `__init__.py` 一致 | `mycode --version` | ✅ |
| M5-5.3 | CHANGELOG.md 列出 M0-M5 | 可读 | 人工读 | ✅ |
| M5-5.4 | README 英文摘要 | 顶部 English summary 段 | 人工读 | ✅ |
| M5-5.5 | `uv build` 产出 wheel | 0.1.0 版本 | `ls dist/` | ✅ |
| M5-5.6 | wheel 含 entry_points | mycode → mycode.cli:main | `unzip -p *.whl entry_points.txt` | ✅ |
| M5-5.7 | 测试未回归 | 241 passed | `uv run pytest -q` | ✅ |
| M5-5.8 | PUBLISH.md 勾选完成项 | checklist 多数已 [x] | 人工读 | ✅ |

---

## 4. 质量验收

### 4.1 测试套件

```bash
cd mycode
uv sync --extra dev
uv run pytest -q
```

**结果**：`241 passed in 10.42s`

**分布**：M0 27 + M1 46 + M2 30 + M3 53 + M4 56 + **M5 29** = 241

### 4.2 回归验收

| 阶段 | 测试数 | 状态 |
|------|-------|-----|
| M0 完成 | 27 | ✅ 保持 |
| M1 完成 | 73 | ✅ 保持 |
| M2 完成 | 103 | ✅ 保持 |
| M3 完成 | 156 | ✅ 保持 |
| M4 完成 | 212 | ✅ 保持 |
| **M5 完成** | **241** | ✅ **新增 29，0 回归** |

### 4.3 代码体积（本期）

```
src/mycode/tools/worktree.py     ≈ 230 行
src/mycode/config/models.py      +10 行 (PrivateAttr)
src/mycode/ui/repl.py            +60 行 (耗时 + Todo 富渲染)
src/mycode/cli.py                +20 行 (worktree 集成)
tests/test_worktree.py             ≈ 170 行
tests/fixtures/stub_mcp_server.py  ≈ 25 行
tests/test_mcp_e2e.py              ≈ 90 行
tests/test_teammate_loop_e2e.py    ≈ 210 行
tests/test_repl_ui.py              ≈ 110 行
CHANGELOG.md                       ≈ 70 行
-----------------------------------------------
M5 净增 ≈ 320 行实现 + 605 行测试 / fixture / changelog
```

### 4.4 质量 checklist

- [x] 新工具（Worktree）错误串全部以 `Error:` 前缀
- [x] Worktree 不调 `os.chdir`（线程安全）
- [x] MCP E2E 用真 subprocess，非 mock
- [x] 队友 loop E2E 用 respx mock 真 HTTP 层，运行真线程
- [x] UI 增强与流式 text delta 兼容（不用 Live）
- [x] 版本号两处（pyproject + __init__）一致
- [x] `uv build` 产出 wheel、entry_points 存在
- [x] 无新依赖
- [x] 未破坏 M0-M4 任何测试

---

## 5. 端到端冒烟

```bash
cd mycode
uv sync --extra dev
uv run pytest -q                                  # 241 passed

# 1. 版本号正确
uv run mycode --version                             # mycode 0.1.0

# 2. Worktree
uv run mycode
# mycode > 用 EnterWorktree 建叫 feature-x 的 worktree
# mycode > /tools | head            # 能看到 EnterWorktree/ExitWorktree
# mycode > WorktreeStatus           # 显示当前在 worktree
# mycode > ExitWorktree action=keep  # 退出但保留分支

# 3. UI 加固
# 任何工具调用后行尾都能看到 "✓ Bash · 45ms" 样式
# TodoWrite 返回以 ●/○/✓ 而非 [ ]/[>]/[x]

# 4. 构建 + 安装自测
rm -rf dist/
uv build                                          # 0.1.0 wheel + sdist
# (可选)用一个干净 Python venv 装 wheel,跑 mycode --help

# 5. PyPI 占用查
uv run python -c "
import httpx
r = httpx.get('https://pypi.org/pypi/mycode/json', timeout=10)
print('AVAILABLE' if r.status_code == 404 else f'OCCUPIED v{r.json()[\"info\"][\"version\"]}')
"
```

---

## 6. 风险与已知限制

| 风险/限制 | 影响 | 跟进 |
|----------|------|-----|
| Worktree commit 未合并检查未做 | 极端场景丢 commit | M6 或用户反馈 |
| Worktree + Session 交互未验证 | resume 跨 worktree 行为不明 | M6 |
| MCP sse/http E2E 缺失 | 只测 stdio | M6 |
| 队友多轮 tool_calls 未完整录制 | 复杂对话场景未覆盖 | M6 |
| PyPI 未真实推送 | 需维护者 Token | 按 PUBLISH.md 操作 |

---

## 7. 验收结论

| 维度 | 要求 | 结果 |
|------|-----|------|
| **功能完整性** | 5 项 M5 条目全部交付 | ✅ |
| **规格一致性** | 与 DESIGN/TOOLS/CONFIG 对齐 | ✅ |
| **测试覆盖** | 新增 ≥ 25 条 | ✅ 新增 29 条 |
| **回归保障** | M0-M4 全保持 | ✅ 212/212 |
| **可复现性** | 一键跑过 | ✅ 241/241 |
| **构建** | `uv build` 产出 0.1.0 wheel | ✅ |
| **文档** | 溯源 + 验收 + CHANGELOG + PUBLISH | ✅ 全套齐 |
| **版本转正** | 0.1.0.dev0 → 0.1.0 | ✅ |
| **安全** | 脱敏 / Worktree 无 chdir / MCP env fail-fast 全保持 | ✅ |

**最终结论**：**✅ M5 验收通过。mycode 0.1.0 已具备对外发布条件，待维护者按 `docs/PUBLISH.md` 推送 PyPI**。

---

## 8. 签署

| 角色 | 姓名 | 日期 |
|------|-----|------|
| 开发 | zhouyunfei | 2026-04 |
| 验收 | _待填写_ | _待填写_ |

> 如验收人在上述冒烟脚本中发现任一步骤失败，请在 Issue 区开 `m5-acceptance-failure` 标签记录。
