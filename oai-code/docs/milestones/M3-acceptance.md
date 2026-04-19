# M3 验收报告

| 项目 | 内容 |
|------|------|
| 里程碑 | oai-code M3 |
| 交付范围 | MCP sse+http / 退出总结 / 多 Agent 协作（s09-s11）/ PyPI 发布准备 |
| 验收日期 | 2026-04 |
| 最终 Commit | `e2e4ef9` |
| 版本 | 0.1.0.dev0 |
| 验收结论 | ✅ **通过** |

---

## 1. 验收依据

- 规格真源：`docs/DESIGN.md` §9 M3、§4.7 MCP、`docs/TOOLS.md` §6（Team 工具）、`docs/CONFIG.md` §3.6 Team / §3.7 MCP
- 设计文档：`docs/milestones/M3.md`（实施溯源）
- 质量基线：`DESIGN.md` §10 测试矩阵 + 人工构建验证

---

## 2. 范围确认

### 2.1 约定交付（7 项）

| 条目 | 规格出处 | 交付状态 |
|------|---------|---------|
| MCP sse 传输 | DESIGN §4.7 M3 | ✅ |
| MCP http 传输 | DESIGN §4.7 M3 | ✅ |
| 退出总结 `/quit --summary` | DESIGN §9 M3 | ✅ |
| s09 消息总线 + Spawn | s09 文档 | ✅ |
| s10 协议（Shutdown / PlanApproval） | s10 文档 | ✅ |
| s11 自治 idle + ClaimTask + 身份重注入 | s11 文档 | ✅ |
| PyPI 发布准备（classifiers/LICENSE/构建通过） | DESIGN §9 M3 | ✅（未真实发布） |

### 2.2 范围外（明确未做）

- 真实 PyPI 推送 —— 需维护者手动走 `docs/PUBLISH.md` 清单
- Worktree 隔离（s12）—— 推到 M4
- MCP sse/http 真实 server 的集成测试 —— 推到 M4
- 队友 loop 的录制回归测试 —— 推到 M4

---

## 3. 功能验收矩阵

### 3.1 M3-1 MCP sse+http

| # | 需求 | 期望行为 | 自动化测试 | 手动验证 | 结果 |
|---|------|---------|-----------|---------|------|
| M3-1.1 | 接受 stdio/sse/http 三种 type | Pydantic 不报错 | `test_accepted_transports` | — | ✅ |
| M3-1.2 | sse 缺 url 直接拒绝 | RuntimeError("missing 'url'") | `test_connect_sse_missing_url_raises` | — | ✅ |
| M3-1.3 | http 缺 url 直接拒绝 | 同上 | `test_connect_http_missing_url_raises` | — | ✅ |
| M3-1.4 | headers 支持 `_env` 规则 | 与 env 字段相同行为 | M2 已测 `_resolve_env` | — | ✅ |
| M3-1.5 | 未知 type 跳过而非崩 | 打印 skipped | 代码分支保证 | — | ✅ |

### 3.2 M3-2 退出总结写 `.oaic/MEMORY.md`

| # | 需求 | 期望行为 | 自动化测试 | 手动验证 | 结果 |
|---|------|---------|-----------|---------|------|
| M3-2.1 | 空对话返回提示 | "no conversation" | `test_empty_conversation` | — | ✅ |
| M3-2.2 | 只有 system 消息也按空对话处理 | 同上 | `test_system_only_returns_no_convo` | — | ✅ |
| M3-2.3 | 首次写入带 header | "# Auto-generated memory" | `test_appends_with_header_on_first_write` | — | ✅ |
| M3-2.4 | 多次写入不重复 header | count == 1 | `test_second_append_no_duplicate_header` | — | ✅ |
| M3-2.5 | 模型返回 `(nothing new)` 跳过写 | 文件无 Auto summary | `test_nothing_new_skipped` | — | ✅ |
| M3-2.6 | LLM 异常被捕获 | Error: summarize failed | `test_llm_error_surfaced` | — | ✅ |
| M3-2.7 | `/exit-summary` / `/quit --summary` REPL 触发 | 调用 summarize_to_memory | — | REPL 手动输入 | ✅ |

### 3.3 M3-3 消息总线 + TeammateManager

| # | 需求 | 期望行为 | 自动化测试 | 结果 |
|---|------|---------|-----------|------|
| M3-3.1 | send + read 成功 | 收件人拿到消息 | `test_send_and_read` | ✅ |
| M3-3.2 | drain-on-read | 第二次 read 为空 | `test_drain_on_read` | ✅ |
| M3-3.3 | 未写过的 inbox 返回 `[]` | 不抛异常 | `test_empty_inbox_returns_list` | ✅ |
| M3-3.4 | 禁止 send 给自己 | Error: cannot send to self | `test_reject_self_send` | ✅ |
| M3-3.5 | 非法 msg_type 拒绝 | Error: invalid msg_type | `test_reject_invalid_msg_type` | ✅ |
| M3-3.6 | 非法 teammate name 拒绝 | Error: invalid name | `test_reject_invalid_name` | ✅ |
| M3-3.7 | broadcast 跳过 sender | count == N-1 | `test_broadcast_skips_sender` | ✅ |
| M3-3.8 | extra fields 保留（如 request_id） | 读到的消息带 request_id | `test_extra_fields_preserved` | ✅ |
| M3-3.9 | register 幂等 | 同名覆盖 role | `test_register_idempotent_updates_role` | ✅ |
| M3-3.10 | set_status 非法值拒绝 | Error: invalid status | `test_set_status` | ✅ |
| M3-3.11 | remove 不存在队友 | Error: unknown | `test_remove_unknown` | ✅ |

### 3.4 M3-4 多 Agent 工具

| # | 需求 | 期望行为 | 自动化测试 | 结果 |
|---|------|---------|-----------|------|
| M3-4.1 | 5 个 team 工具注册进 registry | SpawnTeammate/SendMessage/Broadcast/ReadInbox/ListTeammates | `test_team_tools_registered` | ✅ |
| M3-4.2 | SendMessage 使用 lead 为 sender | 收件人看到 from=lead | `test_send_message_tool_uses_lead_as_sender` | ✅ |
| M3-4.3 | Broadcast 跳过 lead | count 正确 | `test_broadcast_tool` | ✅ |
| M3-4.4 | 队友工具白名单 read_only=True | 无 Write/Edit | `test_teammate_registry_whitelist` | ✅ |
| M3-4.5 | 队友工具白名单 full 模式 | 有 Write/Edit | `test_teammate_registry_full_mode` | ✅ |
| M3-4.6 | 队友 SendMessage 使用自己名 | from=alice | `test_teammate_send_message_uses_self_name` | ✅ |

### 3.5 M3-5 团队协议

| # | 需求 | 期望行为 | 自动化测试 | 结果 |
|---|------|---------|-----------|------|
| M3-5.1 | send_shutdown 产生 req_id + pending | 返回 sent/pending | `test_send_shutdown_request` | ✅ |
| M3-5.2 | shutdown_response approve | 状态 approved | `test_shutdown_response_approve` | ✅ |
| M3-5.3 | 未知 req_id 拒绝 | Error: unknown | `test_shutdown_response_unknown_id` | ✅ |
| M3-5.4 | 不允许对自己 shutdown | Error | `test_send_shutdown_to_self_rejected` | ✅ |
| M3-5.5 | submit_plan 产生 req_id | lead inbox 收到 request | `test_submit_plan` | ✅ |
| M3-5.6 | review_plan approve 发 response | alice 收到 approve=True | `test_review_plan_approve` | ✅ |
| M3-5.7 | review_plan reject 发 response | alice 收到 approve=False + feedback | `test_review_plan_reject` | ✅ |
| M3-5.8 | review 未知 plan 拒绝 | Error | `test_review_unknown_plan` | ✅ |
| M3-5.9 | ShutdownRequest/PlanApproval 注册 | 存在 registry | `test_shutdown_request_tool_registered` | ✅ |
| M3-5.10 | PlanApproval 工具 e2e | 调 handler 成功 | `test_plan_approval_tool_end_to_end` | ✅ |

### 3.6 M3-6 自治 + 身份重注入

| # | 需求 | 期望行为 | 自动化测试 | 结果 |
|---|------|---------|-----------|------|
| M3-6.1 | ClaimTask 注册给队友 | sub registry 有 | `test_claim_registers_tool` | ✅ |
| M3-6.2 | 认领未被占用 task | owner=alice, status=in_progress | `test_claim_unclaimed_task` | ✅ |
| M3-6.3 | 认领别人的 task 拒绝 | Error: already owned | `test_claim_already_owned` | ✅ |
| M3-6.4 | 同人重复认领幂等 | 无 Error | `test_claim_reclaim_by_same_owner_ok` | ✅ |
| M3-6.5 | 认领被阻塞 task 拒绝 | Error: blocked by | `test_claim_blocked` | ✅ |
| M3-6.6 | 认领不存在 task 拒绝 | Error: not found | `test_claim_unknown_task` | ✅ |
| M3-6.7 | 自动扫描挑第一个可用 | 只认 #1，#2 未动 | `test_try_autoclaim_picks_first` | ✅ |
| M3-6.8 | 跳过已 owner 的 | 不 claim | `test_try_autoclaim_skips_owned` | ✅ |
| M3-6.9 | 跳过 blockedBy 的 | 不 claim | `test_try_autoclaim_skips_blocked` | ✅ |
| M3-6.10 | 空看板返回 False | — | `test_try_autoclaim_empty_board` | ✅ |
| M3-6.11 | messages 短时注入 identity | 尾部多一条 `<identity>` | `test_reinject_when_short` | ✅ |
| M3-6.12 | messages 长时不注入 | 无变化 | `test_no_reinject_when_long` | ✅ |

### 3.7 M3-7 PyPI 发布准备

| # | 需求 | 期望行为 | 自动化 / 手动 | 结果 |
|---|------|---------|-------------|------|
| M3-7.1 | pyproject.toml 含 classifiers | 12 条 PyPI 标签 | 手动读 | ✅ |
| M3-7.2 | 含 project.urls | Homepage/Docs/Issues | 手动读 | ✅ |
| M3-7.3 | LICENSE 文件存在 | MIT 正文 | `ls LICENSE` | ✅ |
| M3-7.4 | `uv build` 能构建 | 产出 .whl + .tar.gz | 手动 `uv build` | ✅ |
| M3-7.5 | wheel 含所有模块 | oai_code/** 在 wheel 内 | `unzip -l dist/*.whl` | ✅ |
| M3-7.6 | 测试未回归 | 156 passed | `uv run pytest` | ✅ |
| M3-7.7 | 发布指南文档 | `docs/PUBLISH.md` 完备 | 手动读 | ✅ |

---

## 4. 质量验收

### 4.1 测试套件

```bash
cd oai-code
uv sync --extra dev
uv run pytest -q
```

**结果**：`156 passed in 1.68s`

**分布**：M0 27 + M1 46 + M2 30 + **M3 53** = 156

### 4.2 回归验收

| 阶段 | 测试数 | 状态 |
|------|-------|-----|
| M0 完成 | 27 | ✅ 保持 |
| M1 完成 | 73 | ✅ 保持 |
| M2 完成 | 103 | ✅ 保持 |
| **M3 完成** | **156** | ✅ **新增 53，0 回归** |

### 4.3 构建验证

```
$ uv build
Building source distribution...
Building wheel from source distribution...
Successfully built dist/oai_code-0.1.0.dev0.tar.gz
Successfully built dist/oai_code-0.1.0.dev0-py3-none-any.whl
```

wheel 内容已确认包含所有 `oai_code/**` 模块及子模块（team/ mcp/ memory/ session/ context/ ...）。

### 4.4 代码体积

```
src/oai_code/mcp/client.py          +40 行（sse/http 分支）
src/oai_code/memory/summarize.py    ≈ 100 行
src/oai_code/team/bus.py            ≈ 110 行
src/oai_code/team/manager.py        ≈ 120 行
src/oai_code/team/loop.py           ≈ 300 行
src/oai_code/team/tools.py          ≈ 180 行
src/oai_code/team/protocol.py       ≈ 130 行
src/oai_code/ui/repl.py             +~60 行（/team /inbox /exit-summary）
src/oai_code/cli.py                 +~40 行（team/mcp 接线）
pyproject.toml + LICENSE            +70 行
docs/PUBLISH.md                     ≈ 60 行
-----------------------------------------------
M3 净增 ≈ 1200 行实现 + 53 条测试
```

---

## 5. 端到端冒烟

```bash
cd oai-code

# 1. 核心测试
uv sync --extra dev
uv run pytest -q                                  # 156 passed

# 2. MCP 多传输语义（启动时 enabled=false 的默认下不崩）
uv run oaic --list-sessions                       # 可列出 session,不触发 MCP

# 3. 退出总结（启动 REPL 聊几句后）
# oaic > 我喜欢中文回答
# oaic > 写代码前先读文件
# oaic > /exit-summary
# 应看到: ✓ Appended N lines to .oaic/MEMORY.md

cat .oaic/MEMORY.md                               # 查看追加的内容

# 4. 多 Agent（需要在 .oaic/settings.json 加 "team": {"enabled": true}）
# cat > .oaic/settings.json << 'EOF'
# {"team": {"enabled": true}}
# EOF
# uv run oaic
# oaic > 用 SpawnTeammate 起一个叫 alice 的 backend 队友,让她看下 README
# oaic > /team
# oaic > /inbox

# 5. 本地构建 wheel
rm -rf dist/
uv build
ls dist/    # oai_code-*.whl / .tar.gz
```

---

## 6. 风险与已知限制（供 M4 参考）

| 风险/限制 | 影响 | 缓解/跟进 |
|----------|------|---------|
| MCP sse/http 无真实 E2E | 升级 SDK 后可能静默坏 | M4 起 mock server |
| 队友 loop 无录制回归 | 改 loop 内部逻辑易回归 | M4 用 respx 录制 |
| ClaimTask 竞态窗口 | 极低概率双 claim | M4 加 fcntl lock |
| 队友 auto-compact 未接 | 长对话队友会爆 context | M4 必须补 |
| 退出总结无 token 预算 | 极端情况下费用不可控 | M4 加上限 |
| PyPI 未实际发布 | 需维护者操作 | 按 `docs/PUBLISH.md` 走 |
| Worktree 隔离未做 | 不能并行不同分支的 agent | M4 |

---

## 7. 验收结论

| 维度 | 要求 | 结果 |
|------|-----|------|
| **功能完整性** | 7 项 M3 条目全部交付 | ✅ |
| **规格一致性** | 对齐 DESIGN / TOOLS / CONFIG 三份真源 | ✅ |
| **测试覆盖** | 新增 ≥ 30 条自动化测试 | ✅ 新增 53 条 |
| **回归保障** | M0/M1/M2 所有测试不退化 | ✅ 103/103 保持 |
| **可复现性** | `uv sync && uv run pytest` 一键跑过 | ✅ 156/156 |
| **构建** | `uv build` 产出 wheel | ✅ |
| **文档** | 溯源 + 验收 + 发布指南 | ✅ |
| **安全** | session 脱敏/safe_path/MCP env fail-fast 全保持 | ✅ |

**最终结论**：**✅ M3 验收通过，项目主线功能交付完毕，可进入 M4 质量提升或直接考虑发布 PyPI**。

---

## 8. 签署

| 角色 | 姓名 | 日期 |
|------|-----|------|
| 开发 | zhouyunfei | 2026-04 |
| 验收 | _待填写_ | _待填写_ |

> 如验收人在上述冒烟脚本中发现任一步骤失败，请在 Issue 区开 `m3-acceptance-failure` 标签记录。
