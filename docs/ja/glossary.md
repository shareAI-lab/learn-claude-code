# 用語集

> この用語集は、教材主線で特に重要で、初学者が混ぜやすい言葉だけを集めたものです。  
> 何となく見覚えはあるのに、「結局これは何を指すのか」が言えなくなったら、まずここへ戻ってください。

## いっしょに見ると整理しやすい文書

- [`entity-map.md`](./entity-map.md): それぞれの言葉がどの層に属するかを見る
- [`data-structures.md`](./data-structures.md): 実際にどんな record 形へ落ちるかを見る
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md): `task` という語が 2 種類に分かれ始めたときに戻る
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md): MCP が tool list だけに見えなくなったときに戻る

## Agent

この教材での `agent` は、

> 入力を読み、判断し、必要なら tool を呼び出して仕事を進める model

を指します。

簡単に言えば、

- model が考える
- harness が作業環境を与える

という分担の、考える側です。

## Harness

`harness` は agent の周囲に置く作業環境です。

たとえば次を含みます。

- tools
- filesystem
- permission system
- prompt assembly
- memory
- task runtime

model そのものは harness ではありません。  
harness そのものも model ではありません。

## Agent Loop

`agent loop` は agent system の主循環です。

最小形は次の 5 手順です。

1. 現在の context を model に渡す
2. response が普通の返答か tool_use かを見る
3. tool を実行する
4. result を context に戻す
5. 次の turn へ続くか止まるかを決める

この loop がなければ、system は単発の chat で終わります。

## Message / `messages[]`

`message` は 1 件の message、`messages[]` はその一覧です。

多くの章では次を含みます。

- user message
- assistant message
- tool_result

これは agent の main working memory にあたります。  
ただし permanent memory ではありません。

## Tool

`tool` は model が要求できる動作です。

たとえば、

- file を読む
- file を書く
- shell command を走らせる
- text を検索する

などです。

重要なのは、

> model が直接 OS command を叩くのではなく、tool 名と引数を宣言し、実際の実行は harness 側の code が行う

という点です。

## Tool Schema

`tool schema` は tool の使い方を model に説明する構造です。

普通は次を含みます。

- tool 名
- 何をするか
- 必要な parameter
- parameter の型

初心者向けに言えば、tool の説明書です。

## Dispatch Map

`dispatch map` は、

> tool 名から実際の handler 関数へつなぐ対応表

です。

たとえば次のような形です。

```python
{
    "read_file": read_file_handler,
    "write_file": write_file_handler,
    "bash": bash_handler,
}
```

## Stop Reason

`stop_reason` は、model のこの turn がなぜ止まったかを示す理由です。

代表例:

- `end_turn`: 返答を終えた
- `tool_use`: tool を要求した
- `max_tokens`: 出力が token 上限で切れた

main loop はこの値を見て次の動きを決めます。

## Context

`context` は model が今見えている情報全体です。

ふつうは次を含みます。

- `messages`
- system prompt
- dynamic reminder
- tool_result

context は permanent storage ではなく、

> 今この turn の机の上に出ている情報

と考えると分かりやすいです。

## Compact / Compaction

`compact` は active context を縮めることです。

狙いは、

- 本当に必要な流れを残す
- 重複や雑音を削る
- 後続 turn のための space を作る

ことです。

大事なのは「削ること」そのものではなく、

**次の turn に必要な構造を保ったまま薄くすること**

です。

## Subagent

`subagent` は親 agent から切り出された、一回限りの delegated worker です。

価値は次です。

- 親 context を汚さずに subtask を処理できる
- 結果だけを summary として返せる

`teammate` とは違い、長く system に残る actor ではありません。

## Fork

この教材での `fork` は、

> 子 agent を空白から始めるのではなく、親の context を引き継いで始める方式

を指します。

subtask が親の議論背景を理解している必要があるときに使います。

## Permission

`permission` は、

> model が要求した操作を実行してよいか判定する層

です。

良い permission system は少なくとも次を分けます。

- すぐ拒否すべきもの
- 自動許可してよいもの
- user に確認すべきもの

## Permission Mode

`permission mode` は permission system の動作方針です。

例:

- `default`
- `plan`
- `auto`

つまり個々の request の判定規則ではなく、

> 判定の全体方針

です。

## Hook

`hook` は主 loop を書き換えずに、特定の timing で追加動作を差し込む拡張点です。

たとえば、

- tool 実行前に検査する
- tool 実行後に監査 log を書く

のようなことを行えます。

## Memory

`memory` は session をまたいで残す価値のある情報です。

向いているもの:

- user の長期的 preference
- 何度も再登場する重要事実
- 将来の session でも役に立つ feedback

向いていないもの:

- その場限りの冗長な chat 履歴
- すぐ再導出できる一時情報

## System Prompt

`system prompt` は system-level の instruction surface です。

ここでは model に対して、

- あなたは何者か
- 何を守るべきか
- どのように協力すべきか

を与えます。

普通の user message より安定して効く層です。

## System Reminder

`system reminder` は毎 turn 動的に差し込まれる短い補助情報です。

たとえば、

- current working directory
- 現在日付
- この turn だけ必要な補足

などです。

stable な system prompt とは役割が違います。

## Query

この教材での `query` は、

> 1 つの user request を完了させるまで続く多 turn の処理全体

を指します。

単発の 1 回応答ではなく、

- model 呼び出し
- tool 実行
- continuation
- recovery

を含んだまとまりです。

## Transition Reason

`transition reason` は、

> なぜこの system が次の turn へ続いたのか

を説明する理由です。

これが見えるようになると、

- 普通の tool continuation
- retry
- compact 後の再開
- recovery path

を混ぜずに見られるようになります。

## Task

`task` は durable work graph の中にある仕事目標です。

ふつう次を持ちます。

- subject
- status
- owner
- dependency

ここでの task は「いま実行中の command」ではなく、

> system が長く持ち続ける work goal

です。

## Dependency Graph

`dependency graph` は task 間の依存関係です。

たとえば、

- A が終わってから B
- C と D は並行可
- E は C と D の両方待ち

のような関係を表します。

これにより system は、

- 今できる task
- まだ blocked な task
- 並行可能な task

を判断できます。

## Runtime Task / Runtime Slot

`runtime task` または `runtime slot` は、

> いま実行中、待機中、または直前まで動いていた live execution unit

を指します。

例:

- background の `pytest`
- 走っている teammate
- monitor process

`task` との違いはここです。

- `task`: goal
- `runtime slot`: live execution

## Teammate

`teammate` は multi-agent system 内で長く存在する collaborator です。

`subagent` との違い:

- `subagent`: 一回限りの委譲 worker
- `teammate`: 長く残り、繰り返し仕事を受ける actor

## Protocol

`protocol` は、事前に決めた協調ルールです。

答える内容は次です。

- message はどんな shape か
- response はどう返すか
- approve / reject / expire をどう記録するか

team 章では多くの場合、

```text
request -> response -> status update
```

という骨格で現れます。

## Envelope

`envelope` は、

> 本文に加えてメタデータも一緒に包んだ構造化 record

です。

たとえば message 本文に加えて、

- `from`
- `to`
- `request_id`
- `timestamp`

を一緒に持つものです。

## State Machine

`state machine` は難しい理論名に見えますが、ここでは

> 状態がどう変化してよいかを書いた規則表

です。

たとえば、

```text
pending -> approved
pending -> rejected
pending -> expired
```

だけでも最小の state machine です。

## Router

`router` は分配器です。

役割は、

- request がどの種類かを見る
- 正しい処理経路へ送る

ことです。

tool system では、

- local handler
- MCP client
- plugin bridge

のどこへ送るかを決める層として現れます。

## Control Plane

`control plane` は、

> 自分で本仕事をするというより、誰がどう実行するかを調整する層

です。

たとえば、

- permission 判定
- prompt assembly
- continuation 理由
- lane 選択

などがここに寄ります。

初見では怖く見えるかもしれませんが、この教材ではまず

> 実作業そのものではなく、作業の進め方を調整する層

と覚えれば十分です。

## Capability

`capability` は能力項目です。

MCP の文脈では、capability は tool だけではありません。

たとえば、

- tools
- resources
- prompts
- elicitation

のように複数層があります。

## Worktree

`worktree` は同じ repository の別 working copy です。

この教材では、

> task ごとに割り当てる isolated execution directory

として使います。

価値は次です。

- 並行作業が互いの未コミット変更を汚染しない
- task と execution lane の対応が見える
- review や closeout がしやすい

## MCP

`MCP` は Model Context Protocol です。

この教材では単なる remote tool list より広く、

> 外部 capability を統一的に接続する surface

として扱います。

つまり「外部 tool を呼べる」だけではなく、

- connection
- auth
- resources
- prompts
- capability routing

まで含む層です。
