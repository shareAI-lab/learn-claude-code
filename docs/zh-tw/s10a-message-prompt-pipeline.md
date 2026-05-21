# s10a: Message & Prompt Pipeline (訊息與提示詞管道)

> 這篇橋接文件是 `s10` 的擴充套件。  
> 它要補清一個很關鍵的心智：
>
> **system prompt 很重要，但它不是模型完整輸入的全部。**

## 為什麼要補這一篇

`s10` 已經把 system prompt 從“大字串”升級成“可維護的組裝管線”，這一步非常重要。

但當系統開始長出更多輸入來源時，還會繼續往前走一步：

它會發現，真正送給模型的輸入，不只包含：

- system prompt

還包含：

- 規範化後的 messages
- memory attachments
- hook 注入訊息
- system reminder
- 當前輪次的動態上下文

也就是說，真正的輸入更像一條完整管道：

**Prompt Pipeline，而不只是 Prompt Builder。**

## 先解釋幾個名詞

### 什麼是 prompt block

你可以把 `prompt block` 理解成：

> system prompt 內部的一段結構化片段。

例如：

- 核心身份說明
- 工具說明
- memory section
- CLAUDE.md section

### 什麼是 normalized message

`normalized message` 的意思是：

> 把不同來源、不同格式的訊息整理成統一、穩定、可發給模型的訊息形式。

為什麼需要這一步？

因為系統裡可能出現：

- 普通使用者訊息
- assistant 回覆
- tool_result
- 系統提醒
- attachment 包裹訊息

如果不先整理，模型輸入層會越來越亂。

### 什麼是 system reminder

這在 `s10` 已經提到過。

它不是長期規則，而是：

> 只在當前輪或當前階段臨時追加的一小段系統資訊。

## 最小心智模型

把完整輸入先理解成下面這條流水線：

```text
多種輸入來源
  |
  +-- system prompt blocks
  +-- messages
  +-- attachments
  +-- reminders
  |
  v
normalize
  |
  v
final api payload
```

這條圖裡最重要的不是“normalize”這個詞有多高階，而是：

**所有來源先分清邊界，再在最後一步統一整理。**

## system prompt 為什麼不是全部

這是初學者非常容易混的一個點。

system prompt 適合放：

- 身份
- 規則
- 工具能力描述
- 長期說明

但有些東西不適合放進去：

- 這一輪剛發生的 tool_result
- 某個 hook 剛注入的補充說明
- 某條 memory attachment
- 當前臨時提醒

這些更適合存在訊息流裡，而不是塞進 prompt block。

## 關鍵資料結構

### 1. SystemPromptBlock

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

最小教學版可以只理解成：

- 一段文字
- 可選的快取資訊

### 2. PromptParts

```python
parts = {
    "core": "...",
    "tools": "...",
    "skills": "...",
    "memory": "...",
    "claude_md": "...",
    "dynamic": "...",
}
```

### 3. NormalizedMessage

```python
message = {
    "role": "user" | "assistant",
    "content": [...],
}
```

這裡的 `content` 建議直接理解成“塊列表”，而不是隻是一段字串。  
因為後面你會自然遇到：

- text block
- tool_use block
- tool_result block
- attachment-like block

### 4. ReminderMessage

```python
reminder = {
    "role": "system",
    "content": "Current mode: plan",
}
```

教學版裡你不一定真的要用 `system` role 單獨傳，但心智上要區分：

- 這是長期 prompt block
- 還是當前輪臨時 reminder

## 最小實現

### 第一步：繼續保留 `SystemPromptBuilder`

這一步不能丟。

### 第二步：把訊息輸入做成獨立管道

```python
def build_messages(raw_messages, attachments, reminders):
    messages = normalize_messages(raw_messages)
    messages = attach_memory(messages, attachments)
    messages = append_reminders(messages, reminders)
    return messages
```

### 第三步：在最後一層統一生成 API payload

```python
payload = {
    "system": build_system_prompt(),
    "messages": build_messages(...),
    "tools": build_tools(...),
}
```

這一步特別關鍵。

它會讓讀者明白：

**system prompt、messages、tools 是並列輸入面，而不是互相替代。**

## 一張更完整但仍然容易理解的圖

```text
Prompt Blocks
  - core
  - tools
  - memory
  - CLAUDE.md
  - dynamic context

Messages
  - user messages
  - assistant messages
  - tool_result messages
  - injected reminders

Attachments
  - memory attachment
  - hook attachment

          |
          v
   normalize + assemble
          |
          v
     final API payload
```

## 什麼時候該放在 prompt，什麼時候該放在 message

可以先記這個簡單判斷法：

### 更適合放在 prompt block

- 長期穩定規則
- 工具列表
- 長期身份說明
- CLAUDE.md

### 更適合放在 message 流

- 當前輪 tool_result
- 剛發生的提醒
- 當前輪追加的上下文
- 某次 hook 輸出

### 更適合做 attachment

- 大塊但可選的補充資訊
- 需要按需展開的說明

## 初學者最容易犯的錯

### 1. 把所有東西都塞進 system prompt

這樣會讓 prompt 越來越髒，也會模糊穩定資訊和動態資訊的邊界。

### 2. 完全不做 normalize

隨著訊息來源增多，輸入格式會越來越不穩定。

### 3. 把 memory、hook、tool_result 都當成一類東西

它們都能影響模型，但進入輸入層的方式並不相同。

### 4. 忽略“臨時 reminder”這一層

這會讓很多本該只活一輪的資訊，被錯誤地塞進長期 system prompt。

## 它和 `s10`、`s19` 的關係

- `s10` 講 prompt builder
- 這篇講 message + prompt 的完整輸入管道
- `s19` 則會把 MCP 帶來的額外說明和外部能力繼續接入這條管道

也就是說：

**builder 是 prompt 的內部結構，pipeline 是模型輸入的整體結構。**

## 教學邊界

這篇最重要的，不是羅列所有輸入來源，而是先把三條管線邊界講穩：

- 什麼該進 system blocks
- 什麼該進 normalized messages
- 什麼只應該作為臨時 reminder 或 attachment

只要這三層邊界清楚，讀者就已經能自己搭出一條可靠輸入管道。  
更細的 cache scope、attachment 去重和大結果外接，都可以放到後續擴充套件裡再補。

## 一句話記住

**真正送給模型的，不只是一個 prompt，而是“prompt blocks + normalized messages + attachments + reminders”組成的輸入管道。**
