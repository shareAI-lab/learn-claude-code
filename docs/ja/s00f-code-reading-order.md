# s00f: このリポジトリのコード読解順

> このページは「もっと多くコードを読め」という話ではありません。  
> もっと狭い問題を解決します。
>
> **章順が安定したあと、このリポジトリのコードをどんな順で読めば心智モデルを崩さずに理解できるのか。**

## 先に結論

次の読み方は避けます。

- いちばん長いファイルから読む
- いちばん高度そうな章へ飛ぶ
- 先に `web/` を開いて主線を逆算する
- `agents/*.py` 全体を 1 つの平坦なソース群として眺める

安定したルールは 1 つです。

**コードもカリキュラムと同じ順番で読む。**

各章ファイルの中では、毎回同じ順で読みます。

1. 状態構造
2. tool 定義や registry
3. 1 ターンを進める関数
4. CLI 入口は最後

## なぜこのページが必要か

読者が詰まるのは文章だけではありません。実際にコードを開いた瞬間に、間違った場所から読み始めてまた混ざることが多いからです。

## どの agent ファイルでも同じテンプレートで読む

### 1. まずファイル先頭

最初に答えること:

- この章は何を教えているか
- まだ何を故意に教えていないか

### 2. 状態構造や manager class

優先して探すもの:

- `LoopState`
- `PlanningState`
- `CompactState`
- `TaskManager`
- `BackgroundManager`
- `TeammateManager`
- `WorktreeManager`

### 3. tool 一覧や registry

優先して見る入口:

- `TOOLS`
- `TOOL_HANDLERS`
- `build_tool_pool()`
- 主要な `run_*`

### 4. ターンを進める関数

たとえば:

- `run_one_turn(...)`
- `agent_loop(...)`
- 章固有の `handle_*`

### 5. CLI 入口は最後

`if __name__ == "__main__"` は大事ですが、最初に見る場所ではありません。

## Stage 1: `s01-s06`

この段階は single-agent の背骨です。

| 章 | ファイル | 先に見るもの | 次に見るもの | 次へ進む前に確認すること |
|---|---|---|---|---|
| `s01` | `agents/s01_agent_loop.py` | `LoopState` | `TOOLS` -> `run_one_turn()` -> `agent_loop()` | `messages -> model -> tool_result -> next turn` を追える |
| `s02` | `agents/s02_tool_use.py` | `safe_path()` | handler 群 -> `TOOL_HANDLERS` -> `agent_loop()` | ループを変えずに tool が増える形が分かる |
| `s03` | `agents/s03_todo_write.py` | planning state | todo 更新経路 -> `agent_loop()` | 会話内 plan の外化が分かる |
| `s04` | `agents/s04_subagent.py` | `AgentTemplate` | `run_subagent()` -> 親 `agent_loop()` | 文脈隔離としての subagent が分かる |
| `s05` | `agents/s05_skill_loading.py` | skill registry | registry 周り -> `agent_loop()` | discover light / load deep が分かる |
| `s06` | `agents/s06_context_compact.py` | `CompactState` | compact 周辺 -> `agent_loop()` | compact の本質が分かる |

## Stage 2: `s07-s11`

ここは control plane を固める段階です。

| 章 | ファイル | 先に見るもの | 次に見るもの | 次へ進む前に確認すること |
|---|---|---|---|---|
| `s07` | `agents/s07_permission_system.py` | validator / manager | permission path -> `agent_loop()` | gate before execute |
| `s08` | `agents/s08_hook_system.py` | `HookManager` | hook dispatch -> `agent_loop()` | 固定拡張点としての hook |
| `s09` | `agents/s09_memory_system.py` | memory manager | save / prompt build -> `agent_loop()` | 長期情報層としての memory |
| `s10` | `agents/s10_system_prompt.py` | `SystemPromptBuilder` | input build -> `agent_loop()` | pipeline としての prompt |
| `s11` | `agents/s11_error_recovery.py` | compact / backoff helper | recovery 分岐 -> `agent_loop()` | 失敗後の続行 |

## Stage 3: `s12-s14`

ここから harness は work runtime へ広がります。

| 章 | ファイル | 先に見るもの | 次に見るもの | 次へ進む前に確認すること |
|---|---|---|---|---|
| `s12` | `agents/s12_task_system.py` | `TaskManager` | task create / unlock -> `agent_loop()` | durable goal |
| `s13` | `agents/s13_background_tasks.py` | `NotificationQueue` / `BackgroundManager` | background registration -> `agent_loop()` | runtime slot |
| `s14` | `agents/s14_cron_scheduler.py` | `CronLock` / `CronScheduler` | trigger path -> `agent_loop()` | 未来の開始条件 |

## Stage 4: `s15-s19`

ここは platform 境界を作る段階です。

| 章 | ファイル | 先に見るもの | 次に見るもの | 次へ進む前に確認すること |
|---|---|---|---|---|
| `s15` | `agents/s15_agent_teams.py` | `MessageBus` / `TeammateManager` | roster / inbox / loop -> `agent_loop()` | persistent teammate |
| `s16` | `agents/s16_team_protocols.py` | `RequestStore` | request handler -> `agent_loop()` | request-response + `request_id` |
| `s17` | `agents/s17_autonomous_agents.py` | claim helper / identity helper | claim -> resume -> `agent_loop()` | idle check -> safe claim -> resume |
| `s18` | `agents/s18_worktree_task_isolation.py` | manager 群 | worktree lifecycle -> `agent_loop()` | goal と execution lane の分離 |
| `s19` | `agents/s19_mcp_plugin.py` | capability 周辺 class | route / normalize -> `agent_loop()` | external capability が同じ control plane に戻ること |

## 最良の「文書 + コード」学習ループ

各章で次を繰り返します。

1. 章本文を読む
2. bridge doc を読む
3. 対応する `agents/sXX_*.py` を開く
4. 状態 -> tools -> turn driver -> CLI 入口 の順で読む
5. demo を 1 回動かす
6. 最小版を自分で書き直す

## 一言で言うと

**コード読解順も教学順に従うべきです。まず境界、その次に状態、最後に主ループをどう進めるかを見ます。**
