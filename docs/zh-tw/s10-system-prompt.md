# s10: System Prompt Construction (系統提示詞構建)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > [ s10 ] > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *系統提示詞不是一整塊大字串，而是一條可維護的組裝流水線。*

## 這一章為什麼重要

很多初學者一開始會把 system prompt 寫成一大段固定文字。

這樣在最小 demo 裡當然能跑。

但一旦系統開始長功能，你很快會遇到這些問題：

- 工具列表會變
- skills 會變
- memory 會變
- 當前目錄、日期、模式會變
- 某些提醒只在這一輪有效，不該永遠塞進系統說明

所以到了這個階段，system prompt 不能再當成一塊硬編碼文字。

它應該升級成：

**由多個來源共同組裝出來的一條流水線。**

## 建議聯讀

- 如果你還習慣把 prompt 看成“神秘大段文字”，先回 [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)，重新確認模型輸入在進模型前經歷了哪些控制層。
- 如果你想真正穩住“哪些內容先拼、哪些後拼”，建議把 [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) 放在手邊，這頁就是本章最關鍵的橋。
- 如果你開始把 system rules、工具說明、memory、runtime state 混成一個大塊，先看 [`data-structures.md`](./data-structures.md)，把這些輸入片段的來源重新拆開。

## 先解釋幾個名詞

### 什麼是 system prompt

system prompt 是給模型的系統級說明。

它通常負責告訴模型：

- 你是誰
- 你能做什麼
- 你應該遵守什麼規則
- 你現在處在什麼環境裡

### 什麼是“組裝流水線”

意思是：

- 不同資訊來自不同地方
- 最後按順序拼接成一份輸入

它不是一個死字串，而是一條構建過程。

### 什麼是動態資訊

有些資訊經常變化，例如：

- 當前日期
- 當前工作目錄
- 本輪新增的提醒

這些資訊不適合和所有穩定說明混在一起。

## 最小心智模型

最容易理解的方式，是把 system prompt 想成 6 段：

```text
1. 核心身份和行為說明
2. 工具列表
3. skills 元資訊
4. memory 內容
5. CLAUDE.md 指令鏈
6. 動態環境資訊
```

然後按順序拼起來：

```text
core
+ tools
+ skills
+ memory
+ claude_md
+ dynamic_context
= final system prompt
```

## 為什麼不能把所有東西都硬塞進一個大字串

因為這樣會有三個問題：

### 1. 不好維護

你很難知道：

- 哪一段來自哪裡
- 該修改哪一部分
- 哪一段是固定說明，哪一段是臨時上下文

### 2. 不好測試

如果 system prompt 是一大坨文字，你很難分別測試：

- 工具說明生成得對不對
- memory 是否被正確拼進去
- CLAUDE.md 是否被正確讀取

### 3. 不好做快取和動態更新

一些穩定內容其實不需要每輪大變。  
一些臨時內容又只該活一輪。

這就要求你把“穩定塊”和“動態塊”分開思考。

## 最小實現結構

### 第一步：做一個 builder

```python
class SystemPromptBuilder:
    def build(self) -> str:
        parts = []
        parts.append(self._build_core())
        parts.append(self._build_tools())
        parts.append(self._build_skills())
        parts.append(self._build_memory())
        parts.append(self._build_claude_md())
        parts.append(self._build_dynamic())
        return "\n\n".join(p for p in parts if p)
```

這就是這一章最核心的設計。

### 第二步：每一段只負責一種來源

例如：

- `_build_tools()` 只負責把工具說明生成出來
- `_build_memory()` 只負責拿 memory
- `_build_claude_md()` 只負責讀指令檔案

這樣每一段的職責就很清楚。

## 這一章最關鍵的結構化邊界

### 邊界 1：穩定說明 vs 動態提醒

最重要的一組邊界是：

- 穩定的系統說明
- 每輪臨時變化的提醒

這兩類東西不應該混為一談。

### 邊界 2：system prompt vs system reminder

system prompt 適合放：

- 身份
- 規則
- 工具
- 長期約束

system reminder 適合放：

- 這一輪才臨時需要的補充上下文
- 當前變動的狀態

所以更清晰的做法是：

- 主 system prompt 保持相對穩定
- 每輪額外變化的內容，用單獨的 reminder 方式追加

## 一個實用的教學版本

教學版可以先這樣分：

```text
靜態部分：
- core
- tools
- skills
- memory
- CLAUDE.md

動態部分：
- date
- cwd
- model
- current mode
```

如果你還想再清楚一點，可以加一個邊界標記：

```text
=== DYNAMIC_BOUNDARY ===
```

它的作用不是神秘魔法。

它只是提醒你：

**上面更穩定，下面更容易變。**

## CLAUDE.md 為什麼要單獨一段

因為它的角色不是“某一次任務的臨時上下文”，而是更穩定的長期說明。

教學倉裡，最容易理解的鏈條是：

1. 使用者全域性級
2. 專案根目錄級
3. 當前子目錄級

然後全部拼進去，而不是互相覆蓋。

這樣讀者更容易理解“規則來源可以分層疊加”這個思想。

## memory 為什麼要和 system prompt 有關係

因為 memory 的本質是：

**把跨會話仍然有價值的資訊，重新帶回模型當前的工作環境。**

如果儲存了 memory，卻從來不在系統輸入中重新呈現，那它就等於沒被真正用起來。

所以 memory 最終一定要進入 prompt 組裝鏈條。

## 初學者最容易混淆的點

### 1. 把 system prompt 講成一個固定字串

這會讓讀者看不到系統是如何長大的。

### 2. 把所有變化資訊都塞進 system prompt

這會把穩定說明和臨時提醒攪在一起。

### 3. 把 CLAUDE.md、memory、skills 寫成同一種東西

它們都可能進入 prompt，但來源和職責不同：

- `skills`：可選能力或知識包
- `memory`：跨會話記住的資訊
- `CLAUDE.md`：長期規則說明

## 教學邊界

這一章先只建立一個核心心智：

**prompt 不是一整塊靜態文字，而是一條被逐段組裝出來的輸入流水線。**

所以這裡先不要擴到太多外層細節：

- 不要先講複雜的 section 註冊系統
- 不要先講快取與預算
- 不要先講所有外部能力如何追加 prompt 說明

只要讀者已經能把穩定規則、動態提醒、memory、skills 這些來源看成不同輸入段，而不是同一種“大 prompt”，這一章就已經講到位了。

## 如果你開始分不清 prompt、message、reminder

這是非常正常的。

因為到了這一章，系統輸入已經不再只有一個 system prompt 了。  
它至少會同時出現：

- system prompt blocks
- 普通對話訊息
- tool_result 訊息
- memory attachment
- 當前輪 reminder

如果你開始有這類困惑：

- “這個資訊到底該放 prompt 裡，還是放 message 裡？”
- “為什麼 system prompt 不是全部輸入？”
- “reminder 和長期規則到底差在哪？”

建議繼續看：

- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)
- [`entity-map.md`](./entity-map.md)

## 這章和後續章節的關係

這一章像一個匯合點：

- `s05` skills 會匯進來
- `s09` memory 會匯進來
- `s07` 的當前模式也可能匯進來
- `s19` MCP 以後也可能給 prompt 增加說明

所以 `s10` 的價值不是“新加一個功能”，  
而是“把前面長出來的功能組織成一份清楚的系統輸入”。

## 學完這章後，你應該能回答

- 為什麼 system prompt 不能只是一整塊硬編碼文字？
- 為什麼要把不同來源拆成獨立 section？
- system prompt 和 system reminder 的邊界是什麼？
- memory、skills、CLAUDE.md 為什麼都可能進入 prompt，但又不是一回事？

---

**一句話記住：system prompt 的關鍵不是“寫一段很長的話”，而是“把不同來源的資訊按清晰邊界組裝起來”。**
