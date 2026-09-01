# s15: Integrated Harness — 多くの仕組みを 1 つのループへ

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s13 → [s14](../s14_mcp_plugin/) → `s15` → [s16](../s16_workflow_runtime/) → s17

> *"仕組みは多い、ループは 1 つ"* — tools、permissions、memory、tasks、teams、plugins はすべて同じ `while True` に接続される。
>
> **Harness レイヤー**: 統合 — この例で実際に使う仕組みを 1 つの実行可能なシステムへまとめる。

---

## 問題

前の章では、異なる仕組みをそれぞれ独立した実行例に置いた。本章では、統合ランタイムに必要な仕組みを接続する。

長時間動く coding agent には、同時に次のものが必要になる：

- tool dispatch と permission boundary
- hook extension point
- todo plan と task graph
- skill、memory、runtime system prompt assembly
- compaction と error recovery
- background task と cron scheduling
- team、protocol、IDLE task claiming
- task-bound worktree
- MCP external tool integration

S15 は新しい独立 mechanism を追加する章ではない。既存の mechanism が model loop のどこに入り、そこで生じた event が同じ conversation にどう戻るかを示す。

---

## 解決策

![System Architecture](images/system-architecture.ja.svg)

S15 は新しい mechanism を追加せず、前章までの component を同じ harness に統合する：

```text
user input
  → UserPromptSubmit hooks
  → cron/background notification injection
  → context compact
  → memory + skills + MCP state で system prompt を組み立てる
  → LLM
  → has tool_use block?
      no  → Stop hooks → return
      yes → PreToolUse hooks + permission
          → TOOL_HANDLERS / MCP handlers / background dispatch
          → PostToolUse hooks
          → tool_result / task_notification を messages へ戻す
          → next round
```

loop 自体は同じ構造のままだ。model を呼び、response に `tool_use` block があるかを見て、tool を実行し、結果を `messages` に戻す。tool 実行を続けるかどうかは、実際の `tool_use` block の有無で決まる。

---

## 各 Component の位置

| 位置 | Component | 役割 |
|------|-----------|------|
| user input 周辺 | `UserPromptSubmit` hooks | user input の記録、注入、監査 |
| LLM 前 | cron queue | scheduled prompt を `messages` へ注入 |
| LLM 前 | background notifications | 完了した background work を `<task_notification>` として注入 |
| LLM 前 | compaction pipeline | 大きな出力を予算化し、履歴を切り、古い tool_result を圧縮し、必要なら要約 |
| LLM 前 | memory / skills / MCP state | current capabilities と long-term context を system prompt に組み込む |
| LLM call | error recovery | 429/529 retry、`max_tokens` escalation、prompt-too-long compact |
| tool 実行前 | `PreToolUse` hooks + permission | 危険な command、範囲外 write、destructive MCP tool を止める |
| tool dispatch | `assemble_tool_pool` | built-in tools と dynamic MCP tools を組み立てる |
| tool 実行中 | background dispatch | 明示指定された bash work を daemon thread に移し、placeholder result を返す |
| tool 実行後 | `PostToolUse` hooks | large-output warning、log、後処理 |
| loop へ戻る | tool_result | 1 つの `tool_use` に 1 つの `tool_result`、そして次の model round |
| tool_use がない round / stop 時 | `Stop` hooks | 統計、cleanup、audit |

---

## code.py に含まれるもの

### Tools と Dispatch

built-in tool pool には 26 個の tool がある：

```text
bash, read_file, write_file, edit_file, glob
todo_write, task, load_skill, compact
create_task, update_task, list_tasks, get_task, claim_task, complete_task
schedule_cron, list_crons, cancel_cron
spawn_teammate, list_teammates, send_message
request_shutdown, request_plan, review_plan
create_worktree
connect_mcp
```

`assemble_tool_pool()` は毎 round で次を組み立てる：

```text
BUILTIN_TOOLS + connected MCP tools
BUILTIN_HANDLERS + mcp__server__tool handlers
```

`connect_mcp("docs")` のあと、次の round では `mcp__docs__search` のような tool が出現する。

### Permission と Hooks

permission は tool 実行行に直接埋め込まない。`PreToolUse` hook として扱う：

```python
blocked = trigger_hooks("PreToolUse", block)
if blocked:
    results.append(tool_result(block.id, blocked))
    continue
```

これにより permission、logging、audit が同じ hook point に接続できる。Lead、one-shot subagent、teammate の tool はすべて先に `PreToolUse` を通り、許可された call は handler 実行後に `PostToolUse` を通る。

permission 判定では、MCP server 自身の description を authorization の根拠にしない。host が既知の read-only call の exact allowlist を持ち、それ以外の MCP tool は user に確認する。file tool が `WORKDIR` の外へ出る場合は拒否し、すべての bash command は実行前に確認する。interactive approval を開けるのは foreground user turn だけで、asynchronous turn は main CLI と stdin を奪い合わず fail closed する。

### Plan と Task

S15 には 2 層の plan がある：

- `todo_write`: current session 用の軽量 plan。メモリに保持。
- task graph: cross-session、dependency-aware、claimable な task file。`.tasks/task_*.json` に保存。

前者は単独 agent の drift を防ぐ。後者は team coordination の土台になる。

目的は近いが実装は別である。`todo_write` は現在のセッションのチェックリスト全体を置き換え、task record は安定 ID と個別のライフサイクル更新を持つ。次節の独立した `task` ツールは「隔離 subagent を一度派遣する」意味であり、Task System ではない。

統合 host でもタスクグラフは 2 段階で構築する。Lead はまず全タスクノードを作成し、`create_task` が返した実行時 ID で `update_task` を呼ぶ。チームメイトが使えるのは一覧・Claim・完了だけなので、依存構造は仕事を配る前に Lead が確定する。

### Subagent と Team

S15 には 2 種類の delegation がある：

- `task`: one-shot subagent。独立した `messages[]` を使い、中間 context を捨て、final summary だけ返す。
- `spawn_teammate`: persistent teammate thread。ready `task_id` を渡すと、runtime は thread 開始前に Claim する。省略した場合、teammate は IDLE で後続 Task を待てる。assignment がない teammate は file tool と Shell tool を使えない。固定の tool round 上限なしで `WORK → result → IDLE` を続け、model または dispatch の失敗は `error` を送り、thread cleanup は未完了 assignment を task board へ戻す。model call の前には毎回 inbox を読み、direct message や shutdown request が連続する tool-use round の後ろで待ち続けないようにする。idle 中はまず `MessageBus` を待ち、timeout 後だけ ready task を scan して最大 1 件を atomic に claim する。

Lead は teammate を起動した後、model loop 内で status を繰り返し確認せず、現在の turn を終了する。Lead の受信箱に team event が入ると runtime が次の turn を開始する。

one-shot subagent は context isolation を解決する。persistent teammate は長期並列協作を解決する。

どちらの child tool pool にも `task` と `spawn_teammate` は含まれないため、s15 child は child を再帰的に生成できず、topology は Root → one-shot または teammate となる。s15 に teammate 総数の数値 cap はなく、unique name と host resource が制約になる。one-shot は parent tool call 内で同期実行され、teammate daemon thread は相互にも Lead とも overlap できる。child は Lead conversation を継承しない。one-shot は assigned description と `SUB_SYSTEM` だけを受け取り、teammate は assignment と private message history を持つ。model client、hooks、task/message store、workspace policy は共有し、one-shot は `task` tool result、teammate は `MessageBus` event で結果を返す。

### Memory、Skills、Prompt

S15 は s09 の Memory runtime をそのまま再利用する。model call の前に `.memory/MEMORY.md` catalog を読み、現在の request に関係する record を選び、その本文を `assemble_system_prompt(context)` へ渡す。turn の終了後は `extract_memories()` が後の session でも使える情報を保存し、新しい record が増えた場合は `consolidate_memories()` を続けて実行する。

同じ system prompt には identity、tool guidance、workspace、skills catalog、connected MCP servers も入る。skills は catalog だけを置き、全文は `load_skill(name)` で必要な時に読む。

### Compaction と Recovery

LLM call の前に compaction pipeline を走らせる：

```text
tool_result_budget → snip_compact → micro_compact → compact_history
```

`snip_compact` は中間メッセージを切る前に完全な履歴を保存する。`micro_compact` はコンテキストが上限を超えた場合にだけ実行し、古い既読結果を保存して復元パスへ置き換え、最新 3 件を完全に保ち、上限の約 80% で停止する。未読の新しい結果自体が大きすぎる場合、S15 は履歴要約を検討する前に preview と完全な出力へのパスを残す。

model call は recovery で包む：

- 429: exponential backoff retry
- 529: exponential backoff、連続失敗時は fallback model へ切替可能
- `max_tokens`: max tokens を上げ、その後 continuation を要求
- prompt too long: reactive compact 後に retry

### Background と Cron

bash call が `run_in_background=true` を指定すると、main loop は command の終了を待たず placeholder を返す：

```text
should_run_background → start_background_task → placeholder tool_result
background done → task_notification → next round injects messages
```

background path に入るのは明示的に指定された bash call だけである。command の非ゼロ終了や worker の例外は `failed` notification になる。各 Shell command は独立した process group で動き、command の終了、または Agent が通常経路や `SIGTERM` で終了する時に元の group を停止する。別の session を作った process はその group から離れられる。

cron scheduler は daemon thread として動き、1 秒ごとに確認する。durable な一回限り job は、先に `pending_delivery` として永続化してから queue へ入れ、その prompt を含む model call が成功するまで保持する。呼び出し失敗時と restart 後には再び queue に入るため、配信は at-least-once である。CLI は `cron_queue`、Lead inbox、終了した background work を監視し、どの event からでも Agent を 1 turn 自動で起動する。

### Worktree と MCP

s13 から継承した task-scoped worktree は working directory を管理する：

- pending かつ unowned の task は main workspace のままでもよく、`create_worktree(name, task_id)` で別々の branch と directory に紐付けることもできる
- 作成前に task、name、path、branch、Git registry を検証する。Git command が失敗した後も registry と branch state を照合し、部分的に作成された checkout は未紐付けのまま manual recovery 用に保持する
- idle teammate は ready task を 1 つ atomic に claim し、assignment は `task_id` と effective `cwd` の両方を保持する
- Lead は ready `task_id` を `spawn_teammate` に直接渡すこともでき、Claim 成功後にだけ thread が開始する
- teammate のすべての file tool はその `cwd` を使い、task owner だけが complete できる。assignment は current model turn の終了まで保持する
- 削除は host 側の `remove_worktree()` helper に残し、モデルからは呼べない。user または host が task ownership、assignment lease、background work、Git state を先に確認し、破壊的な削除には別途 user confirmation を必要とする

worktree は tool の default working directory を変更して working copy を分離するだけで、sandbox ではない。process group cleanup は別の session を作った process を封じ込められないため、削除は host-owned のままにする。

Task の Claim または release は assignment version を変え、古い plan approval を無効にする。通常の `send_message` は text を配信するだけで、Task identity も plan state も変えない。

MCP は external capability を担当する：

- `connect_mcp(name)` が mock server に接続する
- `assemble_tool_pool()` が MCP tools を tool pool に組み立て、正規化後の名前衝突を拒否する
- tool name は `mcp__server__tool` 形式に統一する

---

## 構造化 execution trace

s15 と s16 の CLI は process ごとに 1 つの JSONL trace を生成する。module を import するだけでは file を作らない。既定で有効で、environment variable で設定できる：

```sh
HARNESS_TRACE=1
HARNESS_TRACE_DIR=traces
HARNESS_TRACE_OUTPUT=summary       # summary または full
HARNESS_TRACE_PREVIEW_CHARS=500
python s15_integrated_harness/code.py
```

各 record は wall-clock/monotonic time、run/turn/agent ID、parent agent、span/causal ID、thread、event name、data を持つ。`model_request → model_response`、outer `tool_start → tool_end`、inner `tool_execution_start → tool_execution_end`、`agent_start → agent_end`、context、background task、permission wait、workflow node の境界は同じ `span_id` で対応する。tool arguments の credential は再帰的に redaction される。result、prompt、task、message は既定では上限付き preview、文字数、SHA-256 のみを保存する。model event は action type、tool name、stop reason、latency、provider が返した token usage を記録するが、hidden reasoning content は保存しない。

```sh
python s15_integrated_harness/trace_view.py traces/run_....jsonl
python s15_integrated_harness/trace_view.py --view tree
python s15_integrated_harness/trace_view.py --view timeline --width 120
python s15_integrated_harness/trace_view.py --view metrics
```

viewer は agent tree、parallel timeline、model/tool call 数、tool 別集計、subagent/cache 数、最大 depth、最大同時 active agent 数、token、model/tool time、workflow semaphore と agent-launch wait、human wait、概算 orchestration overhead を表示する。`tool_time_ms` は handler execution だけを測定し、permission wait と内部 child work の重複を除外する。`model_time_ms` は client が観測した provider latency であり、network、server queue、inference を含む。pure GPU inference を分離するには vLLM server metrics が必要である。並列実行では合計時間が wall time を超え得るため、重複を merge した `*_wall_time_ms` も出力する。

trace が示すのは実際に実行された plan であり、chain-of-thought ではない。model は text か `tool_use` か、tool/arguments、delegation を決める。deterministic harness code は permission、dispatch、thread scheduling、task/message state、context compaction、retry、stopping condition を決める。

## Remote vLLM で Qwen/Qwen3.8-27B を使う

`Qwen/Qwen3.8-27B` は公式 Hugging Face model ID である。最小変更は Anthropic SDK を維持し、vLLM 0.17.0 以降の Anthropic-compatible `/v1/messages` endpoint に向けること：

```sh
vllm serve Qwen/Qwen3.8-27B \
  --host 0.0.0.0 --port 8000 \
  --served-model-name Qwen/Qwen3.8-27B \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder
```

Harness host の `.env`：

```dotenv
ANTHROPIC_API_KEY=EMPTY
ANTHROPIC_BASE_URL=http://your-vllm-host:8000
MODEL_ID=Qwen/Qwen3.8-27B
```

vLLM server を `--api-key YOUR_TOKEN` 付きで起動する場合は、`ANTHROPIC_API_KEY` を空にして `ANTHROPIC_AUTH_TOKEN=YOUR_TOKEN` を設定する。Anthropic SDK は vLLM の保護された `/v1/messages` endpoint が要求する `Authorization: Bearer YOUR_TOKEN` を送信する。

agent loop に Qwen 専用 branch は不要で、現在の runtime は streaming も使わない。s16 の structured output は prompt で JSON を要求し local validation と 1 回の retry を行う方式で、provider-enforced schema ではないため実測が必要。tool parser がなければ Qwen の tool syntax は Anthropic `tool_use` にならず、reasoning parser がなければ default thinking が output budget を消費し得る。最初に plain response と安全な tool call を検証し、unauthenticated な `EMPTY` endpoint は trusted private network だけで使う。[公式 model card](https://huggingface.co/Qwen/Qwen3.8-27B)、[vLLM Qwen3.8 recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)、[vLLM serving docs](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)を参照。

## Trace experiment

prompt ごとに新しい CLI process を使い、remote model を warm up し、各 experiment を 3 回以上繰り返して vLLM version と hardware も記録する。期待する形は検証対象の仮説である。A は「tool を使わず baseline complete とだけ返す」で 1 model call の baseline、B は delegation なしで s15 dispatch boundary を検索・read する tool-heavy run、C は 3 task を作成して teammate に渡す decomposition、D は s15/s16/tracer の独立集計を 3 teammate に明示的に並列実行させる run、E は s01–s17 の README 全体を読む long-context run とする。Qwen と Claude の比較では prompt、revision、permission answer、server parameter、warm state を固定し、成功率、tool choice、retry、depth、parallelism も比較する。

---

## s14 からの変化

| Scope | s14 MCP | s15 Integrated Harness |
|-------|---------|-------------------------|
| built-in tools | 6 | 25 |
| external tools | 接続済み MCP tools | 同じ dynamic MCP path と host policy |
| local mechanisms | S04 tools、hooks、permission、MCP | todo、subagent、skills、compaction、memory、task graph、background bash、cron、teams、worktrees |
| event sources | user input と tool results | user input、tool results、cron prompts、background notifications、team events |

---

## 試す

```sh
cd learn-claude-code
python s15_integrated_harness/code.py
```

試す prompt：

1. `このリポジトリを調べ、重要な Python ファイルを教えてください。`
2. `接続済みのドキュメントから agent loop の説明を探してください。`
3. `認証モジュールとログインページを隔離した worktree で並行してリファクタリングし、編集前にそれぞれのプランを見せてください。`
4. `3 分後に会議を知らせてください。`
5. `依存関係をバックグラウンドでインストールしながら README.md を読んでください。`

見るポイント：

- tool call の前に hooks/permission を通るか
- `connect_mcp` 後の次 round で MCP tool が出るか
- `run_in_background=true` の bash call が background placeholder を返すか
- cron が時刻到達時に自動で reminder を返すか
- teammate が plan を提出し、approval 前に停止するか
- idle teammate が ready task を 1 つだけ atomic に claim するか
- teammate のすべての file tool が claimed task の `cwd` へ切り替わるか
- complete 後も同じ turn の間は task `cwd` を保ち、IDLE で assignment を解除するか

---

## 次へ

[s16 Workflow Runtime](../s16_workflow_runtime/) は、この host に `Workflow` tool を追加する。Workflow は固定された orchestration path を code に置き、進行状況を記録して同じ run を再開できるようにする。

<!-- translation-sync: zh@v15, en@v15, ja@v15 -->
