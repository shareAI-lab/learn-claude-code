# s11: Error Recovery — 錯誤不是結束，是重試的開始

[中文](README.md) · [繁中](README.zh-tw.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → ... → s09 → s10 → `s11` → [s12](../s12_task_system/) → s13 → ... → s20
> *"錯誤不是終點, 是重試的起點"* — 升級 token、壓縮上下文、切換模型。
>
> **Harness 層**: 韌性 — 主迴圈遇到錯誤時分類並恢復。

---

## 問題

Agent 跑著跑著報錯了：

```
Error: 529 overloaded
```

Agent 崩潰了。它沒有重試，沒有換模型，沒有減少上下文——直接崩潰。

生產環境中 API 錯誤是常態。三種最常見的故障模式：**輸出被截斷**（模型話說一半 token 用完了）、**上下文超限**（壓縮後還是太長）、**臨時故障**（429 限流 / 529 過載）。一個不處理錯誤的 Agent 就像一個一碰就熄火的車。

---

## 解決方案

![Error Recovery Overview](images/error-recovery-overview.svg)

s10 的迴圈、prompt 組裝全部保留。唯一的變動：LLM 呼叫包裹在 try/except 裡，根據錯誤型別走不同的恢復路徑。恢復後 `continue` 回到迴圈開頭重新呼叫 LLM。

三種最常見的恢復模式（教學版只處理 429/529；真實系統還覆蓋連線錯誤、超時、雲廠商認證快取等。CC 實際有 13+ reason code，其餘見 Deep dive）：

| 模式 | 觸發 | 恢復動作 |
|------|------|---------|
| 輸出截斷 | `max_tokens` | 升級 8K→64K / 續寫提示 |
| 上下文超限 | `prompt_too_long` | reactive compact → 重試 |
| 臨時故障 | 429 / 529 | 指數退避 + 抖動，連續 529 可切換備用模型 |

---

## 工作原理

### 路徑 1: 輸出被截斷

模型話說一半，`max_tokens` 用完了。預設 8000 token 不夠它輸出完整回答。

第一次發生時，直接把 `max_tokens` 從 8K 升級到 64K（8 倍空間），重試同一請求——此時不追加截斷輸出到 messages，保持原始請求不變。如果 64K 還是不夠，才儲存截斷輸出並注入續寫提示讓模型接著剛才的話繼續說，最多 3 次：

```python
if response.stop_reason == "max_tokens":
    # First escalation: don't append truncated output, retry same request
    if not state.has_escalated:
        max_tokens = ESCALATED_MAX_TOKENS
        state.has_escalated = True
        continue  # messages unchanged, same request with more tokens
    # 64K still truncated: save output + continuation prompt
    messages.append({"role": "assistant", "content": response.content})
    if state.recovery_count < MAX_RECOVERY_RETRIES:
        messages.append({"role": "user", "content":
            "Output token limit hit. Resume directly — "
            "no apology, no recap. Pick up mid-thought."})
        state.recovery_count += 1
        continue
    return  # still truncated after 3 continuations
# Normal: append after max_tokens check
messages.append({"role": "assistant", "content": response.content})
```

升級只有一次機會，續寫最多 3 次。超過就退出——繼續續寫也不會有實質產出。

### 路徑 2: 上下文超限

LLM 說"你的上下文太長了"（`prompt_too_long`）。s08 的四層壓縮全跑過了，還是超。

觸發 reactive compact——比 auto compact 更激進。教學版只保留最後 5 條訊息模擬壓縮效果；真實實現會呼叫 LLM 生成 compact 摘要再重試。壓縮後重試。但如果壓縮過一次還是超限，只能退出——再壓縮也不會變小：

```python
except PromptTooLongError:
    if not state.has_attempted_reactive_compact:
        messages[:] = reactive_compact(messages)
        state.has_attempted_reactive_compact = True
        continue
    return  # 壓縮過了還是超限，只能退出
```

### 路徑 3: 臨時故障

網路抖動、429 限流、529 過載——這些不是 bug，是分散式系統的常態。

429 和 529 統一走指數退避 + 抖動：第一次等 0.5 秒，第二次等 1 秒，第三次等 2 秒，最多 10 次。加隨機抖動讓併發請求不在同一時刻重試。連續 3 次 529 過載 → 切換到備用模型（若配置了 `FALLBACK_MODEL_ID` 環境變數）：

```python
def retry_delay(attempt, retry_after=None):
    if retry_after:
        return retry_after
    base = min(500 * (2 ** attempt), 32000) / 1000
    return base + random.uniform(0, base * 0.25)

def with_retry(fn, state, max_retries=10):
    for attempt in range(max_retries):
        try:
            return fn()
        except (RateLimitError, OverloadedError):
            delay = retry_delay(attempt)
            time.sleep(delay)
            if is_overloaded:
                state.consecutive_529 += 1
                if state.consecutive_529 >= 3 and FALLBACK_MODEL:
                    state.current_model = FALLBACK_MODEL
    raise MaxRetriesExceeded()
```

退避公式：`min(500 × 2^attempt, 32000) + random(0~25%)`。如果伺服器返回 `Retry-After` header，優先用那個值。

### 合起來跑

```python
def agent_loop(messages, context):
    system = get_system_prompt(context)
    state = RecoveryState()
    max_tokens = 8000

    while True:
        try:
            response = with_retry(
                lambda: client.messages.create(
                    model=state.current_model, system=system,
                    messages=messages, tools=TOOLS,
                    max_tokens=max_tokens),
                state)
        except Exception as e:
            if is_prompt_too_long_error(e):
                if not state.has_attempted_reactive_compact:
                    messages[:] = reactive_compact(messages)
                    state.has_attempted_reactive_compact = True
                    continue
                return
            log_error(e)
            return

        # max_tokens check BEFORE appending to messages
        if response.stop_reason == "max_tokens":
            if not state.has_escalated:
                max_tokens = 64000
                state.has_escalated = True
                continue  # retry same request, messages unchanged
            # save truncated output + continuation prompt
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": CONTINUATION_PROMPT})
            continue
        # Normal completion
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return
        # ... tool execution ...
```

外層 try/except 捕獲 API 異常（prompt_too_long 等），`with_retry` 處理瞬態錯誤（429/529），`stop_reason` 檢查處理截斷。三種恢復機制各管各的錯誤型別。

---

## 相對 s10 的變更

| 元件 | 之前 (s10) | 之後 (s11) |
|------|-----------|-----------|
| 錯誤處理 | 無（一碰就崩潰） | 三種恢復模式 + 指數退避 |
| 新常量 | — | ESCALATED_MAX_TOKENS=64000, MAX_RETRIES=10, BASE_DELAY_MS=500, FALLBACK_MODEL |
| 新函式 | — | with_retry, retry_delay, reactive_compact, is_prompt_too_long_error, RecoveryState |
| 工具 | bash, read_file, write_file (3) | bash, read_file, write_file (3) — 不變 |
| 迴圈 | 裸呼叫 LLM | try/except 包裹 + continue 重試 |

---

## 試一下

```sh
cd learn-claude-code
python s11_error_recovery/code.py
```

試試這些 prompt：

1. 讓 Agent 生成一段很長的程式碼，觀察截斷後是否自動續寫（看 `[max_tokens] escalating` 日誌）
2. 連續讀取大量檔案撐大上下文，觀察 reactive compact
3. 如果遇到 429/529，觀察指數退避的日誌輸出

---

## 接下來

Agent 現在能在錯誤中自動恢復了。但它處理的任務仍然是"一次性"的——你給它一個任務，它做完，結束。

能不能讓 Agent 管理一個**任務列表**——有依賴關係、持久化到磁碟、跨會話能恢復？TODO 列表不是任務系統。

s12 Task System → 任務是有依賴、有狀態、持久化的圖。這是多 Agent 協作的基礎。

<details>
<summary>深入 CC 原始碼</summary>

> 以下基於 CC 原始碼 `query.ts`（1729 行）、`services/api/withRetry.ts`（822 行）、`query/tokenBudget.ts`（93 行）、`utils/tokenBudget.ts`（73 行）的分析。

### 一、十幾種 reason/transition（不只是 3 條）

教學版講了 3 種最常見的恢復模式。CC 實際有十幾種 reason/transition，每輪 LLM 呼叫後都會判斷：

| reason/transition | 教學版對應 | CC 行為 |
|---|---|---|
| `completed` | 正常完成 | 返回結果 |
| `next_turn` | 正常工具呼叫 | 繼續下一輪工具執行 |
| `max_output_tokens_escalate` | 路徑 1 | 8K→64K 升級 |
| `max_output_tokens_recovery` | 路徑 1 續寫 | 續寫提示（最多 3 次） |
| `reactive_compact_retry` | 路徑 2 | reactive compact → 重試 |
| `prompt_too_long` | 路徑 2 | 同上 |
| `collapse_drain_retry` | 未展開 | context collapse 先提交暫存 |
| `model_error` | 未展開 | 重試 |
| `image_error` | 未展開 | `ImageSizeError` / `ImageResizeError` 專門處理 |
| `aborted_streaming` | 未展開 | 流式中止恢復 |
| `aborted_tools` | 未展開 | 工具中止 |
| `stop_hook_blocking` | 未展開 | 注入 blocking error → 模型自糾 |
| `stop_hook_prevented` | 未展開 | hooks 阻止 |
| `hook_stopped` | 未展開 | hook 停止執行 |
| `token_budget_continuation` | 未展開 | token 用量 < 90% 時繼續 |
| `blocking_limit` | 未展開 | 阻塞限制 |
| `max_turns` | 未展開 | 達到最大輪次 |

教學版只展開了前 5 種（最常見的），其餘各有專門處理邏輯。

### 二、指數退避的精確公式

CC 的退避延遲（`withRetry.ts:530-548`）：

```
delay = min(500 × 2^(attempt-1), 32000) + random(0~25%)
```

| 嘗試 | 基礎延遲 | + 抖動 |
|------|---------|--------|
| 1 | 500ms | 0-125ms |
| 2 | 1000ms | 0-250ms |
| 4 | 4000ms | 0-1000ms |
| 7+ | 32000ms（上限） | 0-8000ms |

如果伺服器返回 `Retry-After` header，優先用那個值。

### 三、CONTINUATION 提示原文

CC 的續寫提示（`query.ts:1225-1227`）：

```
Output token limit hit. Resume directly — no apology, no recap of what
you were doing. Pick up mid-thought if that is where the cut happened.
Break remaining work into smaller pieces.
```

Token budget 的 nudge 提示（`tokenBudget.ts:72`）：

```
Stopped at {pct}% of token target. Keep working — do not summarize.
```

### 四、流式錯誤處理

CC 的流式路徑中，可恢復的錯誤（413、max_tokens、media error）在 streaming 期間**被暫扣不展示**（`query.ts:788-822`）——SDK 消費者看不到，只有恢復邏輯能看到。等 streaming 結束後才判斷是否需要恢復。

### 五、529 → Fallback Model 切換

連續 3 次 529 過載錯誤後（`MAX_529_RETRIES = 3`），CC 自動切換到 fallback model（如 Opus → Sonnet）。切換時清除所有 pending 訊息和 tool 結果，給使用者展示 "Switched to {model} due to high demand"。

### 六、Diminishing Returns 檢測

Token budget 的"繼續"不是無限的。當連續 3 次 continuation 且 token 增量 < 500 時，系統判斷"繼續也沒有實質性產出"，停止 continuation（`tokenBudget.ts:60-62`）。

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
