# s00d: Chapter Order Rationale

> この資料は 1 つの仕組みを説明するためのものではありません。  
> もっと基礎的な問いに答えるための資料です:
>
> **なぜこの教材は今の順序で教えるのか。なぜ source file の並びや機能の派手さ、実装難度の順ではないのか。**

## 先に結論

現在の `s01 -> s19` の順序は妥当です。

この順序の価値は、単に章数が多いことではなく、学習者が理解すべき依存順でシステムを育てていることです。

1. 最小の agent loop を作る
2. その loop の周囲に control plane と hardening を足す
3. session 内 planning を durable work と runtime state へ広げる
4. その後で teammate、isolation lane、external capability へ広げる

つまりこの教材は:

**mechanism の依存順**

で構成されています。

## 4 本の依存線

この教材は大きく 4 本の依存線で並んでいます。

1. `core loop dependency`
2. `control-plane dependency`
3. `work-state dependency`
4. `platform-boundary dependency`

雑に言うと:

```text
まず agent を動かす
  -> 次に安全に動かす
  -> 次に長く動かす
  -> 最後に platform として動かす
```

これが今の順序の核心です。

## 全体の並び

```text
s01-s06
  単一 agent の最小主線を作る

s07-s11
  control plane と hardening を足す

s12-s14
  durable work と runtime を作る

s15-s19
  teammate・protocol・autonomy・worktree・external capability を足す
```

各段の終わりで、学習者は次のように言えるべきです。

- `s06` の後: 「動く単一 agent harness を自力で作れる」
- `s11` の後: 「それをより安全に、安定して、拡張しやすくできる」
- `s14` の後: 「durable task、background runtime、time trigger を整理して説明できる」
- `s19` の後: 「高完成度 agent platform の外周境界が見えている」

## なぜ前半は今の順序で固定すべきか

### `s01` は必ず最初

ここで定義されるのは:

- 最小の入口
- turn ごとの進み方
- tool result がなぜ次の model call に戻るのか

これがないと、後ろの章はすべて空中に浮いた feature 説明になります。

### `s02` は `s01` の直後でよい

tool がない agent は、まだ「話しているだけ」で「作業している」状態ではありません。

`s02` で初めて:

- model が `tool_use` を出す
- system が handler を選ぶ
- tool が実行される
- `tool_result` が loop に戻る

という、harness の実在感が出ます。

### `s03` は `s04` より前であるべき

教育上ここは重要です。

先に教えるべきなのは:

- 現在の agent が自分の仕事をどう整理するか

その後に教えるべきなのが:

- どの仕事を subagent へ切り出すべきか

`s04` を早くしすぎると、subagent が isolation mechanism ではなく逃げ道に見えてしまいます。

### `s05` は `s06` の前で正しい

この 2 章は同じ問題の前半と後半です。

- `s05`: そもそも不要な知識を context へ入れすぎない
- `s06`: それでも残る context をどう compact するか

先に膨張を減らし、その後で必要なものだけ compact する。  
この順序はとても自然です。

## なぜ `s07-s11` は 1 つの hardening block なのか

この 5 章は別々に見えて、実は同じ問いに答えています:

**loop はもう動く。では、それをどう安定した本当の system にするか。**

### `s07` は `s08` より前で正しい

先に必要なのは:

- その action を実行してよいか
- deny するか
- user に ask するか

という gate の考え方です。

その後で:

- loop の周囲に何を hook するか

を教える方が自然です。

つまり:

**gate が先、extend が後**

です。

### `s09` は `s10` より前で正しい

`s09` は:

- durable information が何か
- 何を long-term に残すべきか

を教えます。

`s10` は:

- 複数の入力源をどう model input に組み立てるか

を教えます。

つまり:

- memory は content source を定義する
- prompt assembly は source たちの組み立て順を定義する

逆にすると、prompt pipeline が不自然で謎の文字列操作に見えやすくなります。

### `s11` はこの block の締めとして適切

error recovery は独立した機能ではありません。

ここで system は初めて:

- なぜ continue するのか
- なぜ retry するのか
- なぜ stop するのか

を明示する必要があります。

そのためには、input path、tool path、state path、control path が先に見えている必要があります。

## なぜ `s12-s14` は goal -> runtime -> schedule の順なのか

ここは順番を崩すと一気に混乱します。

### `s12` は `s13` より先

`s12` は:

- 仕事そのものが何か
- dependency がどう張られるか
- downstream work がいつ unlock されるか

を教えます。

`s13` は:

- 今まさに何が live execution として動いているか
- background result がどこへ戻るか
- runtime state がどう write-back されるか

を教えます。

つまり:

- `task` は durable goal
- `runtime task` は live execution slot

です。

ここを逆にすると、この 2 つが一語の task に潰れてしまいます。

### `s14` は `s13` の後であるべき

cron は別種の task を増やす章ではありません。

追加するのは:

**time という start condition**

です。

だから自然な順序は:

`durable task graph -> runtime slot -> schedule trigger`

になります。

## なぜ `s15-s19` は team -> protocol -> autonomy -> worktree -> capability bus なのか

### `s15` で system 内に誰が持続するかを定義する

protocol や autonomy より前に必要なのは durable actor です。

- teammate は誰か
- どんな identity を持つか
- どう持続するか

### `s16` で actor 間の coordination rule を定義する

protocol は actor より先には来ません。

protocol は次を構造化するために存在します。

- 誰が request するか
- 誰が approve するか
- 誰が respond するか
- どう trace するか

### `s17` はその後で初めて明確になる

autonomy は曖昧に説明しやすい概念です。

しかし本当に必要なのは:

- persistent teammate がすでに存在する
- structured coordination がすでに存在する

という前提です。

そうでないと autonomous claim は魔法っぽく見えてしまいます。

### `s18` は `s19` より前がよい

worktree isolation は local execution boundary の問題です。

- 並列作業がどこで走るか
- lane 同士をどう隔離するか

これを先に見せてから:

- plugin
- MCP server
- external capability route

へ進む方が、自作実装の足場が崩れません。

### `s19` は最後で正しい

ここは platform の最外周です。

local の:

- actor
- lane
- durable task
- runtime execution

が見えた後で、ようやく:

- external capability provider

がきれいに入ってきます。

## コースを悪くする 5 つの誤った並べ替え

1. `s04` を `s03` より前に動かす  
   local planning より先に delegation を教えてしまう。

2. `s10` を `s09` より前に動かす  
   input source の理解なしに prompt assembly を教えることになる。

3. `s13` を `s12` より前に動かす  
   durable goal と live runtime slot が混ざる。

4. `s17` を `s15` や `s16` より前に動かす  
   autonomy が曖昧な polling magic に見える。

5. `s19` を `s18` より前に動かす  
   local platform boundary より external capability が目立ってしまう。

## Maintainer が順序変更前に確認すべきこと

章を動かす前に次を確認するとよいです。

1. 前提概念はすでに前で説明されているか
2. この変更で別の層の概念同士が混ざらないか
3. この章が主に追加するのは goal か、runtime state か、actor か、capability boundary か
4. これを早めても、学習者は最小正解版をまだ自力で作れるか
5. これは開発者理解のための変更か、それとも source file の順を真似ているだけか

5 番目が後者なら、たいてい変更しない方がよいです。

## 一文で残すなら

**良い章順とは、mechanism の一覧ではなく、各章が前章から自然に伸びた次の層として見える並びです。**
