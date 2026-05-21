# s10: System Prompt — 執行時組裝，不硬編碼

[中文](README.md) · [繁中](README.zh-tw.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → ... → s08 → s09 → `s10` → [s11](../s11_error_recovery/) → s12 → ... → s20
> *"prompt 是組裝出來的, 不是寫死的"* — 分段 + 按需拼接 + 快取。
>
> **Harness 層**: 提示 — 執行時組裝, 不硬編碼。

---

## 問題

從 s01 到 s09，system prompt 都是一行硬編碼：

```python
SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks."
```

s01 夠用，只有 bash、read、write 三個工具。但到 s09，Agent 已經有記憶、有壓縮、有技能載入。prompt 該提的能力越來越多：

```python
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Use tools to solve tasks. Act, don't explain. "
    "Before starting any multi-step task, use todo_write. "
    "Skills are available via list_skills and load_skill. "
    "Relevant memories are injected below when available. "
    # ... 加一個能力就多一段
)
```

三個問題：

1. **換專案要重寫整個 prompt**，不知道哪些該改、哪些該留
2. **修改一處可能影響全域性**，加一段工具描述可能跟前面的指令衝突
3. **每次請求都帶全部內容**，即使當前對話用不到某些段落也浪費 token

System prompt 應該是執行時根據當前狀態組裝的配置：哪些工具啟用、哪些上下文可見、哪些記憶相關、哪些內容必須保持穩定以命中 prompt cache。

---

## 解決方案

![System Prompt Overview](images/system-prompt-overview.svg)

s10 聚焦 prompt 組裝機制。以 s08-s09 的能力為背景，但不重複實現壓縮和記憶系統。核心變動：把硬編碼的 `SYSTEM` 拆成獨立段落（section），執行時根據真實狀態按需拼接，快取結果避免重複組裝。

四個 section，兩種載入策略：

| Section | 載入策略 | 內容 | 判斷依據 |
|---------|---------|------|---------|
| identity | 始終 | 你是誰、怎麼做事 | 始終存在 |
| tools | 始終 | 可用工具列表 | `enabled_tools` |
| workspace | 始終 | 工作目錄 | 始終存在 |
| memory | 按需 | 相關記憶內容 | `.memory/MEMORY.md` 是否存在 |

關鍵設計：section 是否載入取決於真實狀態（工具是否存在、檔案是否存在），不是訊息裡的關鍵詞。

---

## 工作原理

### PROMPT_SECTIONS: 分段定義

把一大段字串拆成字典，每個 key 是一個主題：

```python
PROMPT_SECTIONS = {
    "identity": "You are a coding agent. Act, don't explain.",
    "tools": "Available tools: bash, read_file, write_file.",
    "workspace": f"Working directory: {WORKDIR}",
    "memory": "Relevant memories are injected below when available.",
}
```

每個 section 獨立維護。修改 `tools` 不影響 `identity`，新增 `memory` 不動 `workspace`。

### assemble_system_prompt: 按需拼接

不是所有 section 每次都需要。當前沒有記憶檔案，載入 memory section 只是浪費 token。根據 context 的真實狀態決定載入哪些：

```python
def assemble_system_prompt(context: dict) -> str:
    sections = []

    # 始終載入
    sections.append(PROMPT_SECTIONS["identity"])
    sections.append(PROMPT_SECTIONS["tools"])
    sections.append(PROMPT_SECTIONS["workspace"])

    # 按需載入 — 基於真實狀態，不是關鍵詞
    memories = context.get("memories", "")
    if memories:
        sections.append(f"Relevant memories:\n{memories}")

    return "\n\n".join(sections)
```

"始終載入"的是每輪都需要的：身份、工具、工作目錄。"按需載入"的只在特定條件下才有用。

為什麼不全載入？token 有成本（system prompt 每輪計費），資訊越少 LLM 越專注（無關指令是噪音）。

### get_system_prompt: 快取避免重複拼接

上下文沒變時（同一輪對話的多次 LLM 呼叫，context 相同），重新拼接是浪費。用確定性序列化檢測變化，命中快取直接返回：

```python
def get_system_prompt(context: dict) -> str:
    global _last_context_key, _last_prompt
    key = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
    if key == _last_context_key and _last_prompt:
        return _last_prompt
    _last_context_key = key
    _last_prompt = assemble_system_prompt(context)
    return _last_prompt
```

用 `json.dumps` 而不是 `hash()`：Python 內建 `hash()` 有程序隨機化，不適合做穩定 cache key，而且遇到 list/dict 會報 `unhashable type`。

注意：這裡的快取只是"避免重複拼接字串"，和 CC 的 API prompt cache 不是一回事。CC 的 prompt cache 透過 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 分隔靜態和動態部分，靜態部分命中 global cache，不因動態內容變化而失效。

### context: 真實狀態，不是關鍵詞猜測

context 反映當前執行態的真實狀態：

```python
def update_context(context: dict, messages: list) -> dict:
    memories = ""
    if MEMORY_INDEX.exists():
        content = MEMORY_INDEX.read_text().strip()
        if content:
            memories = content
    return {
        "enabled_tools": list(TOOL_HANDLERS.keys()),
        "workspace": str(WORKDIR),
        "memories": memories,
    }
```

`enabled_tools` 列出實際註冊的工具。`memories` 檢查 `.memory/MEMORY.md` 是否存在。section 載入基於這些真實狀態，不在訊息裡搜關鍵詞。

### 合起來跑

```python
def agent_loop(messages: list, context: dict):
    system = get_system_prompt(context)
    while True:
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=TOOLS, max_tokens=8000)
        # ... 工具執行 ...
        context = update_context(context, messages)
        system = get_system_prompt(context)
```

每輪迴圈開頭拿一次 system prompt。context 變了就重新組裝，沒變就返回快取。

---

## 相對 s09 的變更

| 元件 | 之前 (s09) | 之後 (s10) |
|------|-----------|-----------|
| prompt | 硬編碼 SYSTEM 字串 | PROMPT_SECTIONS + assemble_system_prompt |
| 快取 | 無 | get_system_prompt（json.dumps 檢測 + 快取） |
| 新函式 | — | assemble_system_prompt, get_system_prompt, update_context |
| 工具 | bash, read_file, write_file (3) | bash, read_file, write_file (3) — 不變 |
| 迴圈 | 用固定 SYSTEM | 用 get_system_prompt(context) |

---

## 試一下

```sh
cd learn-claude-code
python s10_system_prompt/code.py
```

觀察重點：

1. 輸出中能看到哪些 section 被載入了（`[assembled] sections: ...` 標籤）
2. 連續對話時，快取命中顯示 `[cache hit]`
3. 建立 `.memory/MEMORY.md` 檔案後，下一輪 memory section 自動載入

試試這些 prompt：

1. `Read the file README.md`（觀察始終載入的三個 section）
2. `Create a file called .memory/MEMORY.md with content "- [test](test.md) — test memory"`（寫入記憶索引）
3. `Read the file code.py`（觀察 memory section 是否出現）

---

## 接下來

System prompt 可以執行時組裝了，但 Agent 碰到錯誤還是會崩。網路抖動、API 限流、輸出被截斷、上下文超限，這些不是 bug，是常態。

s11 Error Recovery → 四條恢復路徑。升級 token、壓縮上下文、指數退避、切換模型。

<details>
<summary>深入 CC 原始碼</summary>

> 以下基於 CC 原始碼 `constants/prompts.ts`（914 行）、`constants/systemPromptSections.ts`（68 行）、`context.ts`（189 行）、`utils/api.ts`（718 行）、`utils/systemPrompt.ts`（123 行）、`bootstrap/state.ts` 的分析。

### CC 的 system prompt 有多少 section？

數量不固定，受 feature flag、output style、KAIROS/Proactive 模式、使用者型別、token 預算等影響。大致分兩類：

**靜態 section**（始終載入）：identity、system、doing_tasks、actions、using_tools、tone_style、output_efficiency 等。

**動態 section**（按狀態載入）：session_guidance、memory、ant_model_override、env_info_simple、language、output_style、mcp_instructions、scratchpad、frc、summarize_tool_results、numeric_length_anchors、token_budget、brief 等。

`mcp_instructions` 是唯一的易失性 section（透過 `DANGEROUS_uncachedSystemPromptSection()` 建立），因為 MCP server 可以在輪次間連線和斷開。

### 組裝函式

```typescript
getSystemPrompt(tools, model, additionalWorkingDirs?, mcpClients?): Promise<string[]>
```

返回 `string[]`（每個元素是一個 section），由 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 分隔靜態和動態部分。

### cache scope

啟用 global cache boundary 時，靜態 section 合併成一個 global cache block，動態 section 不使用 global cache（`cacheScope: null`）。沒有 boundary 或跳過 global cache 的路徑才會走 org scope。

教學版的快取只避免重複拼接字串。CC 的三層快取：

1. **lodash memoize**：`getSystemContext` 和 `getUserContext` 在會話中快取（`context.ts`）
2. **section 註冊快取**：`STATE.systemPromptSectionCache` 快取動態 section 結果，`/clear` 或 `/compact` 時清除
3. **API 級快取**：`splitSysPromptPrefix()`（`api.ts`）把 prompt 按 boundary 分成不同 cache scope 的塊

### getUserContext vs getSystemContext

| | getSystemContext | getUserContext |
|---|---|---|
| 內容 | gitStatus、cacheBreaker | CLAUDE.md 內容、currentDate |
| 注入方式 | 追加到 system prompt 陣列 | 前置為 `<system-reminder>` 使用者訊息 |
| 何時跳過 | 自定義 system prompt 時 | 始終執行 |

### 模式如何改變 prompt

- **CLAUDE_CODE_SIMPLE**：整個 prompt 只有 2 行
- **Proactive/KAIROS**：用緊湊版 prompt 替換所有標準 section
- **Coordinator**：用協調器專用 prompt 完全替換
- **Agent 模式**：Agent 定義的 prompt 替換或追加到預設 prompt

### 總大小

標準互動模式下 system prompt 核心約 20-30KB 文字。CLAUDE_CODE_SIMPLE 約 150 字元。使用者上下文（CLAUDE.md）和系統上下文（git status）在此基礎上累加。

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
