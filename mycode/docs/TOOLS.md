# mycode 工具规格（TOOLS.md）

> **真源范围**：本文件仅对**工具名、input_schema、tool_result 与错误串格式**具有最终解释权。
> 配置字段的定义（默认值、类型、加载顺序）以 **`CONFIG.md`** 为准，本文件只引用配置字段名并描述行为。
> 架构层议题（agent loop、并行/中断策略、威胁模型）以 **`DESIGN.md`** 为准。
> 权威矩阵见 `DESIGN.md §12`。
>
> 所有工具均通过 OpenAI `tools` / `tool_calls` / `role: "tool"` 协议暴露给模型。

---

## 0. 公共约定

### 0.1 命名
- 内置工具用 **PascalCase**：`Bash`、`Read`、`Edit`……
- MCP 工具加前缀：`mcp__<server>__<tool>`；拼接后长度 > 64 字符时 `mcp__<server>__<sha1(tool)[:8]>`
- 子工具按下划线延展：`TaskCreate`、`TaskUpdate`、`BackgroundRun`

### 0.2 参数字段命名
对齐 Claude Code，方便迁移：

| 概念 | 字段名 |
|------|-------|
| 文件路径 | `file_path`（绝对路径优先，相对按 cwd 解析） |
| 编辑的旧文本 | `old_string` |
| 编辑的新文本 | `new_string` |
| 正则模式 | `pattern` |
| Glob 表达式 | `pattern` |
| 子 agent 任务 | `prompt` |
| 分页 | `limit` / `offset` |

### 0.3 tool_result 格式（所有工具）
```json
{
  "role": "tool",
  "tool_call_id": "<id>",
  "content": "<string>"
}
```
- **content 始终是字符串**，即使内部是 JSON 也 `json.dumps(..., ensure_ascii=False)` 后放入
- **单次 result 上限 50 KiB（51200 字节）**，由 `config.tool_result_max_bytes` 控制；超出时末尾追加 `\n[truncated: total N bytes]`
- 异常路径（工具执行失败）→ `content = "Error: <msg>"`，**绝不抛出到 loop 外**

### 0.4 权限标签
每个工具在 registry 里带 `requires: list[str]`，取值域：
- `exec` — 执行任意代码/命令
- `write` — 写本地文件系统
- `network` — 主动发起网络请求
- `delegate` — 派发/启动新的 agent 进程

v1 仅做静态 `allowed_tools` 白名单；M2 接 `allow/deny/ask` 三态。

### 0.5 超时与体积
| 指标 | 默认值 | 覆盖方式 |
|------|--------|---------|
| Bash 单次超时 | 120s | 工具参数 `timeout` |
| 单个工具 result 上限 | 50 KiB（51200 字节） | 配置 `tool_result_max_bytes` |
| 单次 Read 读取上限 | 5000 行 或 256 KiB | 参数 `limit` |
| microcompact 大 result 外置阈值 | 4 KiB（4096 字节） | 配置 `compact.evict_threshold_bytes` |

### 0.6 安全路径
所有文件类工具调用 `safe_path(p)`：
1. 相对路径按 cwd 解析为绝对路径
2. 拒绝 `config.denied_paths`（默认 `~/.ssh`、`~/.aws`、`~/.gnupg`、`**/.env*`）
3. 拒绝逃出 `workspace_root`（除非 `allow_outside_workspace = true`）

---

## 1. 文件系统工具

### 1.1 `Read`
读取文本文件。二进制文件返回占位符，不读原内容。

```json
{
  "name": "Read",
  "description": "Read a text file. Returns content with 1-based line numbers prefixed.",
  "requires": [],
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": {"type": "string", "description": "Absolute or cwd-relative path"},
      "offset": {"type": "integer", "minimum": 0, "description": "0-based start line; offset=0 表示从第 1 行开始"},
      "limit":  {"type": "integer", "minimum": 1, "maximum": 5000, "description": "最多读取行数,与 offset 组合为 [offset, offset+limit)"}
    },
    "required": ["file_path"]
  }
}
```

**输出**：`"  1\tcontent\n  2\tcontent\n..."`；二进制或 > 256KB → `"[binary or too large, N bytes]"`。

**offset / limit 语义**（钉死，防止误解）：
- `offset` 是**文件起始的 0-based 行下标**（不是"跳过行数"），`offset=0` 输出从第 1 行开始
- 输出行号前缀始终按**文件真实行号**显示，不因 offset 重置：`offset=10, limit=3` 返回形如 `" 11\t...\n 12\t...\n 13\t...\n"`
- 可读区间为 half-open `[offset, offset + limit)`，超出文件末尾则截断

### 1.2 `Write`
完整覆盖写入。**要求同 session 内至少 Read 过该文件一次**（防止盲目覆盖），新文件除外。

```json
{
  "name": "Write",
  "requires": ["write"],
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": {"type": "string"},
      "content":   {"type": "string"}
    },
    "required": ["file_path", "content"]
  }
}
```

**输出**：`"Wrote N bytes to <path>"` 或 `"Error: must Read file before overwriting"`。

### 1.3 `Edit`
精确字符串替换。`old_string` 在文件中必须**恰好出现一次**（除非 `replace_all = true`）。

```json
{
  "name": "Edit",
  "requires": ["write"],
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path":   {"type": "string"},
      "old_string":  {"type": "string"},
      "new_string":  {"type": "string"},
      "replace_all": {"type": "boolean", "default": false}
    },
    "required": ["file_path", "old_string", "new_string"]
  }
}
```

**错误**：
- `old_string` 未命中 → `"Error: old_string not found"`
- 命中多次且未开 `replace_all` → `"Error: old_string matched N times; pass more context or set replace_all"`

### 1.4 `Glob`
```json
{
  "name": "Glob",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern": {"type": "string", "description": "e.g. 'src/**/*.py'"},
      "path":    {"type": "string", "description": "Search root; default cwd"}
    },
    "required": ["pattern"]
  }
}
```
**输出**：匹配文件路径列表，按 mtime 倒序，每行一个；> 500 条截断。

### 1.5 `Grep`
基于 `ripgrep`（`rg`）实现。

```json
{
  "name": "Grep",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern":     {"type": "string"},
      "path":        {"type": "string"},
      "glob":        {"type": "string", "description": "e.g. '*.py'"},
      "output_mode": {"type": "string", "enum": ["files_with_matches", "content", "count"], "default": "files_with_matches"},
      "-i":          {"type": "boolean", "description": "case-insensitive"},
      "-n":          {"type": "boolean", "description": "line numbers (content mode)"},
      "-C":          {"type": "integer", "description": "context lines"},
      "head_limit":  {"type": "integer", "default": 250, "description": "0 = unlimited"}
    },
    "required": ["pattern"]
  }
}
```

---

## 2. 执行工具

### 2.1 `Bash`
前台执行 shell 命令。

```json
{
  "name": "Bash",
  "requires": ["exec"],
  "input_schema": {
    "type": "object",
    "properties": {
      "command":     {"type": "string"},
      "timeout":     {"type": "integer", "default": 120, "maximum": 600},
      "description": {"type": "string", "description": "5-10 word summary shown in UI"}
    },
    "required": ["command"]
  }
}
```

**拦截规则**（deny-list，硬编码，不可关闭）：
- `rm -rf /`、`rm -rf ~`、`rm -rf $HOME`
- `sudo`、`shutdown`、`reboot`、`mkfs`
- `> /dev/sd`、`dd of=/dev/`
- 任何匹配 `config.bash_deny_patterns` 正则的命令

**输出**：`stdout + stderr`（合并），超时 → `"Error: Timeout (Ns)"`，非零 exit → 正常输出但末尾附 `"\n[exit code: N]"`。

### 2.2 `BackgroundRun` / `BackgroundCheck`
```json
{
  "name": "BackgroundRun",
  "requires": ["exec"],
  "input_schema": {
    "type": "object",
    "properties": {
      "command":     {"type": "string"},
      "timeout":     {"type": "integer", "default": 3600},
      "description": {"type": "string"}
    },
    "required": ["command"]
  }
}
```
返回 `"Background task <id> started"`；完成后通知会在下一轮 loop 开始时注入 user message `<background-results>...`。

```json
{
  "name": "BackgroundCheck",
  "input_schema": {
    "type": "object",
    "properties": {
      "task_id": {"type": "string", "description": "Omit to list all"}
    }
  }
}
```

---

## 3. 任务 / 清单

### 3.1 `TodoWrite`
短期 checklist（仅存内存，不落盘）。

```json
{
  "name": "TodoWrite",
  "input_schema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "maxItems": 20,
        "items": {
          "type": "object",
          "properties": {
            "content":    {"type": "string"},
            "status":     {"type": "string", "enum": ["pending", "in_progress", "completed"]},
            "activeForm": {"type": "string", "description": "Present-continuous for spinner"}
          },
          "required": ["content", "status", "activeForm"]
        }
      }
    },
    "required": ["items"]
  }
}
```
**不变式**：`in_progress` 最多 1 条；否则 `"Error: only one in_progress allowed"`。

### 3.2 `TaskCreate` / `TaskGet` / `TaskUpdate` / `TaskList`
持久化到 `.mycode/tasks/task_<id>.json`。

```json
{
  "name": "TaskCreate",
  "requires": ["write"],
  "input_schema": {
    "type": "object",
    "properties": {
      "subject":     {"type": "string"},
      "description": {"type": "string"},
      "activeForm":  {"type": "string"}
    },
    "required": ["subject"]
  }
}
```

```json
{
  "name": "TaskUpdate",
  "requires": ["write"],
  "input_schema": {
    "type": "object",
    "properties": {
      "task_id":           {"type": "integer"},
      "status":            {"type": "string", "enum": ["pending", "in_progress", "completed", "deleted"]},
      "owner":             {"type": "string"},
      "add_blocked_by":    {"type": "array", "items": {"type": "integer"}},
      "remove_blocked_by": {"type": "array", "items": {"type": "integer"}}
    },
    "required": ["task_id"]
  }
}
```

**副作用**：`status = completed` 时自动把其他任务 JSON 里 `blockedBy` 数组中含本 id 的项移除；`status = deleted` 物理删除 json 文件。

> **字段命名约定**：工具参数名用 snake_case（`add_blocked_by` / `remove_blocked_by`），落盘 JSON 字段名用 camelCase（`blockedBy`）——前者对齐 OpenAI schema 习惯、后者对齐 Claude Code 的 Task 结构，便于迁移。

```json
{"name": "TaskGet",  "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}}
{"name": "TaskList", "input_schema": {"type": "object", "properties": {}}}
```

---

## 4. Subagent 与 Skills

### 4.1 `Task`（派发子 agent）
```json
{
  "name": "Task",
  "requires": ["delegate"],
  "input_schema": {
    "type": "object",
    "properties": {
      "description":   {"type": "string", "description": "3-5 word label"},
      "prompt":        {"type": "string"},
      "subagent_type": {"type": "string", "enum": ["Explore", "general-purpose", "Plan"], "default": "Explore"}
    },
    "required": ["description", "prompt"]
  }
}
```

子 agent 的工具集按类型限制：
- `Explore`：`Read` / `Grep` / `Glob` / `Bash`(read-only)
- `general-purpose`：全部内置工具
- `Plan`：`Read` / `Grep` / `Glob`，不得写文件

**返回值**：子 agent 的最终文本总结（不把子 agent 内部 messages 回传父）。

### 4.2 `LoadSkill`
```json
{
  "name": "LoadSkill",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Skill name from 启动时注入的列表"}
    },
    "required": ["name"]
  }
}
```
**返回值**：`<skill name="xxx">\n<SKILL.md body>\n</skill>`；未知名字 → `"Error: Unknown skill 'xxx'. Available: ..."`。

---

## 5. 上下文

### 5.1 `Compact`
```json
{
  "name": "Compact",
  "input_schema": {"type": "object", "properties": {"focus": {"type": "string", "description": "What to preserve"}}}
}
```
调用后：当前 messages 经 LLM 摘要 → 替换为单条 user message；完整历史落盘到 `.mycode/transcripts/<ts>.jsonl`。**调用后 loop 立即结束当前轮**，下一次用户输入开始新上下文。

---

## 6. 多 Agent（v1 可选，默认关闭）

以下工具仅在 `config.team.enabled = true` 时注册。

### 6.1 `SpawnTeammate`
```json
{
  "name": "SpawnTeammate",
  "requires": ["delegate"],
  "input_schema": {
    "type": "object",
    "properties": {
      "name":   {"type": "string"},
      "role":   {"type": "string"},
      "prompt": {"type": "string"}
    },
    "required": ["name", "role", "prompt"]
  }
}
```

### 6.2 `SendMessage` / `ReadInbox` / `Broadcast` / `ListTeammates`
```json
{
  "name": "SendMessage",
  "input_schema": {
    "type": "object",
    "properties": {
      "to":       {"type": "string"},
      "content":  {"type": "string"},
      "msg_type": {"type": "string", "enum": ["message", "broadcast", "shutdown_request", "plan_approval_response"], "default": "message"}
    },
    "required": ["to", "content"]
  }
}
```
```json
{"name": "ReadInbox",     "input_schema": {"type": "object", "properties": {}}}
{"name": "Broadcast",     "input_schema": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}
{"name": "ListTeammates", "input_schema": {"type": "object", "properties": {}}}
```

### 6.3 `ShutdownRequest` / `PlanApproval` / `ClaimTask`
```json
{"name": "ShutdownRequest", "input_schema": {"type": "object", "properties": {"teammate": {"type": "string"}}, "required": ["teammate"]}}
{"name": "PlanApproval",    "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"}, "feedback": {"type": "string"}}, "required": ["request_id", "approve"]}}
{"name": "ClaimTask",       "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}}
```

---

## 7. 错误格式统一表

| 场景 | content 字段值 |
|------|---------------|
| 工具参数缺失/非法 | `"Error: <schema violation msg>"` |
| 路径越界 | `"Error: path '<p>' escapes workspace"` |
| 路径命中 denied_paths | `"Error: path '<p>' is denied by policy"` |
| 未知工具 | `"Error: unknown tool '<name>'"` |
| 超时 | `"Error: Timeout (Ns)"` |
| 上游网络失败 | `"Error: upstream <class>: <msg>"` |
| 未知异常 | `"Error: <exc_class>: <msg>"` |

**统一前缀**：任何错误 content 必须以 `"Error:"` 起始，便于模型识别。

---

## 8. 与 Claude Code 的差异摘要

| 项 | Claude Code | mycode |
|----|-------------|----------|
| 协议 | Anthropic Messages API | OpenAI Chat Completions |
| 错误对话化 | 通过 `is_error: true` 标记 | 统一 `"Error:"` 前缀字符串（OpenAI 协议无 is_error 字段） |
| 工具并行 | 模型侧 parallel tool use | 依赖 OpenAI parallel tool_calls + 本地串行化规则（DESIGN §5） |
| `Read` 图像 | 多模态原生 | v1 不支持，返回占位 |
| TaskOutput | 原生支持 | 用 `BackgroundCheck` 替代 |

---

## 9. 变更规则

修改本文件需满足：
1. 新增字段 → **向后兼容**，老参数仍可接受
2. 删除/重命名字段 → 需同步改 `TOOL_SCHEMA_VERSION`（存于 registry.py），session 落盘带版本号
3. 错误 content 前缀保持 `"Error:"`，子分类用冒号 `"Error: <category>: <detail>"`
