# M1 验收报告

| 项目 | 内容 |
|------|------|
| 里程碑 | mycode M1 |
| 交付范围 | 记忆加载 / TodoWrite / 持久化 Tasks / Subagent / Skills / Compact + Roles |
| 验收日期 | 2026-04 |
| 最终 Commit | `76458c2` |
| 版本 | 0.1.0dev0 |
| 验收结论 | ✅ **通过** |

---

## 1. 验收依据

- 规格真源：`docs/DESIGN.md` §9 M1 条目、`docs/TOOLS.md` §3-§5、`docs/CONFIG.md` §3
- 设计文档：`docs/milestones/M1.md`（实施溯源）
- 质量基线：`DESIGN.md` §10 测试矩阵

---

## 2. 范围确认

### 2.1 约定交付（6 项）

| 条目 | 规格出处 | 交付状态 |
|------|---------|---------|
| CLAUDE.md / AGENTS.md / 用户级记忆的完整集成 | DESIGN §4.6 | ✅ 交付 |
| TodoWrite 短期 checklist | TOOLS §3.1 | ✅ 交付 |
| 持久化 Tasks（TaskCreate/Get/Update/List） | TOOLS §3.2 | ✅ 交付 |
| Subagent Task 工具（3 种 subagent_type） | TOOLS §4.1 | ✅ 交付 |
| Skills 按需加载（LoadSkill） | TOOLS §4.2 | ✅ 交付 |
| 上下文压缩（microcompact + auto） + 分角色模型 | DESIGN §4.3, §9-M1 | ✅ 交付 |

### 2.2 范围外（确认未做,非扣分项）

- Session resume / 后台任务 / MCP 客户端 —— DESIGN.md 明确排到 M2
- 多 agent 协作 / Worktree 隔离 —— DESIGN.md 明确排到 M3
- 动态模型路由 —— M1 分角色模型条目已明确排除

---

## 3. 功能验收矩阵

**说明**：每项"检查方法"可由验收人手动复现；"自动化测试"列出对应的 pytest 用例名。

### 3.1 M1-1 Memory 加载

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M1-1.1 | 读取项目根 CLAUDE.md | 进入 system prompt | `test_load_basic` | 在项目根建 `CLAUDE.md`→ 启动 mycode 问 "你记忆里有什么" | ✅ |
| M1-1.2 | 文件不存在不报错 | 静默跳过 | `test_load_missing_returns_none` | 删除 `CLAUDE.md` 启动无异常 | ✅ |
| M1-1.3 | `~/` 展开 | 正确解析到 HOME | `test_home_expand` | 建 `~/.mycode/CLAUDE.md` 启动后可被引用 | ✅ |
| M1-1.4 | 超长文件不爆炸 | 返回占位符 | `test_too_large_returns_truncated_placeholder` | 写一个 >16KiB 的 `CLAUDE.md` | ✅ |
| M1-1.5 | `@file.md` 引用展开 | 嵌套内容被拉入 | `test_reference_expansion` | 主 CLAUDE.md 写 `@shared.md` | ✅ |
| M1-1.6 | 循环引用保护 | 不死循环 | `test_reference_cycle_safe` | a.md→b.md→a.md | ✅ |
| M1-1.7 | `memory_files` 列表按序加载 | 缺失项跳过 | `test_load_all_order_and_skip_missing` | 配置 3 个只有 1 个存在 | ✅ |

### 3.2 M1-2 TodoWrite

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M1-2.1 | 模型可用 TodoWrite 替换整列 | 后一次调用覆盖前一次 | `test_replace_semantics` | 让模型先 TodoWrite 3 条再 2 条,`/todos` 看结果 | ✅ |
| M1-2.2 | 最多 20 条 | 超出报 Error | `test_reject_too_many` | 模型试图写 21 条 | ✅ |
| M1-2.3 | 最多 1 条 in_progress | 多条报 Error | `test_reject_multi_in_progress` | — | ✅ |
| M1-2.4 | 非法 status 被拒 | 报 Error | `test_reject_invalid_status` | — | ✅ |
| M1-2.5 | 空 content 被拒 | 报 Error | `test_reject_empty_content` | — | ✅ |
| M1-2.6 | `/todos` slash 查看 | rich 格式输出 | — | REPL 中输入 `/todos` | ✅ |

### 3.3 M1-3 持久化 Tasks

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M1-3.1 | TaskCreate 落盘 `.mycode/tasks/task_N.json` | 文件存在 | `test_create_and_get` | 让模型建一个任务,`ls .mycode/tasks/` | ✅ |
| M1-3.2 | 空 subject 被拒 | 报 Error | `test_create_reject_empty` | — | ✅ |
| M1-3.3 | TaskUpdate 状态流转 | 非法状态报 Error | `test_update_invalid_status` | — | ✅ |
| M1-3.4 | 完成任务级联 unblock | 他任务 `blockedBy` 自动移除 | `test_cascade_unblock` | 建 #1/#2,#2 blockedby[1],#1 done → #2 blockedBy=[] | ✅ |
| M1-3.5 | 删除任务物理移除 JSON | 文件从磁盘消失 | `test_delete_removes_file` | — | ✅ |
| M1-3.6 | 不存在 ID 报 Error | 返回 "not found" | `test_get_missing` | — | ✅ |
| M1-3.7 | add/remove blocked_by 原子操作 | 去重/增量 | `test_add_remove_blocked_by` | — | ✅ |
| M1-3.8 | `/tasks` slash 列出 | 按 ID 升序 | `test_list_ordering` | REPL 中 `/tasks` | ✅ |

### 3.4 M1-4 Subagent Task 工具

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M1-4.1 | Explore 只有 Read/Grep/Glob/Bash | 无 Write/Edit | `test_explore_filter_whitelist` | — | ✅ |
| M1-4.2 | Plan 只有 Read/Grep/Glob | 无任何写操作 | `test_plan_filter_excludes_write` | — | ✅ |
| M1-4.3 | general-purpose 继承全部 | 与父 registry 等价 | `test_general_purpose_inherits_all` | — | ✅ |
| M1-4.4 | 未知 subagent_type 报 Error | 返回 "unknown" | `test_unknown_subagent_type` | — | ✅ |
| M1-4.5 | Task 工具已注册且 schema 合法 | input_schema 有 prompt / subagent_type | `test_register_adds_task_tool` | — | ✅ |
| M1-4.6 | 子 agent 返回文本总结 | 父 agent 收到字符串 | 真实端到端 | `mycode -p "派子 agent 找所有 register_ 函数"` | ✅ |

### 3.5 M1-5 Skills

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M1-5.1 | SKILL.md frontmatter 解析 | name + description 正确 | `test_parse_skill_with_frontmatter` | — | ✅ |
| M1-5.2 | 无 frontmatter 时用目录名 fallback | skill.name = dir name | `test_parse_without_frontmatter_fallback` | — | ✅ |
| M1-5.3 | skills_dirs 顺序 = 优先级 | 同名前者胜出 | `test_discover_multiple_dirs_first_wins` | 在 `./skills/x/` 和 `~/.mycode/skills/x/` 各放一份不同的 SKILL.md | ✅ |
| M1-5.4 | LoadSkill(name) 返回正文 | 包 `<skill>` 标签 | `test_load_known_and_unknown` | — | ✅ |
| M1-5.5 | 未知 skill 名报 Error | 列出可用名 | `test_load_known_and_unknown` | — | ✅ |
| M1-5.6 | 启动时只注入 name + description | 不把 body 塞 system | `test_descriptions_lists_all` | — | ✅ |
| M1-5.7 | 空 skills_dirs 不崩 | registry 为空 | `test_empty_dirs_no_crash` | — | ✅ |

### 3.6 M1-6 Compact + Roles

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M1-6.1 | microcompact 保留最近 N 条 tool_result | 老的才外置 | `test_microcompact_evicts_old_large` | 看 `.mycode/blobs/*.txt` 产出 | ✅ |
| M1-6.2 | tool_result 数量不足 N 时不动 | evicted == 0 | `test_microcompact_skips_when_few_tools` | — | ✅ |
| M1-6.3 | 小 tool_result 不外置 | 体积 <= evict_threshold 跳过 | `test_microcompact_below_threshold_not_evicted` | — | ✅ |
| M1-6.4 | Token 估算按 ~4 字符 | 可用于阈值判断 | `test_estimate_tokens` | — | ✅ |
| M1-6.5 | auto-compact 按阈值触发 | context_window × threshold_pct% | `test_should_auto_compact_threshold` | — | ✅ |
| M1-6.6 | auto-compact 产出 summary + tail 保留 | system + 1 compacted + 尾 6 条 | `test_auto_compact_produces_summary` | — | ✅ |
| M1-6.7 | transcripts 落盘 | `.mycode/transcripts/*.jsonl` | `test_auto_compact_produces_summary` | 跑 `/compact` 后 `ls .mycode/transcripts/` | ✅ |
| M1-6.8 | `roles.summarize.provider` 生效 | derive 出的 Config.model 正确 | `test_roles_derive_for_summarize` | — | ✅ |
| M1-6.9 | 未填 role 继承顶层 | sub.model == main.model | `test_roles_role_inherits_when_empty` | — | ✅ |
| M1-6.10 | role 可部分覆盖单字段 | 仅 model 变,base_url 继承 | `test_roles_partial_override_model_only` | — | ✅ |
| M1-6.11 | `/compact` slash 手动触发 | REPL 中打印 before→after | — | `printf "/compact\n/quit\n" \| uv run mycode` | ✅ |

---

## 4. 质量验收

### 4.1 测试套件

```bash
cd mycode
uv run pytest -q
```

**结果**：`73 passed in 0.19s`

**测试分布**：

| 文件 | 用例 | 角色 |
|------|-----|------|
| test_schemas.py | 2 | M0 工具 schema 合规 |
| test_tools.py | 10 | M0 六个基础工具 e2e |
| test_config.py | 6 | M0 四级加载 + profile |
| test_dispatcher.py | 5 | M0 并行/串行派发 |
| test_redact.py | 4 | M0 脱敏 |
| test_memory.py | 9 | **M1-1** |
| test_todo.py | 8 | **M1-2** |
| test_tasks.py | 9 | **M1-3** |
| test_subagent.py | 5 | **M1-4** |
| test_skills.py | 6 | **M1-5** |
| test_compact.py | 9 | **M1-6** |
| **合计** | **73** | — |

M1 新增 46 条自动化测试（原 27 → 73）。

### 4.2 回归验收

M1 不应破坏 M0 能力。M0 全部 27 条测试保持 ✅ 通过，未出现回归。

### 4.3 代码体积

```
src/mycode/memory/loader.py         ≈ 90  行
src/mycode/tools/todo.py            ≈ 100 行
src/mycode/tools/tasks.py           ≈ 200 行
src/mycode/tools/subagent.py        ≈ 130 行
src/mycode/tools/skills.py          ≈ 110 行
src/mycode/tools/compact_tool.py    ≈ 40  行
src/mycode/context/compact.py       ≈ 140 行
src/mycode/config/models.py         +60  行(Roles*)
src/mycode/agent/loop.py            +15  行(summarize_llm)
src/mycode/cli.py / ui/repl.py      +~80 行(串接与 slash)
-----------------------------------------------
M1 净增 ≈ 965 行实现 + 46 条测试
```

### 4.4 代码质量检查

- [x] 每个新工具在 `TOOLS.md` 中有对应条款
- [x] 错误路径统一 `Error:` 前缀（对齐 TOOLS.md §7）
- [x] 文件类工具全部走 `safe_path` 审计
- [x] 无硬编码 API key / secret
- [x] 无破坏 M0 已有测试
- [x] `.env` 仍在 `.gitignore`，未泄漏
- [x] 所有新建路径（`.mycode/blobs/` / `.mycode/transcripts/` / `.mycode/tasks/`）均自动 `mkdir`

---

## 5. 端到端冒烟

以下是验收人可手动复现的冒烟脚本（需 `.env` 有效 API key）：

```bash
cd mycode

# 1. 基础工具仍然 OK
uv run mycode -p "一句话总结 README.md"

# 2. Memory 生效
echo "# Project Memory\nProject is mycode, Python CLI." > CLAUDE.md
uv run mycode -p "项目是什么?"   # 应引用 CLAUDE.md 内容
rm CLAUDE.md

# 3. 持久 Task
uv run mycode -p "创建一个 task:写 M1 验收报告"
cat .mycode/tasks/task_*.json

# 4. Subagent
uv run mycode -p "派 Explore 子 agent 列出 src/mycode/tools 下所有 .py 文件"

# 5. Compact
printf "你好\n/compact\n/quit\n" | uv run mycode   # 应打印 compacted: N → M

# 6. Roles 切换
uv run mycode --provider fenbi-mini -p "你是什么模型"
uv run mycode --provider fenbi-sonnet -p "你是什么模型"

# 7. REPL 所有 slash
printf "/help\n/models\n/tools\n/quit\n" | uv run mycode
```

全部步骤在验收环境 (macOS 26, Python 3.13, uv 最新) 实测通过。

---

## 6. 风险与已知限制（供 M2 参考）

| 风险/限制 | 影响 | 缓解/跟进 |
|----------|------|----------|
| auto_compact 会丢失 tool_calls 对应关系 | 极长会话后模型无法追溯具体工具调用 | M2 改为"保留 tool 消息摘要索引" |
| Compact 工具调用后不强制结束本轮 | 极端情况可能被模型连续调用 | M2 在 loop 里对 `Compact` tool_call 加显式 `stop` 信号 |
| 子 agent 无法继承父的 Read 过文件列表 | 每次派发需模型自行说明上下文 | 预期行为（隔离）；M2 可加 hint system prompt |
| `/provider` 切换后 skills 不重扫 | 运行时切 profile 不会看到新挂载的 skill | 无用户诉求；M2 加 `/reload` slash |
| Ctrl-C 中断语义无自动化测试 | 回归风险 | M2 用 signal 注入做 async 测试 |

---

## 7. 验收结论

| 维度 | 要求 | 结果 |
|------|-----|------|
| **功能完整性** | 6 项 M1 条目全部交付 | ✅ |
| **规格一致性** | 对齐 TOOLS.md / DESIGN.md / CONFIG.md | ✅ |
| **测试覆盖** | 新增 ≥30 条自动化测试 | ✅ 新增 46 条 |
| **回归保障** | M0 所有测试不退化 | ✅ 27/27 通过 |
| **可复现性** | `uv sync && uv run pytest` 一键跑过 | ✅ 73/73 通过 |
| **文档** | 有溯源 + 验收两份文档 | ✅ |
| **安全** | 无密钥泄漏 / 路径越界回归 | ✅ |

**最终结论**：**✅ M1 验收通过，批准进入 M2**。

---

## 8. 签署

| 角色 | 姓名 | 日期 |
|------|-----|------|
| 开发 | zhouyunfei | 2026-04 |
| 验收 | _待填写_ | _待填写_ |

> 如验收人在上述冒烟脚本中发现任一步骤失败，请在 Issue 区开 `m1-acceptance-failure` 标签记录。
