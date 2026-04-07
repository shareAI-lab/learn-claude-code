# Core Data Structures (主要データ構造マップ)

> agent 学習でいちばん迷いやすいのは、機能の多さそのものではなく、  
> **「今の状態がどの record に入っているのか」が見えなくなること**です。  
> この文書は、主線章と bridge doc に繰り返し出てくる record をひとつの地図として並べ直し、  
> 読者が system 全体を「機能一覧」ではなく「状態の配置図」として理解できるようにするための資料です。

## どう使うか

この資料は辞書というより、`state map` として使ってください。

- 単語の意味が怪しくなったら [`glossary.md`](./glossary.md) へ戻る
- object 同士の境界が混ざったら [`entity-map.md`](./entity-map.md) を開く
- `TaskRecord` と `RuntimeTaskState` が混ざったら [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) を読む
- MCP で tools 以外の layer が混ざったら [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) を併読する

## 最初にこの 2 本だけは覚える

### 原則 1: 内容状態と制御状態を分ける

内容状態とは、system が「何を扱っているか」を表す状態です。

例:

- `messages`
- `tool_result`
- memory の本文
- task の title や description

制御状態とは、system が「次にどう進むか」を表す状態です。

例:

- `turn_count`
- `transition`
- `has_attempted_compact`
- `max_output_tokens_override`
- `pending_classifier_check`

この 2 つを混ぜると、読者はすぐに次の疑問で詰まります。

- なぜ `messages` だけでは足りないのか
- なぜ control plane が必要なのか
- なぜ recovery や compact が別 state を持つのか

### 原則 2: durable state と runtime state を分ける

`durable state` は、session をまたいでも残す価値がある状態です。

例:

- task
- memory
- schedule
- team roster

`runtime state` は、system が動いている間だけ意味を持つ状態です。

例:

- 現在の permission decision
- 今走っている runtime task
- active MCP connection
- 今回の query の continuation reason

この区別が曖昧だと、task・runtime slot・notification・schedule・worktree が全部同じ層に見えてしまいます。

## 1. Query と会話制御の状態

この層の核心は:

> 会話内容を持つ record と、query の進行理由を持つ record は別物である

です。

### `Message`

役割:

- user と assistant の会話履歴を持つ
- tool 呼び出し前後の往復も保存する

最小形:

```python
message = {
    "role": "user" | "assistant",
    "content": "...",
}
```

agent が tool を使い始めると、`content` は単なる文字列では足りなくなり、次のような block list になることがあります。

- text block
- `tool_use`
- `tool_result`

この record の本質は、**会話内容の記録**です。  
「なぜ次ターンへ進んだか」は `Message` の責務ではありません。

関連章:

- `s01`
- `s02`
- `s06`
- `s10`

### `NormalizedMessage`

役割:

- さまざまな内部 message を、model API に渡せる統一形式へ揃える

最小形:

```python
message = {
    "role": "user" | "assistant",
    "content": [
        {"type": "text", "text": "..."},
    ],
}
```

`Message` と `NormalizedMessage` の違い:

- `Message`: system 内部の履歴 record に近い
- `NormalizedMessage`: model 呼び出し直前の入力形式に近い

つまり、前者は「何を覚えているか」、後者は「何を送るか」です。

関連章:

- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

### `CompactSummary`

役割:

- context が長くなり過ぎたとき、古い会話を要約へ置き換える

最小形:

```python
summary = {
    "task_overview": "...",
    "current_state": "...",
    "key_decisions": ["..."],
    "next_steps": ["..."],
}
```

重要なのは、compact が「ログ削除」ではないことです。  
compact summary は次の query 継続に必要な最小構造を残す record です。

最低でも次の 4 つは落とさないようにします。

- task の大枠
- ここまで終わったこと
- 重要な判断
- 次にやるべきこと

関連章:

- `s06`
- `s11`

### `SystemPromptBlock`

役割:

- system prompt を section 単位で管理する

最小形:

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

この record を持つ意味:

- prompt を一枚岩の巨大文字列にしない
- どの section が何の役割か説明できる
- 後から block 単位で差し替えや検査ができる

`cache_scope` は最初は不要でも構いません。  
ただ、「この block は比較的安定」「この block は毎ターン変わる」という発想は早めに持っておくと、system prompt の理解が崩れにくくなります。

関連章:

- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

### `PromptParts`

役割:

- system prompt を最終連結する前に、構成 source ごとに分けて持つ

最小形:

```python
parts = {
    "core": "...",
    "tools": "...",
    "skills": "...",
    "memory": "...",
    "dynamic": "...",
}
```

この record は、読者に次のことを教えます。

- prompt は「書かれている」のではなく「組み立てられている」
- stable policy と volatile runtime data は同じ section ではない
- input source ごとに責務を分けた方が debug しやすい

関連章:

- `s10`

### `QueryParams`

役割:

- query 開始時点で外部から受け取る入口入力

最小形:

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "user_context": {...},
    "system_context": {...},
    "tool_use_context": {...},
    "fallback_model": None,
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

ここで大切なのは:

- これは query の**入口入力**である
- query の途中でどんどん変わる内部状態とは別である

つまり `QueryParams` は「入る前に決まっているもの」、`QueryState` は「入ってから変わるもの」です。

関連章:

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

### `QueryState`

役割:

- 1 本の query が複数ターンにわたって進む間の制御状態を持つ

最小形:

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "turn_count": 1,
    "max_output_tokens_recovery_count": 0,
    "has_attempted_reactive_compact": False,
    "max_output_tokens_override": None,
    "pending_tool_use_summary": None,
    "stop_hook_active": False,
    "transition": None,
}
```

この record に入るものの共通点:

- 対話内容そのものではない
- 「次をどう続けるか」を決める情報である

初心者がよく詰まる点:

- `messages` が入っているので「全部 conversation state に見える」
- しかし `turn_count` や `transition` は会話ではなく control state

この record を理解できると、

- recovery
- compact
- hook continuation
- token budget continuation

がすべて「同じ query を継続する理由の差分」として読めるようになります。

関連章:

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- `s11`

### `TransitionReason`

役割:

- 前ターンが終わらず、次ターンへ続いた理由を明示する

最小形:

```python
transition = {
    "reason": "next_turn",
}
```

より実用的には次のような値が入ります。

- `next_turn`
- `tool_result_continuation`
- `reactive_compact_retry`
- `max_output_tokens_recovery`
- `stop_hook_continuation`

これを別 record として持つ利点:

- log が読みやすい
- test が書きやすい
- recovery の分岐理由を説明しやすい

つまりこれは「高度な最適化」ではなく、  
**継続理由を見える状態へ変えるための最小構造**です。

関連章:

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- `s11`

## 2. Tool 実行・権限・hook の状態

この層の核心は:

> tool は `name -> handler` だけで完結せず、その前後に permission / runtime / hook の状態が存在する

です。

### `ToolSpec`

役割:

- model に「どんな tool があり、どんな入力を受け取るか」を見せる

最小形:

```python
tool = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {...},
}
```

これは execution 実装そのものではありません。  
あくまで **model に見せる contract** です。

関連章:

- `s02`
- `s19`

### `ToolDispatchMap`

役割:

- tool 名を実際の handler 関数へ引く

最小形:

```python
dispatch = {
    "read_file": run_read_file,
    "write_file": run_write_file,
}
```

この record の仕事は単純です。

- 正しい handler を見つける

ただし実システムではこれだけで足りません。  
本当に難しいのは:

- いつ実行するか
- 並列にしてよいか
- permission を通すか
- 結果をどう loop へ戻すか

です。

関連章:

- `s02`
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

### `ToolUseContext`

役割:

- tool が共有状態へ触るための窓口を持つ

最小形:

```python
context = {
    "workspace": "...",
    "permission_system": perms,
    "notifications": queue,
    "memory_store": memory,
}
```

この record がないと、各 tool が勝手に global state を触り始め、system 全体の境界が崩れます。

つまり `ToolUseContext` は、

> tool が system とどこで接続するか

を見える形にするための record です。

関連章:

- `s02`
- `s07`
- `s09`
- `s13`

### `ToolResultEnvelope`

役割:

- tool 実行結果を loop が扱える統一形式で包む

最小形:

```python
result = {
    "tool_use_id": "toolu_123",
    "content": "...",
}
```

大切なのは、tool 結果が「ただの文字列」ではないことです。  
最低でも:

- どの tool call に対する結果か
- loop にどう書き戻すか

を持たせる必要があります。

関連章:

- `s02`

### `PermissionRule`

役割:

- 特定 tool / path / content に対する allow / deny / ask 条件を表す

最小形:

```python
rule = {
    "tool": "bash",
    "behavior": "deny",
    "path": None,
    "content": "sudo *",
}
```

この record があることで、permission system は次を言えるようになります。

- どの tool に対する rule か
- 何にマッチしたら発火するか
- 発火後に何を返すか

関連章:

- `s07`

### `PermissionDecision`

役割:

- 今回の tool 実行に対する permission 結果を表す

最小形:

```python
decision = {
    "behavior": "allow" | "deny" | "ask",
    "reason": "...",
}
```

これを独立 record にする意味:

- deny 理由を model が見える
- ask を loop に戻して次アクションを組み立てられる
- log や UI にも同じ object を流せる

関連章:

- `s07`

### `HookEvent`

役割:

- pre_tool / post_tool / on_error などの lifecycle event を統一形で渡す

最小形:

```python
event = {
    "kind": "post_tool",
    "tool_name": "edit_file",
    "input": {...},
    "result": "...",
    "error": None,
    "duration_ms": 42,
}
```

hook が安定して増やせるかどうかは、この record の形が揃っているかに大きく依存します。

もし毎回適当な文字列だけを hook に渡すと:

- audit hook
- metrics hook
- policy hook

のたびに payload 形式がばらけます。

関連章:

- `s08`

### `ToolExecutionBatch`

役割:

- 同じ execution lane でまとめて調度してよい tool block の束を表す

最小形:

```python
batch = {
    "is_concurrency_safe": True,
    "blocks": [tool_use_1, tool_use_2],
}
```

この record を導入すると、読者は:

- tool を常に 1 個ずつ実行する必要はない
- ただし何でも並列にしてよいわけでもない

という 2 本の境界を同時に理解しやすくなります。

関連章:

- [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)

### `TrackedTool`

役割:

- 各 tool の lifecycle を個別に追う

最小形:

```python
tracked = {
    "id": "toolu_01",
    "name": "read_file",
    "status": "queued",
    "is_concurrency_safe": True,
    "pending_progress": [],
    "results": [],
    "context_modifiers": [],
}
```

これがあると runtime は次のことを説明できます。

- 何が待機中か
- 何が実行中か
- 何が progress を出したか
- 何が完了したか

関連章:

- [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)

### `queued_context_modifiers`

役割:

- 並列 tool が生んだ共有 state 変更を、先に queue し、後で安定順に merge する

最小形:

```python
queued = {
    "toolu_01": [modifier_a],
    "toolu_02": [modifier_b],
}
```

ここで守りたい境界:

- 並列実行してよい
- しかし共有 state を完了順でそのまま書き換えてよいとは限らない

この record は、parallel execution と stable merge を切り分けるための最小構造です。

関連章:

- [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)

## 3. Skill・memory・prompt source の状態

この層の核心は:

> model input の材料は、その場でひとつの文字列に溶けているのではなく、複数の source record として存在する

です。

### `SkillRegistry`

役割:

- 利用可能な skill の索引を持つ

最小形:

```python
registry = [
    {"name": "agent-browser", "path": "...", "description": "..."},
]
```

これは「何があるか」を示す record であり、skill 本文そのものではありません。

関連章:

- `s05`

### `SkillContent`

役割:

- 実際に読み込んだ skill の本文や補助資料を持つ

最小形:

```python
skill = {
    "name": "agent-browser",
    "body": "...markdown...",
}
```

`SkillRegistry` と `SkillContent` を分ける理由:

- registry は discovery 用
- content は injection 用

つまり「見つける record」と「使う record」を分けるためです。

関連章:

- `s05`

### `MemoryEntry`

役割:

- 長期に残すべき事実を 1 件ずつ持つ

最小形:

```python
entry = {
    "key": "package_manager_preference",
    "value": "pnpm",
    "scope": "user",
    "reason": "user explicit preference",
}
```

memory の重要境界:

- 会話全文を残す record ではない
- durable fact を残す record である

関連章:

- `s09`

### `MemoryWriteCandidate`

役割:

- 今回のターンから「long-term memory に昇格させる候補」を一時的に保持する

最小形:

```python
candidate = {
    "fact": "Use pnpm by default",
    "scope": "user",
    "confidence": "high",
}
```

教学 repo では必須ではありません。  
ただし reader が「memory はいつ書くのか」で混乱しやすい場合、この record を挟むと

- その場の conversation detail
- durable fact candidate
- 実際に保存された memory

の 3 層を分けやすくなります。

関連章:

- `s09`

## 4. Todo・task・runtime・team の状態

この層が一番混ざりやすいです。  
理由は、全部が「仕事っぽい object」に見えるからです。

### `TodoItem`

役割:

- 今の session 内での短期的な進行メモ

最小形:

```python
todo = {
    "content": "Inspect auth tests",
    "status": "pending",
}
```

これは durable work graph ではありません。  
今ターンの認知負荷を軽くするための session-local 補助構造です。

関連章:

- `s03`

### `PlanState`

役割:

- 複数の `TodoItem` と current focus をまとめる

最小形:

```python
plan = {
    "todos": [...],
    "current_focus": "Inspect auth tests",
}
```

これも基本は session-local です。  
`TaskRecord` と違って、再起動しても必ず復元したい durable board とは限りません。

関連章:

- `s03`

### `TaskRecord`

役割:

- durable work goal を表す

最小形:

```python
task = {
    "id": "task-auth-migrate",
    "title": "Migrate auth layer",
    "status": "pending",
    "dependencies": [],
}
```

この record が持つべき心智:

- 何を達成したいか
- 依存関係は何か
- 今どの状態か

ここで大切なのは、**task は goal node であって、今まさに走っている process ではない**ことです。

関連章:

- `s12`

### `RuntimeTaskState`

役割:

- いま動いている 1 回の execution slot を表す

最小形:

```python
runtime_task = {
    "id": "rt_42",
    "task_id": "task-auth-migrate",
    "status": "running",
    "preview": "...",
    "output_file": ".runtime-tasks/rt_42.log",
}
```

`TaskRecord` との違い:

- `TaskRecord`: 何を達成するか
- `RuntimeTaskState`: その goal に向かう今回の実行は今どうなっているか

関連章:

- `s13`
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### `NotificationRecord`

役割:

- background 実行や外部 capability から main loop へ戻る preview を持つ

最小形:

```python
note = {
    "source": "runtime_task",
    "task_id": "rt_42",
    "preview": "3 tests failing...",
}
```

この record は全文ログの保存先ではありません。  
役割は:

- main loop に「戻ってきた事実」を知らせる
- prompt space を全文ログで埋めない

ことです。

関連章:

- `s13`

### `ScheduleRecord`

役割:

- いつ何を trigger するかを表す

最小形:

```python
schedule = {
    "name": "nightly-health-check",
    "cron": "0 2 * * *",
    "task_template": "repo_health_check",
}
```

重要な境界:

- `ScheduleRecord` は時間規則
- `TaskRecord` は work goal
- `RuntimeTaskState` は live execution

この 3 つを一緒にしないことが `s14` の核心です。

関連章:

- `s14`

### `TeamMember`

役割:

- 長期に存在する teammate の身元を表す

最小形:

```python
member = {
    "name": "alice",
    "role": "test-specialist",
    "status": "working",
}
```

`TeamMember` は task ではありません。  
「誰が長く system 内に存在しているか」を表す actor record です。

関連章:

- `s15`

### `TeamConfig`

役割:

- team roster 全体をまとめる

最小形:

```python
config = {
    "team_name": "default",
    "members": [member1, member2],
}
```

この record を durable に持つことで、

- team に誰がいるか
- 役割が何か
- 次回起動時に何を復元するか

が見えるようになります。

関連章:

- `s15`

### `MessageEnvelope`

役割:

- teammate 間の message を、本文とメタ情報込みで包む

最小形:

```python
envelope = {
    "type": "message",
    "from": "lead",
    "to": "alice",
    "content": "Review retry tests",
    "timestamp": 1710000000.0,
}
```

`envelope` を使う理由:

- 誰から誰へ送ったか分かる
- 普通の会話と protocol request を区別しやすい
- mailbox を durable channel として扱える

関連章:

- `s15`
- `s16`

### `RequestRecord`

役割:

- approval や shutdown のような構造化 protocol state を持つ

最小形:

```python
request = {
    "request_id": "req_91",
    "kind": "plan_approval",
    "status": "pending",
    "payload": {...},
}
```

これを別 record にすることで、

- ただの chat message
- 追跡可能な coordination request

を明確に分けられます。

関連章:

- `s16`

### `ClaimPolicy`

役割:

- autonomous worker が何を self-claim してよいかを表す

最小形:

```python
policy = {
    "role": "test-specialist",
    "may_claim": ["retry-related"],
}
```

この record がないと autonomy は「空いている worker が勝手に全部取りに行く」設計になりやすく、  
race condition と重複実行を呼び込みます。

関連章:

- `s17`

### `WorktreeRecord`

役割:

- isolated execution lane を表す

最小形:

```python
worktree = {
    "path": ".worktrees/wt-auth-migrate",
    "task_id": "task-auth-migrate",
    "status": "active",
}
```

この record の核心:

- task は goal
- runtime slot は live execution
- worktree は「どこで走るか」の lane

関連章:

- `s18`

## 5. MCP・plugin・外部 capability の状態

この層の核心は:

> 外部 capability も「ただの tool list」ではなく、接続状態と routing を持つ platform object である

です。

### `MCPServerConfig`

役割:

- 外部 server の設定を表す

最小形:

```python
config = {
    "name": "figma",
    "transport": "stdio",
    "command": "...",
}
```

これは capability そのものではなく、接続の入口設定です。

関連章:

- `s19`

### `ConnectionState`

役割:

- remote capability の現在状態を表す

最小形:

```python
state = {
    "status": "connected",
    "needs_auth": False,
    "last_error": None,
}
```

この record が必要な理由:

- 外部 capability は常に使えるとは限らない
- 問題が tool schema なのか connection なのか区別する必要がある

関連章:

- `s19`
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

### `CapabilityRoute`

役割:

- native tool / plugin / MCP server のどこへ解決されたかを表す

最小形:

```python
route = {
    "source": "mcp",
    "target": "figma.inspect",
}
```

この record があると、

- 発見
- routing
- permission
- 実行
- result normalization

が同じ capability bus 上で説明できます。

関連章:

- `s19`

## 最後に、特に混同しやすい組み合わせ

### `TodoItem` vs `TaskRecord`

- `TodoItem`: 今 session で何を見るか
- `TaskRecord`: durable work goal と dependency をどう持つか

### `TaskRecord` vs `RuntimeTaskState`

- `TaskRecord`: 何を達成したいか
- `RuntimeTaskState`: 今回の実行は今どう進んでいるか

### `RuntimeTaskState` vs `ScheduleRecord`

- `RuntimeTaskState`: live execution
- `ScheduleRecord`: いつ trigger するか

### `SubagentContext` vs `TeamMember`

- `SubagentContext`: 一回きりの delegation branch
- `TeamMember`: 長期に残る actor identity

### `TeamMember` vs `RequestRecord`

- `TeamMember`: 誰が存在するか
- `RequestRecord`: どんな coordination request が進行中か

### `TaskRecord` vs `WorktreeRecord`

- `TaskRecord`: 何をやるか
- `WorktreeRecord`: どこでやるか

### `ToolSpec` vs `CapabilityRoute`

- `ToolSpec`: model に見せる contract
- `CapabilityRoute`: 実際にどこへ routing するか

## 読み終えたら言えるべきこと

少なくとも次の 3 文を、自分の言葉で説明できる状態を目指してください。

1. `messages` は内容状態であり、`transition` は制御状態である。
2. `TaskRecord` は goal node であり、`RuntimeTaskState` は live execution slot である。
3. `TeamMember`、`RequestRecord`、`WorktreeRecord` は全部「仕事っぽい」が、それぞれ actor、protocol、lane という別層の object である。

## 一文で覚える

**どの record が内容を持ち、どの record が流れを持ち、どれが durable でどれが runtime かを分けられれば、agent system の複雑さは急に読める形になります。**
