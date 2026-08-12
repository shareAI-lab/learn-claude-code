# s16: Workflow Runtime — レシピをコードに書く

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *「ターンごとのチャットは、10 秒ごとにシェフへメールするようなものです。Workflow は厨房が従えるレシピです。」*
>
> **Harness 層**: Orchestration — single-agent loop の上に multi-agent script を載せます。
>
> モデルを信頼し、harness をエンジニアリングする。Workflow は、その考えを一階上げたものです。

---

友だちとチャットだけで料理しているところを想像してください。「玉ねぎを切って」。待つ。「できた？」。次はフライパン、塩。一品ならそのリズムでも持ちます。二十卓の宴会では持ちません。手順は抜け、同じ言葉が返り、スマホが落ちたら冷たいところからやり直しです。

モデルがシェフとクリップボードを兼ねるときも、同じ感触です。計画と実行が一つの会話に押し込まれます。**Workflow** は書かれたレシピです。厨房（小さな runtime）がそれに従い、助手（subagent）が味見と判断をし、仕掛かりの器はカウンターに——変数と journal に——置かれます。グループスレッドの中ではありません。

## なぜ、もう一枚の harness が要るのか

デフォルトの Claude Code harness は、コーディング型の仕事にもう十分強いです。直す、走らせる、エラーを読む、また試す。一つのループ。一つの頭。かなりの手業が出ます。

ただ、ある仕事にはその上に**定制の harness** が要ります。深い調査、セキュリティの洗い出し、agent teams、変更一式を広げて review するような仕事です。SDK で先に手書きしてもよい。あるいは——ここが生きているところですが——Claude に**このタスク用**の harness を書かせ、走らせ、良いものを残せます。

コースのモットーを一階上げると、こうなります。各ステップの中ではモデルを信頼する。ステップの並びは、自分で形を決める。

## 長いチャットが静かにやりがちなこと

s01 から s15 まで、計画と行動は同じ context window を共有します。次の一手が直前の発見に依るときは心地よいです。仕事が長く、大規模に並行し、硬い構造を求め、あるいは疑り深い第二意見が要ると、脆くなります。

長いチャットをじっと見ていると、用語を覚える前に癖に出会います。50 項目のうち 35 で勝利宣言をする。自分の宿題を採点させると甘くなる——狐が鶏小屋を採点する。多ターンと圧縮のあいだに、「X には触るな」が薄れていく。

それが agentic laziness、self-preferential bias、goal drift です。名前より感触が大事です。仕事をする窓が、計画を覚える窓でもある。柔らかい会話メモリは、並行性や安定した結果の形、再開を預けるには弱い場所です。

## アイデアが落ちる瞬間

もし計画がコードの中に住んだらどうでしょう。

助手は相変わらず考えます——きれいな机で。**script** がループと扇状の分配とマージを持ちます。中間結果は変数と journal にあり、会話には入りません。途中で切り上げる癖は艦隊を止めにくくなり、自己採点の甘さは著者ではない第二の助手にぶつかり、drift も掴みにくくなります。

**Workflow はオーケストレーションを「賢さ」から「構造」へ移します。** モデルは各 `agent()` の中で判断し、地図は script が持ちます。

```text
  messages[] ──► Workflow(...) ──► tool_result { launched, result, task }
                      │
                      ▼
              ┌───────────────┐
              │ script が     │
              │ topology を持つ│
              └───────┬───────┘
                      │ agent / parallel / pipeline
                      ▼
                 変数 + journal
```

1 回の `Workflow` tool call が、その実行を始めます。進み具合は途中で小さく鳴り、レシピが終わると一つの tool result が戻ります。

<details>
<summary>Runtime 概要図（任意）</summary>

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

</details>

## ふたつの入口——そして外のいとこ

Claude Code は入口について率直です。

**Dynamic** — モデルが*この*タスク用の JavaScript オーケストレーションを書く（`script`、あとから `scriptPath`）。問題がまだ熱いうちに裁断する harness。

**Saved** — 良い script がすでに `.claude/workflows/` のような場所にある。`name` + `args` で呼び出す。残すに値した run が、再利用できるカードになったものです。

外にはいとこもあります。**static** harness を Agent SDK や `claude -p` で先に書くやり方です。あらゆるエッジケースに耐える必要があるので、どうしても汎用になります。dynamic はこの布のための裁断です。形が合ったら保存します。

![Static harness vs dynamic workflow](images/dynamic-vs-static.png)

*同じ問い、ふたつの harness。左: 固定の検索→検証→要約 → 汎用レポート。右: billing コードを読み、分岐し、devil's advocate を呼ぶ → 具体的な推奨。*

**この章は Python の teaching runtime です。** 同じアイデアを、1 行ずつ読める形で示します。デモは名前で一つの saved workflow を登録します。概念は Claude Code の script 世界と 1:1 です。「モデルは実行可能コードを渡せない」などと言いません——それは Claude Code については初めから正しくありませんでした。ここでは JS インタプリタを埋め込まないだけです。

```python
# teaching sketch — saved の入口（完全な Claude Code schema ではない）
Workflow({ "name": "review-changes", "args": { "changes": "..." } })

# Claude Code は他にも受け付ける: script | scriptPath | resumeFromRunId
```

## スクリプトが話す三つの動詞

学校のバザー。どのテーブルも 混ぜる → 焼く → 箱詰め。助手が味見をし、レシピが順番を決めます。

```text
  agent      助手ひとり、仕事ひとつ
  pipeline   各ケーキが自分で stage を歩く   （既定 — barrier なし）
  parallel   すべてのトレイが戻るまで待つ   （barrier — 控えめに）
```

`agent(prompt, opts?)` は助手ひとりに頼みます。`schema` があれば検証済み JSON が返り——次の段が受け取れるソケットになり——最初が雑なら一回だけやり直せます。

`pipeline` はケーキ A が箱詰めのあいだに、ケーキ B がまだ混ぜていてもよい形です。`parallel` は次の段が本当に全部の結果を要すときだけ——トレイ全部を味見してから採点表を書く、といった場面です。

```python
# teaching sketch — 形だけ（実行可能な sample は code.py）
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

助手が失敗しても艦隊は優しくいられます。`parallel` の失敗はそのスロットで `null`、`pipeline` の失敗は**その item** を落として残りの stage を飛ばします。マージの前に絞ります。

厨房が止まったら？ disk 上の journal が*呼び出し順*で各 call を覚えます。resume は**最長の未変更プレフィックス**を再生し、最初の変更から先は live。本物の JS runtime は `Date.now()` / `Math.random()` を禁じてノートを揃えます。この Python デモはそのサンドボックスまではやりません——それでも script は決定的に書いてください。

```text
  journal   [A] [B] [C] [D]
  resume     hit hit  ✂  live   ← プレフィックスは C で切れる
```

<details>
<summary>公式プリミティブ・カード + 静かな動詞</summary>

![Workflow primitives](images/workflow-primitives.png)

*公式カード: `agent`、そして `parallel`（barrier）と `pipeline`（streaming stages）。Claude Code には `model` / `isolation` / `agentType` もあります。teaching runtime は表面を小さく保ちます。*

静かな動詞: `phase`、`log`、入れ子の `workflow`（1 段）、`args`、`budget`。

</details>

## レシピが書けるようになったら——パターンの道具箱

動詞は小麦粉と火加減です。人が何度も発明し直すのは、少数の*形*——道具箱であり、必点メニューではありません。

![Six Workflow Patterns](images/six-workflow-patterns.png)

*公式の六パターン格子。トポロジーは script が持ち、このレッスンでは `agent` / `parallel` / `pipeline` / journal で各形を話します。*

このあとのサンプルのために、いちばん大事な三つを先に感じてください——名前はあとからでよいです。

**Fanout-And-Synthesize** — 五十ファイルは一つの疲れた context に入りません。分け、多く走らせ、barrier でまとめます。

```text
  task ──► ● ● ● ● ══barrier══► synthesize
```

**Adversarial Verification** — 狐が鶏小屋を採点してはいけません。worker が出し、独立した verifier が突き、立っているものだけ残します。

```text
  worker ──► verifier
         ├──► verifier
         └──► verifier   → まだ立つものだけ
```

**Generate-And-Filter** — 欲しいのは選択肢であり、最初に賢く聞こえた案ではありません。多くの generator、そのあと rubric（と dedupe）。

同じ道具箱には **Classify-And-Act**（専門家へ振り分け）、**Tournament**（ペア審判で勝者）、**Loop Until Done**（「新しい発見？」が yes のあいだ spawn、硬い `budget` 付き）もあります。コストが明瞭さや安全を買うときだけ、スタイルを借ります。

<details>
<summary>各パターンをこのレッスンのプリミティブへ写す</summary>

| パターン | プリミティブの素描 | 使わないとき |
|----------|--------------------|--------------|
| Classify-And-Act | `agent` → 分岐 → `agent` | 全部が同じ扱いでよい |
| Fanout-And-Synthesize | `pipeline` / `parallel` → 統合 | 一通しでもう足りる |
| Adversarial Verification | 生産 → `parallel(verify)` → filter | 間違えても安い |
| Generate-And-Filter | `parallel(gens)` → filter | 良い答えの空間がもともと狭い |
| Tournament | pairwise 審判 `agent` | 鋭い rubric が一通しで決める |
| Loop Until Done | `while` + 停止 + `budget` | 仕事量が分かっている |

```python
# teaching sketch — 分類してから動く
kind = await ctx.agent("この ticket を分類", schema=KIND)
if kind["type"] == "billing":
    return await ctx.agent("billing を処理…")
```

組み合わせはふつうです。深い調査はしばしば fanout → filter → verify → synthesize と重ねます。

</details>

### 信頼できない入力に workflow が出会うとき

サポートチケットやユーザーフィードバックは信頼できません。それらを*読む* agent に、PR を開ける鍵まで持たせたくありません。エアロックを残します。reader は read-only のまま、構造化 summary だけを渡し、trusted な actor は summary にだけ作用する——生本文には触れない。

```text
  backlog (untrusted)
       │
       ▼
  ┌─ QUARANTINE (read-only) ─┐
  │  readers → dedupe → summary │
  └────────────┬───────────────┘
               ▼
  ┌─ TRUSTED (high privilege) ─┐
  │  actor → fix / escalate     │
  └─────────────────────────────┘
```

<details>
<summary>公式 quarantine 図</summary>

![Quarantine triage](images/quarantine-triage.png)

*Reader は quarantine で分類と dedupe をし、高権限ツールは trusted 側に住みます。バックログが眠らないなら `/loop` と組んでもよいです。*

</details>

## `review-changes` を歩く — ひとつの composition

サンプルは「一つのパターン」ではありません。**Fanout-And-Synthesize** の中に **Adversarial Verification** が入り、終わりで軽く filter がかかる——`isReal` の finding だけが残ります。

```text
  correctness ── audit ── verify ──┐
  security    ── audit ── verify ──┤── confirmed
  performance ── audit ── verify ──┤
  style       ── audit ── verify ──┘
       fanout        ▲                synthesize
                     └── 各 finding の懐疑的 verify
```

`pipeline(DIMENSIONS, audit, verify)` が各 dimension に机を渡します。`verify` 内の verifier の `parallel` が敵対の和音です。リスト filter が synthesize。`phase` が Review → Verify を印し、journal が各 `agent()` を覚えるので、止まっても audit をやり直さない。

三つの癖が席を失う感触があります。艦隊は二つの dimension で止められず、著者は審判ではなく、トポロジーは途中で漂いません。

```python
# code.py より — 実行可能な sample（短縮）
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"{len(confirmed)} 件の実在する問題を確認")
    return {"confirmed": confirmed}
```

<details>
<summary>s15 に掛けて（置き換えない）</summary>

s15 は依然として host loop です。s16 が足すのは `Workflow` tool だけです。あなた（またはモデル）が saved の名前を頼み、adapter が script を走らせます。

本番では背景＋通知で置けます。teaching CLI は `demo` / `resume` を前景に置き、phase と cache hit を追いやすくしています。アイデアは同じで、簡略化は明示します。

</details>

## 宝石を回す: 計画を握っているのは誰か

役に立つ問いは「agent は何人か？」ではなく、**トポロジーを誰が持つか**、仕掛かりの器はどこに置かれるか、です。

| 近所 | 計画を握るもの | 中間結果の置き場 | 向いている用途 |
|------|----------------|------------------|----------------|
| [s06 Subagent](../s06_subagent/) | モデル、一度きり | ほとんど捨てる | 汚い子タスクの隔離 |
| [s13 Agent Teams](../s13_agent_teams/) | Lead + mailbox | 共有タスク / メッセージ | 長時間の同僚 |
| [s15 Integrated Harness](../s15_integrated_harness/) | 一つのループ内のモデル | `messages[]` | 積み上げ型 coding agent |
| **s16 Workflow** | **Script** | **変数 + journal** | 構造化した fan-out + verify |
| [s17 Goal Loop](../s17_goal_loop/) | 停止時の evaluator | 会話を証拠に | 「ゴール全体は終わったか？」 |

より安い道もしばしば勝ちます。skill を軟らかい計画にする、短い multi-agent の会話、手書きの static orchestrator、あるいは大きな一回のモデルターン。構造が単一の context より長く生きねばならないときに、workflow へ手を伸ばします。

## 棚に戻しておくとき

Workflow は token と調整のコストを使います。ふつうのコーディングの大半は、五人の reviewer を必要としません。

この仕事が本当にもっと計算と定制 harness を欲しがっているか、聞いてください。ふつうの s15 の一ターン——あるいは一つの誠実な s06 subagent——で足りるなら、そこで止めます。抑制も設計思想の一部です。

## 試してみる

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow（real API）
python s16_workflow_runtime/code.py demo     # 固定 fixture。phase を見る
python s16_workflow_runtime/code.py resume   # 同じ runId。cache hit を期待
```

Review が Verify に道を譲るのを見てください。完全な resume では agent が `cached` になり、`agents=0 tokens=0` と出るはずです——ノートが「温め直しは要らない」と言っている感じです。

## 次へ

s16 はバッチの回し方です。[s17 Goal Loop](../s17_goal_loop/) は戸口で別の問いをします。止めるべきか、もう一ターンか。

<!-- translation-sync: zh@v17, en@v17, ja@v17 -->
