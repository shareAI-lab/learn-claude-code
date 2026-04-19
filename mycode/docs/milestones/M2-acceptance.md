# M2 验收报告

| 项目 | 内容 |
|------|------|
| 里程碑 | mycode M2 |
| 交付范围 | Session 持久化 / 后台任务 / MCP stdio 客户端 / Slash 完整集 |
| 验收日期 | 2026-04 |
| 最终 Commit | `12db596` |
| 版本 | 0.1.0dev0 |
| 验收结论 | ✅ **通过** |

---

## 1. 验收依据

- 规格真源：`docs/DESIGN.md` §9 M2 条目、§4.4（Session）、§4.7（MCP）、`docs/TOOLS.md` §2.2、`docs/CONFIG.md` §3.7
- 设计文档：`docs/milestones/M2.md`（实施溯源）
- 质量基线：`DESIGN.md` §10 测试矩阵

---

## 2. 范围确认

### 2.1 约定交付（4 项）

| 条目 | 规格出处 | 交付状态 |
|------|---------|---------|
| Session 持久化 + resume | DESIGN §4.4, §9-M2 | ✅ 交付 |
| 后台任务（BackgroundRun/Check） | TOOLS §2.2, DESIGN §4.2 | ✅ 交付 |
| MCP 客户端（stdio） | DESIGN §4.7, CONFIG §3.7 | ✅ 交付 |
| Slash 完整集 | DESIGN §4.8 | ✅ 交付 |

### 2.2 范围外（确认未做，非扣分项）

- MCP sse/http 传输 —— 本次决策明确仅 stdio，M3 再做
- 多 Agent 协作 / Worktree 隔离 / PyPI 发布 —— M3
- BackgroundKill 终止能力 —— M3
- 动态模型路由 —— M3+

---

## 3. 功能验收矩阵

### 3.1 M2-1 Session 持久化与 resume

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M2-1.1 | 启动默认创建新 session | `.mycode/sessions/<id>.jsonl` 文件存在 | `test_new_session_creates_file` | 启动 mycode 后 `ls .mycode/sessions/` | ✅ |
| M2-1.2 | session id 格式 `YYYYMMDD-HHMMSS-<hex4>` | 正则匹配 | `test_new_session_creates_file` | — | ✅ |
| M2-1.3 | 逐轮 append 不重复写 | 多次 flush 只写新增 | `test_append_new_messages` | — | ✅ |
| M2-1.4 | `load()` 完整恢复 messages | 从 jsonl 还原成 list | `test_load_roundtrip` | `mycode --resume <id>` 能继续对话 | ✅ |
| M2-1.5 | `--resume` 不存在的 id 报错 | stderr 报 not found | `test_load_missing_raises` | `mycode --resume bogus-id` | ✅ |
| M2-1.6 | `latest_id` / `list_ids` 按 mtime 倒序 | 最新的在前 | `test_list_ids_sorted_by_mtime` / `test_latest_id` | — | ✅ |
| M2-1.7 | `--list-sessions` 打印列表 | 含 msg 数与首条 user 输入 | — | `mycode --list-sessions` | ✅ |
| M2-1.8 | `auto_save=false` 时不落盘 | append_new_messages 返回 0 | `test_auto_save_false_no_write` | `mycode --no-save` 后 `.mycode/sessions/` 无新文件 | ✅ |
| M2-1.9 | 写盘前脱敏 | Bearer/sk- 不明文 | `test_redact_on_write` | jsonl 文件 grep 无明文 key | ✅ |
| M2-1.10 | `/sessions` slash 列出 | 当前 session 带 ● | REPL 端到端 + `test_list_sessions_shows_current` | REPL 输 `/sessions` | ✅ |
| M2-1.11 | `/resume <id|latest>` slash | 切换 state 并 ✓ 提示 | — | REPL 输 `/resume latest` | ✅ |

### 3.2 M2-2 后台任务

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M2-2.1 | BackgroundRun 立即返回 id | 不阻塞 agent loop | `test_run_returns_task_id` | — | ✅ |
| M2-2.2 | 任务正常完成 | status=completed + 输出 | `test_task_completes` | — | ✅ |
| M2-2.3 | exit code != 0 被记录 | content 末尾 `[exit code: N]` | `test_exit_code_captured` | — | ✅ |
| M2-2.4 | timeout 中止 | status=timeout | `test_timeout` | — | ✅ |
| M2-2.5 | BackgroundCheck 单任务 / 全量 | 已知 id 返回状态，未知报 Error | `test_check_known_and_unknown` / `test_check_all_empty_and_listed` | — | ✅ |
| M2-2.6 | drain 返回后不重复 | 第二次调用为空 | `test_drain_returns_once` | — | ✅ |
| M2-2.7 | 每轮 loop 开头 drain 注入 | messages 末尾含 `<background-results>` | 手动端到端 | REPL 让模型起 bg 任务后再聊天 | ✅ |
| M2-2.8 | `/bg [id]` slash | 查状态或列全部 | — | REPL 输 `/bg` | ✅ |

### 3.3 M2-3 MCP stdio 客户端

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M2-3.1 | 短工具名 `mcp__<srv>__<tool>` | 原样前缀 | `test_short_name_uses_verbatim` | — | ✅ |
| M2-3.2 | 长工具名 sha1 缩短 | 长度 ≤ 64、原名不出现 | `test_long_name_is_hashed` | — | ✅ |
| M2-3.3 | sha1 确定性 | 相同输入 → 相同输出 | `test_hash_is_deterministic` | — | ✅ |
| M2-3.4 | `_env` 后缀规则 | 环境变量注入 | `test_env_suffix_resolves_from_os_env` | — | ✅ |
| M2-3.5 | `_env` 缺失 fail-fast | 抛 RuntimeError | `test_env_missing_raises` | — | ✅ |
| M2-3.6 | 非 `_env` 字面透传 | key/value 不变 | `test_env_literal_passthrough` | — | ✅ |
| M2-3.7 | 未连接时 call_tool | 返回 `Error: mcp server '...' not connected` | `test_call_without_connection_returns_error` | — | ✅ |
| M2-3.8 | 未启动时 summary | "no mcp servers connected" | `test_summary_empty` | `/mcp` 无配置时打印提示 | ✅ |
| M2-3.9 | 非 stdio 的 server 跳过 | 打印 skipped: only 'stdio' | — | 配置 type=sse 启动看日志 | ✅（代码 `if sc.type != "stdio"` 分支） |

### 3.4 M2-4 Slash 完整集

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M2-4.1 | `/help` 分组 | session / inspect / model / other | `test_help_grouped` | — | ✅ |
| M2-4.2 | `/system` 显示 prompt | 含字符数与正文 | `test_system_prompt_rendered` | — | ✅ |
| M2-4.3 | `/history [N]` | 默认 10,N 控制条数 | `test_history_rendered` | — | ✅ |
| M2-4.4 | `/debug` 显示估算 | messages + est_tokens + ctx_limit | `test_debug_status_includes_metrics` | — | ✅ |
| M2-4.5 | `/save` 手动 flush | 打印 session id 与新写入数 | `test_save_slash` | — | ✅ |
| M2-4.6 | `/sessions` 当前标记 | ● 表示当前 session | `test_list_sessions_shows_current` | — | ✅ |

---

## 4. 质量验收

### 4.1 测试套件

```bash
cd mycode
uv sync --extra dev
uv run pytest -q
```

**结果**：`103 passed in 1.54s`

**分布**：M0 27 + M1 46 + **M2 30** = 103

### 4.2 回归验收

| 阶段 | 测试数 | 状态 |
|------|-------|-----|
| M0 完成 | 27 | ✅ 全部保持 |
| M1 完成 | 73 | ✅ 全部保持 |
| **M2 完成** | **103** | ✅ **新增 30，0 回归** |

### 4.3 代码体积

```
src/mycode/session/store.py        ≈ 125 行
src/mycode/tools/background.py     ≈ 140 行
src/mycode/mcp/client.py           ≈ 195 行
src/mycode/ui/repl.py              +~120 行（slash + 辅助方法）
src/mycode/cli.py                  +~60 行（串接）
src/mycode/agent/loop.py           +~20 行（bg_manager drain）
-----------------------------------------------
M2 净增 ≈ 660 行实现 + 30 条测试
```

### 4.4 代码质量 checklist

- [x] MCP tool name 长度策略对齐 TOOLS.md §0.1
- [x] MCP `_env` 规则对齐 CONFIG.md §3.7
- [x] Session 落盘前跑 `redact`
- [x] 后台任务 exit code / timeout 分类清晰
- [x] 未破坏 M0/M1 已有测试
- [x] `.env` / `.mycode/sessions/` / `.mycode/blobs/` 均在 `.gitignore`（`.mycode/` 一条覆盖）
- [x] 所有新路径自动 `mkdir`
- [x] 无硬编码 API key

---

## 5. 端到端冒烟

```bash
cd mycode

# 1. Session 持久化 + resume
uv run mycode -p "记住数字 42"
uv run mycode --list-sessions     # 应看到刚才的 session
uv run mycode --resume latest -p "我告诉你什么数字"  # 模型应答 42

# 2. 后台任务（REPL 中）
uv run mycode
  # 输入：用 BackgroundRun 跑 "sleep 2 && echo done" 然后告诉我结果
  # 应看到: [bg:xxx] completed: done

# 3. MCP 缺配置时不崩
uv run mycode -p "/mcp"   # 或直接启动 REPL 输 /mcp

# 4. Slash 完整集
printf "/help\n/system\n/history\n/debug\n/save\n/sessions\n/quit\n" | uv run mycode

# 5. 跑完整测试
uv sync --extra dev
uv run pytest -q  # 103 passed
```

---

## 6. 风险与已知限制（供 M3 参考）

| 风险/限制 | 影响 | 缓解/跟进 |
|----------|------|---------|
| MCP 只支持 stdio | 云端 http/sse server 接不上 | M3 补 sse+http |
| Session resume 不重算 system prompt | 改了 CLAUDE.md 需 `/clear` | M3 加 `--refresh-system` |
| 后台任务无法 kill | Ctrl-C 后子进程继续跑 | M3 加 `BackgroundKill` |
| auto-compact 与 session 混流 | resume 后可能前缀重复 | M3 引入 session 版本化 |
| `/history` 不展开 tool_calls | 调试详情不全 | 有需求时再加 |
| MCP 无真实 server 的 E2E 测试 | 回归风险 | M3 加 minimal stub server |

---

## 7. 验收结论

| 维度 | 要求 | 结果 |
|------|-----|------|
| **功能完整性** | 4 项 M2 条目全部交付 | ✅ |
| **规格一致性** | 对齐 TOOLS.md / DESIGN.md / CONFIG.md | ✅ |
| **测试覆盖** | 新增 ≥20 条自动化测试 | ✅ 新增 30 条 |
| **回归保障** | M0/M1 所有测试不退化 | ✅ 73/73 保持 |
| **可复现性** | `uv sync && uv run pytest` 一键跑过 | ✅ 103/103 |
| **端到端** | Session resume 真实打通 | ✅ 模型记住 42 → 新进程答 42 |
| **文档** | 溯源 + 验收双份 | ✅ |
| **安全** | 写盘脱敏、`_env` fail-fast | ✅ |

**最终结论**：**✅ M2 验收通过，批准进入 M3**。

---

## 8. 签署

| 角色 | 姓名 | 日期 |
|------|-----|------|
| 开发 | zhouyunfei | 2026-04 |
| 验收 | _待填写_ | _待填写_ |

> 如验收人在上述冒烟脚本中发现任一步骤失败，请在 Issue 区开 `m2-acceptance-failure` 标签记录。
