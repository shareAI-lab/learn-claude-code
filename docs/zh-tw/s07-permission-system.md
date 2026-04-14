# s07: Permission System (許可權系統)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > [ s07 ] > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *模型可以提出行動建議，但真正執行之前，必須先過安全關。*

## 這一章的核心目標

到了 `s06`，你的 agent 已經能讀檔案、改檔案、跑命令、做規劃、壓縮上下文。

問題也隨之出現了：

- 模型可能會寫錯檔案
- 模型可能會執行危險命令
- 模型可能會在不該動手的時候動手

所以從這一章開始，系統需要一條新的管道：

**“意圖”不能直接變成“執行”，中間必須經過許可權檢查。**

## 建議聯讀

- 如果你開始把“模型提議動作”和“系統真的執行動作”混成一件事，先回 [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)，重新確認 query 是怎麼進入控制面的。
- 如果你還沒徹底穩住“工具請求為什麼不能直接落到 handler”，建議把 [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) 放在手邊一起讀。
- 如果你在 `PermissionRule / PermissionDecision / tool_result` 這幾層物件上開始打結，先回 [`data-structures.md`](./data-structures.md)，把狀態邊界重新拆開。

## 先解釋幾個名詞

### 什麼是許可權系統

許可權系統不是“有沒有許可權”這樣一個布林值。

它更像一條管道，用來回答：

1. 這次呼叫要不要直接拒絕？
2. 能不能自動放行？
3. 剩下的要不要問使用者？

### 什麼是許可權模式

許可權模式是系統當前的總體風格。

例如：

- 謹慎一點：大多數操作都問使用者
- 保守一點：只允許讀，不允許寫
- 流暢一點：簡單安全的操作自動放行

### 什麼是規則

規則就是“遇到某種工具呼叫時，該怎麼處理”的小條款。

最小規則通常包含三部分：

```python
{
    "tool": "bash",
    "content": "sudo *",
    "behavior": "deny",
}
```

意思是：

- 針對 `bash`
- 如果命令內容匹配 `sudo *`
- 就拒絕

## 最小許可權系統應該長什麼樣

如果你是從 0 開始手寫，一個最小但正確的許可權系統只需要四步：

```text
tool_call
  |
  v
1. deny rules     -> 命中了就拒絕
  |
  v
2. mode check     -> 根據當前模式決定
  |
  v
3. allow rules    -> 命中了就放行
  |
  v
4. ask user       -> 剩下的交給使用者確認
```

這四步已經能覆蓋教學倉庫 80% 的核心需要。

## 為什麼順序是這樣

### 第 1 步先看 deny rules

因為有些東西不應該交給“模式”去決定。

比如：

- 明顯危險的命令
- 明顯越界的路徑

這些應該優先擋掉。

### 第 2 步看 mode

因為模式決定當前會話的大方向。

例如在 `plan` 模式下，系統就應該天然更保守。

### 第 3 步看 allow rules

有些安全、重複、常見的操作可以直接過。

比如：

- 讀檔案
- 搜尋程式碼
- 檢視 git 狀態

### 第 4 步才 ask

前面都沒命中的灰區，才交給使用者。

## 推薦先實現的 3 種模式

不要一上來就做特別多模式。  
先把下面三種做穩：

| 模式 | 含義 | 適合什麼場景 |
|---|---|---|
| `default` | 未命中規則時問使用者 | 日常互動 |
| `plan` | 只允許讀，不允許寫 | 計劃、審查、分析 |
| `auto` | 簡單安全操作自動過，危險操作再問 | 高流暢度探索 |

先有這三種，你就已經有了一個可用的許可權系統。

## 這一章最重要的資料結構

### 1. 許可權規則

```python
PermissionRule = {
    "tool": str,
    "behavior": "allow" | "deny" | "ask",
    "path": str | None,
    "content": str | None,
}
```

你不一定一開始就需要 `path` 和 `content` 都支援。  
但規則至少要能表達：

- 針對哪個工具
- 命中後怎麼處理

### 2. 許可權模式

```python
mode = "default" | "plan" | "auto"
```

### 3. 許可權決策結果

```python
{
    "behavior": "allow" | "deny" | "ask",
    "reason": "why this decision was made"
}
```

這三個結構已經足夠搭起最小系統。

## 最小實現怎麼寫

```python
def check_permission(tool_name: str, tool_input: dict) -> dict:
    # 1. deny rules
    for rule in deny_rules:
        if matches(rule, tool_name, tool_input):
            return {"behavior": "deny", "reason": "matched deny rule"}

    # 2. mode
    if mode == "plan" and tool_name in WRITE_TOOLS:
        return {"behavior": "deny", "reason": "plan mode blocks writes"}
    if mode == "auto" and tool_name in READ_ONLY_TOOLS:
        return {"behavior": "allow", "reason": "auto mode allows reads"}

    # 3. allow rules
    for rule in allow_rules:
        if matches(rule, tool_name, tool_input):
            return {"behavior": "allow", "reason": "matched allow rule"}

    # 4. fallback
    return {"behavior": "ask", "reason": "needs confirmation"}
```

然後在執行工具前接進去：

```python
decision = perms.check(tool_name, tool_input)

if decision["behavior"] == "deny":
    return f"Permission denied: {decision['reason']}"
if decision["behavior"] == "ask":
    ok = ask_user(...)
    if not ok:
        return "Permission denied by user"

return handler(**tool_input)
```

## Bash 為什麼值得單獨講

所有工具裡，`bash` 通常最危險。

因為：

- `read_file` 只能讀檔案
- `write_file` 只能寫檔案
- 但 `bash` 幾乎能做任何事

所以你不能只把 bash 當成一個普通字串。

一個更成熟的系統，通常會把 bash 當成一門小語言來檢查。

哪怕教學版不做完整語法分析，也建議至少先擋住這些明顯危險點：

- `sudo`
- `rm -rf`
- 命令替換
- 可疑重定向
- 明顯的 shell 元字元拼接

這背後的核心思想只有一句：

**bash 不是普通文字，而是可執行動作描述。**

## 初學者怎麼把這章做對

### 第一步：先做 3 個模式

不要一開始就做 6 個模式、10 個來源、複雜 classifier。

先穩穩做出：

- `default`
- `plan`
- `auto`

### 第二步：先做 deny / allow 兩類規則

這已經足夠表達很多現實需求。

### 第三步：給 bash 加最小安全檢查

哪怕只是模式匹配版，也比完全裸奔好很多。

### 第四步：加拒絕計數

如果 agent 連續多次被拒絕，說明它可能卡住了。

這時可以：

- 給出提示
- 建議切到 `plan`
- 讓使用者重新澄清目標

## 教學邊界

這一章先只講透一條許可權管道就夠了：

- 工具意圖先進入許可權判斷
- 許可權結果只分成 `allow / ask / deny`
- 透過以後才真的執行

先把這條主線做穩，比一開始塞進很多模式名、規則來源、寫回配置、額外目錄、自動分類器都更重要。

換句話說，這章要先讓讀者真正理解的是：

**任何工具呼叫，都不應該直接執行；中間必須先過一條許可權管道。**

## 這章不應該講太多什麼

為了不打亂初學者心智，這章不應該過早陷入：

- 企業策略源的全部優先順序
- 非常複雜的自動分類器
- 產品環境裡的所有無頭模式細節
- 某個特定生產程式碼裡的全部 validator 名稱

這些東西存在，但不屬於第一層理解。

第一層理解只有一句話：

**任何工具呼叫，都不應該直接執行；中間必須先過一條許可權管道。**

## 這一章和後續章節的關係

- `s07` 決定“能不能執行”
- `s08` 決定“執行前後還能不能插入額外邏輯”
- `s10` 會把當前模式和許可權說明放進 prompt 組裝裡

所以這章是後面很多機制的安全前提。

## 學完這章後，你應該能回答

- 為什麼許可權系統不是一個簡單開關？
- 為什麼 deny 要先於 allow？
- 為什麼要先做 3 個模式，而不是一上來做很複雜？
- 為什麼 bash 要被特殊對待？

---

**一句話記住：許可權系統不是為了讓 agent 更笨，而是為了讓 agent 的行動先經過一道可靠的安全判斷。**
