# M0 验收报告

| 项目 | 内容 |
|------|------|
| 里程碑 | mycode M0 |
| 交付范围 | CLI + REPL + 流式渲染 + 6 基础工具 + 四级配置 + 27 测试 |
| 验收日期 | 2026-04（事后补写） |
| 起始 Commit | `d24b15d` |
| 最终 Commit | `8de2ca8`（含 REPL 运行时切换增强） |
| 版本 | 0.1.0dev0 |
| 验收结论 | ✅ **通过** |

> **说明**：M0 交付当时只写了 `M0.md`（溯源文档），未独立出验收报告。本文件按 M1/M2 同款模板补齐，事后复核并无发现偏差。

---

## 1. 验收依据

- 规格真源：`docs/DESIGN.md` §9 M0 条目、`docs/TOOLS.md` §1-§2、`docs/CONFIG.md` §1-§3
- 设计文档：`docs/milestones/M0.md`（溯源）
- 质量基线：`DESIGN.md` §10 测试矩阵（对 M0 要求 schema / 协议 / 工具集成 / 中断 / 脱敏 5 项基础覆盖）

---

## 2. 范围确认

### 2.1 约定交付（6 项）

| 条目 | 规格出处 | 交付状态 |
|------|---------|---------|
| CLI 入口 + REPL + 流式渲染 | DESIGN §4.8, §9-M0 | ✅ 交付 |
| OpenAI SDK 封装 + provider profile | DESIGN §4.1, CONFIG §4 | ✅ 交付（7 个 profile + 3 个 fenbi 别名） |
| 6 个基础工具（Bash/Read/Write/Edit/Glob/Grep） | TOOLS §1.1-§1.5, §2.1 | ✅ 交付 |
| Agent Loop（并行派发 + Ctrl-C 中断语义） | DESIGN §5, §4.8 | ✅ 交付 |
| 四级配置加载 + Pydantic 校验 | CONFIG §1-§2 | ✅ 交付 |
| 基础测试（schema/工具/脱敏/配置/dispatcher） | DESIGN §10 | ✅ 27 条 |

### 2.2 范围外（明确未做，非扣分项）

- TodoWrite / 持久化 Tasks / Subagent / Skills / 记忆完整集成 → M1
- 上下文压缩 / 分角色模型 → M1
- Session 持久化 / 后台任务 / MCP → M2
- 多 Agent / Worktree / PyPI → M3
- 多模态 / Windows 原生支持 → 已在 DESIGN §11 决策不做

---

## 3. 功能验收矩阵

### 3.1 CLI 与 REPL 基础

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M0-A.1 | `uv run mycode --help` | 列出全部 CLI flag | — | 命令执行后看输出 | ✅ |
| M0-A.2 | `uv run mycode` 进入 REPL | 横幅 + `mycode >` 提示符 | — | 直接启动 | ✅ |
| M0-A.3 | `mycode -p "..."` 单次模式 | 输出后退出，退出码 0 | — | `uv run mycode -p "hi"` | ✅ |
| M0-A.4 | Ctrl-D 正常退出 | 无 traceback、码 0 | — | REPL 中按 Ctrl-D | ✅ |
| M0-A.5 | `/quit` 正常退出 | 无 traceback | — | REPL 输入 `/quit` | ✅ |
| M0-A.6 | 单次 Ctrl-C | 打断当前工具但不退出 | — | REPL 长任务中按 Ctrl-C | ✅ |
| M0-A.7 | 双 Ctrl-C（1s 内） | 退出进程 | — | 快速按两次 Ctrl-C | ✅ |

### 3.2 Provider 与流式

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M0-B.1 | `--provider deepseek` profile 默认值填充 | base_url/model/api_key_env 自动填 | `test_profile_fills_defaults` | — | ✅ |
| M0-B.2 | `fenbi` profile 的 `default_query` | 请求 URL 带 `?service_provider=ppio` | `test_fenbi_profile_has_default_query` | 抓包 / 看请求 | ✅ |
| M0-B.3 | 项目级 > 用户级 settings | project 覆盖 user | `test_project_overrides_user` | — | ✅ |
| M0-B.4 | CLI flag > settings | CLI 最终话语权 | `test_cli_override_wins` | `--model x` 覆盖 json | ✅ |
| M0-B.5 | `memory_files` 默认含用户级 | 列表含 `~/.mycode/CLAUDE.md` | `test_memory_files_default_includes_user_level` | — | ✅ |
| M0-B.6 | `mcp_servers` 按 key 深合并 | user/project 合并不互相覆盖 | `test_deep_merge_mcp_servers` | — | ✅ |
| M0-B.7 | 流式工具调用识别 | 模型 tool_calls 被 dispatcher 执行 | — | `mycode -p "读 README.md"` | ✅ 真实 fenbi 调用 |
| M0-B.8 | `/provider <name>` 运行时切换 | base_url/model 同步更新 | — | REPL `/provider fenbi-sonnet` | ✅ |
| M0-B.9 | `/models` 列出 profile | 当前 ● 标记 | — | REPL `/models` | ✅ |

### 3.3 六个基础工具

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M0-C.1 | Read 按 1-based 行号前缀输出 | 格式 `"    1\t..."` | `test_read_write_edit_roundtrip` | — | ✅ |
| M0-C.2 | Read offset/limit half-open 区间 | `offset=10, limit=3` → 第 11/12/13 行 | `test_read_offset_limit` | — | ✅ |
| M0-C.3 | Read 二进制占位 | `[binary or too large, N bytes]` | `test_read_binary_placeholder` | `mycode -p "读 img.png"` | ✅ |
| M0-C.4 | Write 必须先 Read | 未 Read 报 Error | `test_write_requires_prior_read` | — | ✅ |
| M0-C.5 | Edit `old_string` 多次命中 | 无 `replace_all` 时报 Error | `test_edit_ambiguous` | — | ✅ |
| M0-C.6 | Bash 正常命令 | stdout+stderr 合并 | `test_bash_ok_and_deny` | — | ✅ |
| M0-C.7 | Bash deny-list（`sudo` 等） | 返回 `Error: command blocked` | `test_bash_ok_and_deny` | `mycode -p "用 Bash 跑 sudo ls"` | ✅ |
| M0-C.8 | Bash exit code != 0 | 输出末尾 `[exit code: N]` | `test_bash_exit_code` | — | ✅ |
| M0-C.9 | Glob 按 mtime 倒序 | 新文件在前 | `test_glob` | — | ✅ |
| M0-C.10 | Grep content 模式返回行 | `def foo():` 出现在输出里 | `test_grep_content` | `mycode -p "找 register_ 开头函数"` | ✅ |
| M0-C.11 | safe_path 拒绝越界 | `../../etc/passwd` 报 Error | `test_path_denied` | — | ✅ |

### 3.4 Agent Loop / 派发

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M0-D.1 | 未知工具返回 Error | `Error: unknown tool '...'` | `test_unknown_tool_returns_error` | — | ✅ |
| M0-D.2 | `denied_tools` 拦截 | `Error: tool '<n>' not allowed` | `test_denied_tool_returns_error` | — | ✅ |
| M0-D.3 | 并行 tool_calls 顺序保持 | 结果列表与入参同序 | `test_result_order_matches_input` | — | ✅ |
| M0-D.4 | 同路径 Write 强制串行 | 多个写同文件全部成功 | `test_same_path_write_serializes` | — | ✅ |
| M0-D.5 | 大输出按 `tool_result_max_bytes` 截断 | 末尾 `[truncated: total N bytes]` | `test_truncation_on_large_output` | — | ✅ |
| M0-D.6 | 工具失败转 `Error:` 字符串 | 不抛到 loop 外 | 所有 tool 测试（`Error:` 前缀一致性） | — | ✅ |
| M0-D.7 | Ctrl-C 补灌未完成 `tool_call_id` | `[interrupted by user]` + `<interrupted/>` | — | 仅手动验证（M1 有规划补自动化） | ⚠️（实现 ✅，自动化测试 ⏳） |

### 3.5 安全与脱敏

| # | 需求 | 期望行为 | 自动化测试 | 手动验证方法 | 结果 |
|---|------|---------|-----------|-------------|------|
| M0-E.1 | 工具 schema 全部合法 JSON Schema | type=object + properties | `test_all_tools_have_schema` | — | ✅ |
| M0-E.2 | OpenAI tools spec 形态 | `type: function` + name/description/parameters | `test_openai_specs_shape` | — | ✅ |
| M0-E.3 | Bearer token 脱敏 | Bearer 后面的 token → `[REDACTED]` | `test_redact_bearer_token` | — | ✅ |
| M0-E.4 | `sk-*` key 脱敏 | 完整替换 | `test_redact_sk_prefix` | — | ✅ |
| M0-E.5 | JSON 里 `api_key` 字段脱敏 | 引号内值替换 | `test_redact_quoted_api_key_json` | — | ✅ |
| M0-E.6 | 普通文本不误伤 | `file not found` 原样 | `test_redact_leaves_ordinary_text` | — | ✅ |

---

## 4. 质量验收

### 4.1 测试套件

```bash
cd mycode
uv sync
uv run pytest -q
```

**M0 当时结果**：`27 passed`
**M2 完成后回溯跑**：`103 passed`，M0 部分 27 条全部保持通过

### 4.2 测试分布（M0 交付时）

| 文件 | 用例数 | 覆盖规格 |
|------|-------|---------|
| `tests/test_schemas.py` | 2 | TOOLS §0 |
| `tests/test_tools.py` | 10 | TOOLS §1-§2 |
| `tests/test_config.py` | 6 | CONFIG §1 |
| `tests/test_dispatcher.py` | 5 | DESIGN §5 |
| `tests/test_redact.py` | 4 | DESIGN §7.2 |
| **合计** | **27** | — |

### 4.3 代码体积（M0 交付时）

```
pyproject.toml                       42 行
src/mycode/cli.py                  ~110 行
src/mycode/config/{loader,models}  ~170 行
src/mycode/llm/{client,providers}  ~180 行
src/mycode/agent/{loop,dispatcher,system_prompt} ~290 行
src/mycode/tools/{builtin,registry,safety}       ~420 行
src/mycode/ui/repl.py              ~180 行
tests/                               ~500 行
-----------------------------------------------
M0 总量 ≈ 1900 行实现 + 500 行测试
```

### 4.4 代码质量 checklist

- [x] 每个工具在 `TOOLS.md` 中有对应条款
- [x] 错误路径统一 `Error:` 前缀
- [x] 文件类工具全部走 `safe_path`
- [x] 无硬编码 API key / `.env` 在 `.gitignore`
- [x] 四级配置 merge 规则与 CONFIG.md §1 一致
- [x] fenbi 等自定义 URL 的 `default_query` 正确传递给 OpenAI SDK
- [x] 进程退出码规范（正常 0 / 中断 130 / 配置错 2）

---

## 5. 端到端冒烟

以下是验收人可手动复现的冒烟脚本（需 `.env` 有效 API key）：

```bash
cd mycode

# 1. CLI 入口基本健康
uv run mycode --version
uv run mycode --help

# 2. 单次模式
uv run mycode -p "用一句话描述 README.md 的内容"

# 3. 工具链真跑
uv run mycode -p "用 Grep 找出所有 register_ 开头的函数定义"

# 4. Profile 切换
uv run mycode --provider fenbi-mini -p "你是什么模型"
uv run mycode --provider fenbi-sonnet -p "你是什么模型"

# 5. REPL 基本命令
printf "/help\n/tools\n/models\n/quit\n" | uv run mycode

# 6. Ctrl-D 退出
echo "" | uv run mycode   # 应立即退出,码 0

# 7. 自动化测试
uv run pytest tests/ -q   # M0 部分 27 个全过(完整 103 条也全过)
```

**全部步骤在 macOS 26 / Python 3.13 / uv 最新版实测通过。**

---

## 6. 风险与已知限制（供 M1+ 参考）

| 风险/限制 | 影响 | 跟进 |
|----------|------|------|
| 无对话持久化 | REPL 退出即丢上下文 | ✅ M2-1 已补 Session resume |
| 无 Token 计数 / 压缩 | 超长会话会直接失败 | ✅ M1-6 已补 micro/auto compact |
| Bash deny-list 简陋 | 恶意命令覆盖不全 | 保持现状；用户可加 `bash_deny_patterns` |
| Windows 未覆盖 | `shell=True` 在 Windows 行为不一致 | DESIGN §11 决策 v1 只保 macOS/Linux |
| 不支持多模态 | Read 不会解析 PNG/PDF | DESIGN §11 决策不做 |
| Ctrl-C 中断语义无自动化测试 | 实现正确但易回归 | M1/M2 仍未补；M3 建议补 |

---

## 7. 验收结论

| 维度 | 要求 | 结果 |
|------|-----|------|
| **功能完整性** | M0 路线图 5 条 bullet 全部交付 | ✅ |
| **规格一致性** | 与 TOOLS.md / DESIGN.md / CONFIG.md 对齐 | ✅ |
| **测试覆盖** | 基础 5 类覆盖 | ✅ 27 条，5 文件 |
| **可复现性** | `uv sync && uv run pytest` 一键跑过 | ✅ 27/27 |
| **端到端** | fenbi 真实网关单次/REPL 打通 | ✅ |
| **文档** | 有溯源文档（本次事后补验收报告） | ✅ 至此完整 |
| **安全** | 脱敏/路径越界/危险命令 | ✅ |

**最终结论**：**✅ M0 验收通过（事后复核）**，当时的交付质量达标且未发现遗漏。

---

## 8. 签署

| 角色 | 姓名 | 日期 |
|------|-----|------|
| 开发 | zhouyunfei | 2026-04 |
| 验收 | _待填写_ | _待填写_ |

> 本文件为事后补写，用于对齐 M1/M2 验收文档格式。M0 当时的实际验收依据是 `docs/milestones/M0.md` §3 节的验收清单，核心结论一致。
