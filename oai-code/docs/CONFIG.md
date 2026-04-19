# oai-code 配置规格（CONFIG.md）

> 四级优先级（高 → 低）：**CLI flag > 项目 `.oaic/settings.json` > 用户 `~/.oaic/settings.json` > 环境变量**。
> 环境变量仅作**默认值来源**，不与 JSON 同级 merge：JSON 里缺失的字段才 fallback 到 env。

---

## 1. 加载顺序与合并规则

1. 加载环境变量 → 生成 `EnvDefaults` 对象
2. 加载 `~/.oaic/settings.json` → 覆盖 EnvDefaults（**深合并**：dict 逐键覆盖，list/scalar 整体替换）
3. 加载 `<cwd>/.oaic/settings.json` → 深合并覆盖
4. 加载 `--config <path>` 或 `$OAIC_CONFIG` 指向的文件 → 深合并覆盖（同规则；两者同时存在时 `--config` 胜出；均不设则跳过）
5. 应用 CLI flag → 顶层字段整体替换
6. Pydantic 校验 → 任一非法字段直接报错退出，不尝试"尽量运行"

**`--config` / `OAIC_CONFIG` 的层级定位**：位于 **项目级 settings < config 文件 < CLI flag** 之间。典型用法是临时叠加一个 profile（如 `--config ci.json` 跑 CI），但 CLI flag 始终是"最终话语权"。

**特殊**：`mcp_servers` 采用**按 key 合并**（用户级给出 `linear`，项目级给出 `github`，两者共存）；同名 key 由更高层整体覆盖低层。

---

## 2. 字段总表

```json
{
  "$schema": "https://oai-code.dev/schema/v1.json",

  "provider": "deepseek",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "api_key_env": "DEEPSEEK_API_KEY",
  "fallback_model": null,

  "max_tokens": 8192,
  "context_window": 128000,
  "temperature": null,

  "compact": {
    "threshold_pct": 75,
    "evict_threshold_bytes": 4096,
    "keep_recent_tool_results": 3
  },

  "parallel_tools": 4,
  "serial_only": false,
  "tool_result_max_bytes": 51200,

  "allowed_tools": null,
  "denied_tools": [],
  "denied_paths": ["~/.ssh", "~/.aws", "~/.gnupg", "**/.env*"],
  "bash_deny_patterns": [],
  "allow_outside_workspace": false,

  "skills_dirs": ["./skills", "~/.oaic/skills"],
  "memory_files": ["CLAUDE.md", "AGENTS.md", ".oaic/MEMORY.md", "~/.oaic/CLAUDE.md"],

  "session": {
    "dir": ".oaic/sessions",
    "auto_save": true,
    "redact_keys": ["authorization", "api_key", "api-key", "openai_api_key"]
  },

  "team": {
    "enabled": false,
    "poll_interval_sec": 5,
    "idle_timeout_sec": 60
  },

  "mcp_servers": {},

  "ui": {
    "theme": "dark",
    "stream": true,
    "show_tool_args": true,
    "confirm_destructive": true
  }
}
```

---

## 3. 字段释义

### 3.1 LLM 连接

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `provider` | string | `"openai"` | 仅作 profile 索引，决定 `base_url`/`api_key_env` 的默认值；不传协议选择 |
| `base_url` | string | profile 决定 | 可显式覆盖；空字符串禁止 |
| `model` | string | profile 决定 | 必填（profile 未给就必须 CLI/JSON 给） |
| `api_key_env` | string | profile 决定 | **只接受环境变量名**，禁止直接写 key |
| `fallback_model` | string \| null | null | 首选 model 报 4xx/5xx 时降级（M2+） |
| `max_tokens` | int | 8192 | 单次 completion 上限 |
| `context_window` | int | 按 model 查表 | 用于计算 compact 阈值 |
| `temperature` | float \| null | null | null = 不传，走模型默认 |

### 3.2 上下文压缩

| 字段 | 默认 | 说明 |
|------|------|------|
| `compact.threshold_pct` | 75 | 触发 auto-compact 的 context 占用百分比 |
| `compact.evict_threshold_bytes` | 4096 | microcompact 外置到 blob 文件的体积阈值 |
| `compact.keep_recent_tool_results` | 3 | 最近 N 轮 tool_result 保留原文 |

### 3.3 工具并发与权限

| 字段 | 默认 | 说明 |
|------|------|------|
| `parallel_tools` | 4 | 单轮并发执行的 tool_calls 上限；1 = 全串行 |
| `serial_only` | false | 兜底开关，等价于 `parallel_tools = 1` |
| `tool_result_max_bytes` | 51200 | 单次 tool_result content 字符串上限；超出时末尾追加 `\n[truncated: total N bytes]` |
| `allowed_tools` | null | null = 全允许；给出数组则仅允许列表内工具 |
| `denied_tools` | [] | 在 allowed_tools 基础上再黑名单 |
| `denied_paths` | 见默认 | glob 或前缀，匹配则所有文件类工具拒绝 |
| `bash_deny_patterns` | [] | 追加到 Bash 硬编码 deny-list 的用户正则 |
| `allow_outside_workspace` | false | 允许读/写 workspace_root 之外的路径 |

### 3.4 Skills 与记忆

| 字段 | 默认 | 说明 |
|------|------|------|
| `skills_dirs` | `["./skills", "~/.oaic/skills"]` | 扫描顺序即优先级，同名时前者覆盖后者 |
| `memory_files` | `["CLAUDE.md", "AGENTS.md", ".oaic/MEMORY.md", "~/.oaic/CLAUDE.md"]` | 按数组顺序读取并拼接到 system prompt；前 3 项为项目级（基于 cwd），末项为用户级（`~/` 展开）；缺失的文件静默跳过 |

### 3.5 Session

| 字段 | 默认 | 说明 |
|------|------|------|
| `session.dir` | `.oaic/sessions` | 存储目录 |
| `session.auto_save` | true | 每轮结束后追加写 jsonl |
| `session.redact_keys` | 见默认 | 写入前按 key 脱敏（value 长度 > 8 时替换为 `[REDACTED]`） |

### 3.6 Team（多 agent，v1 默认关）

| 字段 | 默认 | 说明 |
|------|------|------|
| `team.enabled` | false | false 时 `SpawnTeammate` 等工具不注册 |
| `team.poll_interval_sec` | 5 | idle 状态轮询间隔 |
| `team.idle_timeout_sec` | 60 | idle 超时后自动 shutdown |

### 3.7 MCP servers

```json
{
  "mcp_servers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "@linear/mcp-server"],
      "env": {"LINEAR_API_KEY_env": "LINEAR_API_KEY"},
      "timeout_sec": 30,
      "enabled": true
    },
    "postgres": {
      "type": "sse",
      "url": "http://localhost:8765/sse",
      "headers": {"Authorization_env": "PG_MCP_TOKEN"}
    }
  }
}
```

**`_env` 后缀解析规则**（env 与 headers 通用）：
- key 以 `_env` 结尾：**strip 掉 `_env` 后缀作为真实 key**，value 视为环境变量名，从主进程 env 读取实际值
- key 不以 `_env` 结尾：字面使用 key 和 value

**示例解析结果**：
| 输入 | 实际 env/header key | 实际 value |
|------|---------------------|-----------|
| `"LINEAR_API_KEY_env": "LINEAR_API_KEY"` | `LINEAR_API_KEY` | `$LINEAR_API_KEY` 环境变量的值 |
| `"Authorization_env": "PG_MCP_TOKEN"` | `Authorization` | `$PG_MCP_TOKEN` 环境变量的值 |
| `"LOG_LEVEL": "debug"` | `LOG_LEVEL` | 字面 `"debug"` |

环境变量不存在时：启动时报错，fail-fast。

**子字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"stdio"` (默认) / `"sse"` / `"http"` | 传输方式 |
| `command` + `args` | string + array | stdio 类型下的子进程命令 |
| `url` | string | sse/http 类型下的端点 |
| `env` | dict | 子进程环境变量白名单注入；**key 以 `_env` 结尾时从主进程 env 取值** |
| `headers` | dict | http/sse 类型；同样支持 `_env` 后缀 |
| `timeout_sec` | int | 单次工具调用超时 |
| `enabled` | bool | false 时不启动但保留配置 |

**环境注入规则**：MCP 子进程**只继承**下列 env —— `PATH`、`HOME`、`LANG`、`LC_*`、以及 `env` 字段显式给出的键；其余一律 drop。

### 3.8 UI

| 字段 | 默认 | 说明 |
|------|------|------|
| `ui.theme` | `"dark"` | `dark` / `light` / `auto` |
| `ui.stream` | true | 流式渲染 LLM 回复 |
| `ui.show_tool_args` | true | 每次工具调用展开参数 |
| `ui.confirm_destructive` | true | `rm`、`Write` 覆盖已存在大文件等动作前交互确认 |

---

## 4. Provider Profiles（预置）

`src/oai_code/llm/providers.py` 提供下列 profile，`provider` 字段命中时作为默认值：

| provider | base_url | 推荐 model | api_key_env |
|----------|---------|-----------|-------------|
| `openai` | `https://api.openai.com/v1` | `gpt-4o` | `OPENAI_API_KEY` |
| `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` | `DASHSCOPE_API_KEY` |
| `openrouter` | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4` | `OPENROUTER_API_KEY` |
| `ollama` | `http://localhost:11434/v1` | `qwen2.5-coder` | `OLLAMA_API_KEY`（可留空） |
| `vllm` | `http://localhost:8000/v1` | 用户提供 | `VLLM_API_KEY` |
| `custom` | — | — | — |

Profile 只给默认值，用户可以部分覆盖：
```json
{"provider": "deepseek", "model": "deepseek-reasoner"}
```

---

## 5. 环境变量

| 变量 | 用途 |
|------|------|
| `OAIC_CONFIG` | 指定额外的 settings.json 路径 |
| `OAIC_PROVIDER` | 覆盖 `provider` |
| `OAIC_MODEL` | 覆盖 `model` |
| `OAIC_BASE_URL` | 覆盖 `base_url` |
| `OAIC_DEBUG` | `1` = 打开 debug（等价 `--debug`） |
| `<API_KEY_ENV>` | 各 provider 的 key（由 `api_key_env` 指定） |

**不提供** `OAIC_API_KEY` 这种通用名——强制走 `api_key_env` 间接引用，避免 shell history 意外泄露。

---

## 6. CLI flag 速查

| flag | 等价字段 |
|------|---------|
| `--provider <name>` | `provider` |
| `--model <id>` | `model` |
| `--base-url <url>` | `base_url` |
| `-p, --prompt "<text>"` | 单次模式（不进 REPL） |
| `--resume <session-id>` | 恢复 session |
| `--config <path>` | 额外加载的 settings.json |
| `--allow-tool <name>` | 追加到 `allowed_tools`（若当前为 null，则**先初始化为全量内置工具列表再追加**，即 `--allow-tool X` 永远不会把"全允许"变成"只允许 X"） |
| `--deny-tool <name>` | 追加到 `denied_tools`；与 `allowed_tools` 的 null 状态无关 |
| `--no-stream` | `ui.stream = false` |
| `--serial` | `serial_only = true` |
| `--debug` | 详细日志 |
| `--debug-raw` | 不脱敏日志（仅写 `.oaic/debug/`） |

---

## 7. 示例

> 下述示例中的 `//` 注释仅供阅读说明，**settings.json 本身必须是合法 JSON**（不支持注释）；如需在本地用 JSONC，请自行去除注释后保存。

### 7.1 最小用户级配置
```jsonc
// ~/.oaic/settings.json
{
  "provider": "deepseek",
  "api_key_env": "DEEPSEEK_API_KEY"
}
```
其余字段全走 profile 默认值。

### 7.2 项目级覆盖
```jsonc
// ./.oaic/settings.json
{
  "model": "deepseek-reasoner",
  "denied_paths": ["~/.ssh", "~/.aws", "**/.env*", "**/secrets/**"],
  "allowed_tools": ["Read", "Grep", "Glob", "Bash", "Edit", "Write", "TodoWrite"],
  "mcp_servers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN_env": "GH_TOKEN"}
    }
  }
}
```

### 7.3 本地 Ollama
```json
{
  "provider": "ollama",
  "model": "qwen2.5-coder:14b",
  "base_url": "http://localhost:11434/v1",
  "context_window": 32768,
  "serial_only": true
}
```

---

## 8. 迁移提示（Claude Code → oai-code）

- `~/.claude/settings.json` 里的 `mcp_servers` **结构一致**，可直接拷贝
- `~/.claude/CLAUDE.md` 默认会被读到（见 `memory_files`）
- `~/.claude/skills/<name>/SKILL.md` 目录结构兼容，软链到 `~/.oaic/skills/` 即可

---

## 9. 校验与错误

启动时的 Pydantic 校验错误一律 fail-fast，退出码 2。典型错误信息：

```
oaic: invalid config at .oaic/settings.json
  - model: field required (no profile default for provider 'custom')
  - compact.threshold_pct: must be 10..95, got 150
  - mcp_servers.linear.command: missing
```

**不做"尽量运行"**：宁可拒绝启动，也不让用户带着半可用配置跑出错的工具结果。
