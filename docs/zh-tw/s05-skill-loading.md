# s05: Skills (按需知識載入)

`s00 > s01 > s02 > s03 > s04 > [ s05 ] > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *不是把所有知識永遠塞進 prompt，而是在需要的時候再載入正確那一份。*

## 這一章要解決什麼問題

到了 `s04`，你的 agent 已經會：

- 調工具
- 做會話內規劃
- 把大任務分給子 agent

接下來很自然會遇到另一個問題：

> 不同任務需要的領域知識不一樣。

例如：

- 做程式碼審查，需要一套審查清單
- 做 Git 操作，需要一套提交約定
- 做 MCP 整合，需要一套專門步驟

如果你把這些知識包全部塞進 system prompt，就會出現兩個問題：

1. 大部分 token 都浪費在當前用不到的說明上
2. prompt 越來越臃腫，主線規則越來越不清楚

所以這一章真正要做的是：

**把“長期可選知識”從 system prompt 主體裡拆出來，改成按需載入。**

## 先解釋幾個名詞

### 什麼是 skill

這裡的 `skill` 可以先簡單理解成：

> 一份圍繞某類任務的可複用說明書。

它通常會告訴 agent：

- 什麼時候該用它
- 做這類任務時有哪些步驟
- 有哪些注意事項

### 什麼是 discovery

`discovery` 指“發現有哪些 skill 可用”。

這一層只需要很輕量的資訊，例如：

- skill 名字
- 一句描述

### 什麼是 loading

`loading` 指“把某個 skill 的完整正文真正讀進來”。

這一層才是昂貴的，因為它會把完整內容放進當前上下文。

## 最小心智模型

把這一章先理解成兩層：

```text
第 1 層：輕量目錄
  - skill 名稱
  - skill 描述
  - 讓模型知道“有哪些可用”

第 2 層：按需正文
  - 只有模型真正需要時才載入
  - 透過工具結果注入當前上下文
```

可以畫成這樣：

```text
system prompt
  |
  +-- Skills available:
      - code-review: review checklist
      - git-workflow: branch and commit guidance
      - mcp-builder: build an MCP server
```

當模型判斷自己需要某份知識時：

```text
load_skill("code-review")
   |
   v
tool_result
   |
   v
<skill name="code-review">
完整審查說明
</skill>
```

這就是這一章最核心的設計。

## 關鍵資料結構

### 1. SkillManifest

先準備一份很輕的元資訊：

```python
{
    "name": "code-review",
    "description": "Checklist for reviewing code changes",
}
```

它的作用只是讓模型知道：

> 這份 skill 存在，並且大概是幹什麼的。

### 2. SkillDocument

真正被載入時，再讀取完整內容：

```python
{
    "manifest": {...},
    "body": "... full skill text ...",
}
```

### 3. SkillRegistry

你最好不要把 skill 散著讀取。

更清楚的方式是做一個統一登錄檔：

```python
registry = {
    "code-review": SkillDocument(...),
    "git-workflow": SkillDocument(...),
}
```

它至少要能回答兩個問題：

1. 有哪些 skill 可用
2. 某個 skill 的完整內容是什麼

## 最小實現

### 第一步：把每個 skill 放成一個目錄

最小結構可以這樣：

```text
skills/
  code-review/
    SKILL.md
  git-workflow/
    SKILL.md
```

### 第二步：從 `SKILL.md` 裡讀取最小元資訊

```python
class SkillRegistry:
    def __init__(self, skills_dir):
        self.skills = {}
        self._load_all()

    def _load_all(self):
        for path in skills_dir.rglob("SKILL.md"):
            meta, body = parse_frontmatter(path.read_text())
            name = meta.get("name", path.parent.name)
            self.skills[name] = {
                "manifest": {
                    "name": name,
                    "description": meta.get("description", ""),
                },
                "body": body,
            }
```

這裡的 `frontmatter` 你可以先簡單理解成：

> 放在正文前面的一小段結構化後設資料。

### 第三步：把 skill 目錄放進 system prompt

```python
SYSTEM = f"""You are a coding agent.
Skills available:
{SKILL_REGISTRY.describe_available()}
"""
```

注意這裡放的是**目錄資訊**，不是完整正文。

### 第四步：提供一個 `load_skill` 工具

```python
TOOL_HANDLERS = {
    "load_skill": lambda **kw: SKILL_REGISTRY.load_full_text(kw["name"]),
}
```

當模型呼叫它時，把完整 skill 正文作為 `tool_result` 返回。

### 第五步：讓 skill 正文只在當前需要時進入上下文

這一步的核心思想就是：

> 平時只展示“有哪些知識包”，真正工作時才把那一包展開。

## skill、memory、CLAUDE.md 的邊界

這三個概念很容易混。

### skill

可選知識包。  
只有在某類任務需要時才載入。

### memory

跨會話仍然有價值的資訊。  
它是系統記住的東西，不是任務手冊。

### CLAUDE.md

更穩定、更長期的規則說明。  
它通常比單個 skill 更“全域性”。

一個簡單判斷法：

- 這是某類任務才需要的做法或知識：`skill`
- 這是需要長期記住的事實或偏好：`memory`
- 這是更穩定的全域性規則：`CLAUDE.md`

## 它如何接到主迴圈裡

這一章以後，system prompt 不再只是一段固定身份說明。

它開始長出一個很重要的新段落：

- 可用技能目錄

而訊息流裡則會出現新的按需注入內容：

- 某個 skill 的完整正文

也就是說，系統輸入現在開始分成兩層：

```text
穩定層：
  身份、規則、工具、skill 目錄

按需層：
  當前真的載入進來的 skill 正文
```

這也是 `s10` 會繼續系統化展開的東西。

## 初學者最容易犯的錯

### 1. 把所有 skill 正文永遠塞進 system prompt

這樣會讓 prompt 很快臃腫到難以維護。

### 2. skill 目錄資訊寫得太弱

如果只有名字，沒有描述，模型就不知道什麼時候該載入它。

### 3. 把 skill 當成“絕對規則”

skill 更像“可選工作手冊”，不是所有輪次都必須用。

### 4. 把 skill 和 memory 混成一類

skill 解決的是“怎麼做一類事”，memory 解決的是“記住長期事實”。

### 5. 一上來就講太多多源載入細節

教學主線真正要先講清的是：

**輕量發現，重內容按需載入。**

## 教學邊界

這章只要先守住兩層就夠了：

- 輕量發現：先告訴模型有哪些 skill
- 按需深載入：真正需要時再把正文放進輸入

所以這裡不用提前擴到：

- 多來源收集
- 條件啟用
- skill 引數化
- fork 式執行
- 更復雜的 prompt 管道拼裝

如果讀者已經明白“為什麼不能把所有 skill 永遠塞進 system prompt，而應該先列目錄、再按需載入”，這章就已經講到位了。

## 一句話記住

**Skill 系統的核心，不是“多一個工具”，而是“把可選知識從常駐 prompt 裡拆出來，改成按需載入”。**
