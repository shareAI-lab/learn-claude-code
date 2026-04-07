# s00: アーキテクチャ全体図

> この章は教材全体の地図です。  
> 「結局この repository は何を教えようとしていて、なぜこの順番で章が並んでいるのか」を先に掴みたいなら、まずここから読むのがいちばん安全です。

## 先に結論

この教材の章順は妥当です。

大事なのは章数の多さではありません。  
大事なのは、初学者が無理なく積み上がる順番で system を育てていることです。

全体は次の 4 段階に分かれています。

1. まず本当に動く単一 agent を作る
2. その上に安全性、拡張点、memory、prompt、recovery を足す
3. 会話中の一時的 progress を durable work system へ押し上げる
4. 最後に teams、protocols、autonomy、worktree、MCP / plugin へ広げる

この順番が自然なのは、学習者が最初に固めるべき主線がたった 1 本だからです。

```text
user input
  ->
model reasoning
  ->
tool execution
  ->
result write-back
  ->
next turn or finish
```

この主線がまだ曖昧なまま後段の mechanism を積むと、

- permission
- hook
- memory
- MCP
- worktree

のような言葉が全部ばらばらの trivia に見えてしまいます。

## この教材が再構成したいもの

この教材の目標は、どこかの production code を逐行でなぞることではありません。

本当に再構成したいのは次の部分です。

- 主要 module は何か
- module 同士がどう協調するか
- 各 module の責務は何か
- 重要 state がどこに住むか
- 1 つの request が system の中をどう流れるか

つまり狙っているのは、

**設計主脈への高い忠実度であって、周辺実装の 1:1 再現ではありません。**

これはとても重要です。

もしあなたが本当に知りたいのが、

> 0 から自分で高完成度の coding agent harness を作れるようになること

なら、優先して掴むべきなのは次です。

- agent loop
- tools
- planning
- context management
- permissions
- hooks
- memory
- prompt assembly
- tasks
- teams
- isolated execution lanes
- external capability routing

逆に、最初の主線に持ち込まなくてよいものもあります。

- packaging / release
- cross-platform compatibility の細かな枝
- enterprise wiring
- telemetry
- 歴史的 compatibility layer
- product 固有の naming accident

これらが存在しうること自体は否定しません。  
ただし 0-to-1 教学の中心に置くべきではありません。

## 読むときの 3 つの原則

### 1. まず最小で正しい版を学ぶ

たとえば subagent なら、最初に必要なのはこれだけです。

- 親 agent が subtask を切る
- 子 agent が自分の `messages` を持つ
- 子 agent が summary を返す

これだけで、

**親 context を汚さずに探索作業を切り出せる**

という核心は学べます。

そのあとでようやく、

- 親 context を引き継ぐ fork
- 独立 permission
- background 実行
- worktree 隔離

を足せばよいです。

### 2. 新しい語は使う前に意味を固める

この教材では次のような語が頻繁に出ます。

- state machine
- dispatch map
- dependency graph
- worktree
- protocol envelope
- capability
- control plane

意味が曖昧なまま先へ進むと、後ろの章で一気に詰まります。

そのときは無理に本文を読み切ろうとせず、次の文書へ戻ってください。

- [`glossary.md`](./glossary.md)
- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)

### 3. 周辺の複雑さを主線へ持ち込みすぎない

良い教材は「全部話す教材」ではありません。

良い教材は、

- 核心は完全に話す
- 周辺で重く複雑なものは後ろへ回す

という構造を持っています。

だからこの repository では、あえて主線の外に置いている内容があります。

- packaging / release
- enterprise policy glue
- telemetry
- client integration の細部
- 逐行の逆向き比較 trivia

## 先に開いておくと楽な補助文書

主線 chapter と一緒に、次の文書を補助地図として持っておくと理解が安定します。

| 文書 | 用途 |
|---|---|
| [`teaching-scope.md`](./teaching-scope.md) | 何を教え、何を意図的に省くかを見る |
| [`data-structures.md`](./data-structures.md) | system 全体の重要 record を一か所で見る |
| [`s00f-code-reading-order.md`](./s00f-code-reading-order.md) | chapter order と local code reading order をそろえる |

さらに、後半で mechanism 間のつながりが曖昧になったら、次の bridge docs が効きます。

| 文書 | 補うもの |
|---|---|
| [`s00d-chapter-order-rationale.md`](./s00d-chapter-order-rationale.md) | なぜ今の順番で学ぶのか |
| [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) | 参照 repository の高信号 module 群と教材章の対応 |
| [`s00a-query-control-plane.md`](./s00a-query-control-plane.md) | 高完成度 system に loop 以外の control plane が必要になる理由 |
| [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md) | 1 request が system 全体をどう流れるか |
| [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) | tool layer が単なる `tool_name -> handler` で終わらない理由 |
| [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) | message / prompt / memory がどこで合流するか |
| [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) | durable task と live runtime slot の違い |
| [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) | MCP を capability bus として見るための地図 |
| [`entity-map.md`](./entity-map.md) | entity の境界を徹底的に分ける |

## 4 段階の学習パス

### Stage 1: Core Single-Agent (`s01-s06`)

ここでの目標は、

**まず本当に役に立つ単一 agent を作ること**

です。

| 章 | 学ぶもの | 解く問題 |
|---|---|---|
| `s01` | Agent Loop | loop がなければ agent にならない |
| `s02` | Tool Use | model を「話すだけ」から「実際に動く」へ変える |
| `s03` | Todo / Planning | multi-step work が漂わないようにする |
| `s04` | Subagent | 探索作業で親 context を汚さない |
| `s05` | Skills | 必要な知識だけ後から載せる |
| `s06` | Context Compact | 会話が長くなっても主線を保つ |

### Stage 2: Hardening (`s07-s11`)

ここでの目標は、

**動くだけの agent を、安全で拡張可能な agent へ押し上げること**

です。

| 章 | 学ぶもの | 解く問題 |
|---|---|---|
| `s07` | Permission System | 危険な操作を gate の後ろへ置く |
| `s08` | Hook System | loop 本体を書き換えず周辺拡張する |
| `s09` | Memory System | 本当に価値ある情報だけを跨 session で残す |
| `s10` | System Prompt | stable rule と runtime input を組み立てる |
| `s11` | Error Recovery | 失敗後も stop 一択にしない |

### Stage 3: Runtime Work (`s12-s14`)

ここでの目標は、

**session 中の計画を durable work graph と runtime execution に分けること**

です。

| 章 | 学ぶもの | 解く問題 |
|---|---|---|
| `s12` | Task System | work goal を disk 上に持つ |
| `s13` | Background Tasks | 遅い command が前景思考を止めないようにする |
| `s14` | Cron Scheduler | 時間そのものを trigger にする |

### Stage 4: Platform (`s15-s19`)

ここでの目標は、

**single-agent harness を協調 platform へ広げること**

です。

| 章 | 学ぶもの | 解く問題 |
|---|---|---|
| `s15` | Agent Teams | persistent teammate を持つ |
| `s16` | Team Protocols | 協調を自由文から structured flow へ上げる |
| `s17` | Autonomous Agents | idle teammate が自分で次の work を取れるようにする |
| `s18` | Worktree Isolation | 並行 task が同じ directory を踏み荒らさないようにする |
| `s19` | MCP & Plugin | 外部 capability を統一 surface で扱う |

## 各章が system に足す中核構造

読者が中盤で混乱しやすいのは、

- 今の章は何を増やしているのか
- その state は system のどこに属するのか

が曖昧になるからです。

そこで各章を「新しく足す構造」で見直すとこうなります。

| 章 | 中核構造 | 学習後に言えるべきこと |
|---|---|---|
| `s01` | `LoopState` | 最小の agent loop を自分で書ける |
| `s02` | `ToolSpec` / dispatch map | model の意図を安定して実行へ落とせる |
| `s03` | `TodoItem` / `PlanState` | 現在の progress を外部 state として持てる |
| `s04` | `SubagentContext` | 親 context を汚さず委譲できる |
| `s05` | `SkillRegistry` | 必要な knowledge を必要な時だけ注入できる |
| `s06` | compaction records | 長い対話でも主線を保てる |
| `s07` | `PermissionDecision` | 実行を gate の後ろへ置ける |
| `s08` | hook events | loop を壊さず extension を追加できる |
| `s09` | memory records | 跨 session で残すべき情報を選別できる |
| `s10` | prompt parts | 入力を section 単位で組み立てられる |
| `s11` | recovery state / transition reason | なぜ続行するのかを state として説明できる |
| `s12` | `TaskRecord` | durable work graph を作れる |
| `s13` | `RuntimeTaskState` | live execution と work goal を分けて見られる |
| `s14` | `ScheduleRecord` | time-based trigger を足せる |
| `s15` | `TeamMember` | persistent actor を持てる |
| `s16` | `ProtocolEnvelope` / `RequestRecord` | structured coordination を作れる |
| `s17` | `ClaimPolicy` / autonomy state | 自治的な claim / resume を説明できる |
| `s18` | `WorktreeRecord` / `TaskBinding` | 並行 execution lane を分離できる |
| `s19` | `MCPServerConfig` / capability route | native / plugin / MCP を同じ外側境界で見られる |

## system 全体を 3 層で見る

全体を最も簡単に捉えるなら、次の 3 層に分けてください。

```text
1. Main Loop
   user input を受け、model を呼び、結果に応じて続く

2. Control / Context Layer
   permission、hook、memory、prompt、recovery が loop を支える

3. Work / Platform Layer
   tasks、teams、runtime slots、worktrees、MCP が大きな作業面を作る
```

図で見るとこうです。

```text
User
  |
  v
messages[]
  |
  v
+-------------------------+
| Agent Loop (s01)        |
| 1. 入力を組み立てる      |
| 2. model を呼ぶ         |
| 3. stop_reason を見る   |
| 4. tool を実行する      |
| 5. result を write-back |
| 6. 次 turn を決める     |
+-------------------------+
  |
  +------------------------------+
  |                              |
  v                              v
Tool / Control Plane         Context / State Layer
(s02, s07, s08, s19)         (s03, s06, s09, s10, s11)
  |                              |
  v                              v
Tasks / Teams / Worktree / Runtime (s12-s18)
```

ここで大切なのは、system 全体を 1 本の巨大な file や 1 つの class として捉えないことです。

**chapter order とは、system をどの層の順で理解すると最も心智負荷が低いかを表したもの**

です。

## この章を読み終えたら何が言えるべきか

この章のゴールは、個々の API を覚えることではありません。

読み終えた時点で、少なくとも次の 3 文を自分の言葉で言える状態を目指してください。

1. この教材は production implementation の周辺 detail ではなく、agent harness の主設計を教えている
2. chapter order は `single agent -> hardening -> runtime work -> platform` の 4 段階で意味がある
3. 後ろの章の mechanism は前の章の上に自然に積み上がるので、順番を大きく崩すと学習心智が乱れる

## 一文で覚える

**良い章順とは、機能一覧ではなく、前の層から次の層が自然に育つ学習経路です。**
