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

Claude Code の設計者は率直です。dynamic workflow は、モデルがその場で自分用の multi-agent harness を書けるようにします。コースのモットーを一階上げると、こうなります。各ステップの中ではモデルを信頼する。ステップの並びは、自分で形を決める。

## 長いチャットが静かにやりがちなこと

s01 から s15 まで、計画と行動は同じ context window を共有します。次の一手が直前の発見に依るときは、とても心地よいです。

ところが仕事が長く、大規模に並行し、硬い構造を求め、あるいは疑り深い第二意見が要ると、脆くなります。長いチャットをじっと見ていると、用語を覚える前に、見覚えのある癖に出会います。

50 項目のうち 35 で勝利宣言をする。自分の宿題を採点させると甘くなる——狐が鶏小屋を採点する。多ターンと圧縮のあいだに、「X には触るな」という静かな制約が薄れていく。

それが agentic laziness、self-preferential bias、goal drift です。名前より感触が大事です。仕事をする窓が、計画を覚える窓でもある。会話履歴は、並行性や安定した結果の形、落ちたあとの再開を預けるには柔らかい場所です。多くのファイルを review する、調査してから検証する、N 個のモジュールを同じやり方で移す——そうした仕事は、形が先に分かっています。柔らかい記憶だけでは足りません。

## アイデアが落ちる瞬間

もし計画がコードの中に住んだらどうでしょう。

助手は相変わらず考えます——きれいな机で、焦点の定まった一つの仕事を。**script** がループと扇状の分配とマージを持ちます。中間結果は変数と journal にあり、会話には入りません。途中で切り上げる癖は艦隊全体を止めにくくなり、自己採点の甘さは著者ではない第二の助手にぶつかり、drift も掴みにくくなります。トポロジーを、疲れた語り手が毎ターン書き換える必要がないからです。

一行で言えば、**workflow はオーケストレーションを「賢さ」から「構造」へ移します。** モデルは各 `agent()` の中で判断し、地図は script が持ちます。

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

1 回の `Workflow` tool call が、その実行を始めます。進み具合は途中で小さく鳴り、最後に launch 情報と結果と task state が一つの tool result で戻ります。

## ふたつの入口——そして外のいとこ

Claude Code は入口について率直です。

ときどきモデルは、*この*タスク用の JavaScript オーケストレーションを書き、`script` として渡します（あとから `scriptPath` を編集することもあります）。これが **dynamic** の入口です。問題がまだ熱いうちに、合わせた harness を裁断します。

ときどき、良い script はすでに `.claude/workflows/` のような場所にあります。`name` と `args` で呼び出します。これが **saved** の入口です。残すに値した run が、再利用できるカードになったものです。

外にはいとこもあります。Agent SDK や `claude -p` で先に書く **static** harness です。あらゆるエッジケースに耐える必要があるので、どうしても汎用になります。dynamic はこの布のための裁断です。形が合ったら保存します。

![Static harness vs dynamic workflow](images/dynamic-vs-static.png)

*Claude Code の設計エッセイより。同じ問い、ふたつの harness。左 — 固定の検索→検証→要約で、汎用レポートに終わる。右 — billing コードを読み、分岐し、devil's advocate を呼んでから具体的な推奨を出す特注レシピ。*

**この章は Python の teaching runtime です。** 同じアイデアを、1 行ずつ読める形で示します。デモは名前で一つの saved workflow を登録します。概念は Claude Code の script 世界と一一対応です。「モデルは実行可能コードを渡せない」などと言いません——それは Claude Code については初めから正しくありませんでした。ここでは、完全な JavaScript インタプリタを埋め込まないだけです。

```python
# Teaching adapter: saved の入口（name + args）。
# Claude Code は script / scriptPath / resumeFromRunId も受け付ける。
WORKFLOW_TOOL = {
    "name": "Workflow",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "args": {"type": "object"},
            "resume_from_run_id": {"type": "string"},
            "resumeFromRunId": {"type": "string"},
        },
        "required": ["name"],
    },
}
```

## スクリプトが話す三つの動詞

学校のバザーでケーキをたくさん焼くとします。どのテーブルも 混ぜる → 焼く → 箱詰め。助手が味見をし、レシピが順番を決めます。

![Workflow primitives: agent, parallel, pipeline](images/workflow-primitives.png)

*公式のプリミティブ・カード。ひとつの `agent` と、多くを走らせる二つのやり方 — `parallel`（barrier）と `pipeline`（各 item が自分の stage を流れる）。*

`agent(prompt, opts?)` は、助手ひとりに一つの仕事を頼むことです。`schema` を付ければ、答えは検証済み JSON になり——次の段が受け取れるソケットになり——最初が雑なら一回だけやり直せます。本物の Claude Code では `model`、`isolation`（worktree / remote）、`agentType` も選べます。この teaching runtime は表面を小さく保ち、1 行ずつ読めるようにしています。

`pipeline(items, *stages)` は多段仕事の既定です。各ケーキが自分で段階を歩き、一方が箱詰めのあいだに、もう一方はまだ混ぜていてもよい。stage 間に barrier はありません。

`parallel(thunks)` は揃うまで待つバリアです。次の段が本当に全部の結果を要すときだけ欲しくなります。トレイ全部を味見してから採点表を書く、といった場面です。

その周りに、静かな動詞もあります。`phase` はいまの場所、`log` は短い一声、入れ子の `workflow`、`args` は材料リスト、`budget` はオーブン分（token）です。

```python
# 各 review dimension が自分で audit → verify を歩く。
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

助手が失敗しても、艦隊は優しくいられます。`parallel` の失敗した thunk はそのスロットで `null` になり、gather 自体は reject しません。`pipeline` の失敗した stage は**その item** を null にし、残りの stage を飛ばします。マージの前に注意して絞ります。

厨房が止まったら？ 各 run には `runId` と disk 上の journal があります——助手が戻った順ではなく、あなたが**呼んだ**順のノートです。resume は script を先頭から歩き、**最長の未変更プレフィックス**を再生します。最初の変更または未完了で、それ以降はすべて live。本物の JS runtime が `Date.now()` と `Math.random()` を禁じるのはこのためです。時計とサイコロがノートをずらします。この Python デモはそのサンドボックスまではやりません——それでも script は決定的に書いてください。

```text
journal:  [A ok] [B ok] [C ok] [D ok]
resume:   A hit → B hit → C 変更 → D は live
```

## レシピが書けるようになったら——パターンの道具箱

動詞は小麦粉と火加減です。人が何度も発明し直すのは、少数の*形*です。道具箱だと思ってください。必点メニューではありません。

![Six Workflow Patterns](images/six-workflow-patterns.png)

*公式の六パターン格子 — 道具箱であり、必点メニューではない。トポロジーは script が持ち、このレッスンでは `agent` / `parallel` / `pipeline` / `phase` / journal で各形を話します。*

**Classify-And-Act。** 痛み: 万能の助手は何でもそこそこ。形: classifier が見て、専門家 A / B / C へ振り分ける。ここ: `agent({schema})` がラベルを返し、script が続く `agent`（または入れ子の `workflow`）へ分岐。全部が本当に同じ扱いでよいなら使わない。

**Fanout-And-Synthesize。** 痛み: 五十ファイルは一つの疲れた context に入らず、押し込めば混線する。形: 分け、多く走らせ、barrier で待ち、まとめる。ここ: 各 item に stage があるなら `pipeline`、次が全結果を要すなら `parallel`。まとめは gather のあとのふつうの Python。三つか五つの関連ファイルで足りるなら使わない。

**Adversarial Verification。** 痛み: 狐が鶏小屋を採点する。形: worker が出す。独立した verifier が反証する。生き残ったものだけ残る。ここ: 生産の `agent`、それから verifier の `parallel`（schema 付き）、そのあと filter。`phase` で Review と Verify。間違えても安いなら使わない。

**Generate-And-Filter。** 痛み: 欲しいのは選択肢であり、最初に賢く聞こえた案ではない。形: 多くの generator が rubric + dedupe の filter に流す。ここ: generator の `parallel`、そのあと script 側の filter（または審判 `agent`）。生成が高いとき journal が効く。良い答えの空間がもともと狭いなら使わない。

**Tournament。** 痛み: 味や順位では絶対スコアがぼやける。形: ペアごとの審判、トーナメント表、勝者——比較判断は孤独な採点に勝る。ここ: pairwise 審判 `agent` の `parallel` を回し、一つ残るまで続ける。鋭い rubric が一通しで決めるなら使わない。

**Loop Until Done。** 痛み: 坑道にまだ何巡あるか分からない。形: 「新しい発見？」が yes のあいだ spawn し続け、空振りで止まる。ここ: `while` で `agent`/`parallel` を包み、schema 付きの停止チェックと硬い `budget`。長い掘りには journal resume。仕事量が分かっているなら固定の `pipeline` の方が単純。

いくつか顔が付いたあと、道具箱は一目で収まります。

| パターン | プリミティブの素描 | 手を伸ばすとき |
|----------|--------------------|----------------|
| Classify-And-Act | `agent` → 分岐 → `agent` | 項目ごとに違う専門家が要る |
| Fanout-And-Synthesize | `pipeline` / `parallel` → 統合 | きれいな机がたくさん、そのあと一つの要約 |
| Adversarial Verification | 生産 → `parallel(verify)` → filter | 間違えると高い |
| Generate-And-Filter | `parallel(gens)` → rubric filter | まず選択肢、それから味 |
| Tournament | pairwise 審判 `agent` | 順位/味に鋭い物差しがない |
| Loop Until Done | `while` + 停止 + `budget` | どれだけ埋まっているか不明 |

組み合わせはふつうです。深い調査はしばしば fanout → filter → verify → synthesize と重ねます。私たちのサンプルは、二つの音の小さな和音です。

### 信頼できない入力に workflow が出会うとき

道具箱のそばにもう一つ残しておきたい形があります。**quarantine triage** です。サポートチケット、bug 報告、ユーザーフィードバックは信頼できません。それらを*読む* agent に、PR を開ける鍵まで持たせたくはありません。

![Quarantine triage](images/quarantine-triage.png)

*Reader は read-only の quarantine に留まり、分類と dedupe をし、構造化 summary だけを渡します。高権限ツールは trusted 側に住み — summary にだけ作用し、生本文には触れません。バックログが眠らないなら `/loop` と組んでもよいです。*

このレッスンのプリミティブでは、それも script と agent です。低権限 reader `agent` の `pipeline` や `parallel`、変数に入った構造化 summary、それから書く側の別 actor `agent`（または入れ子の `workflow`）。面白いのはエアロック — 誰が生テキストを見てよいか、です。

## `review-changes` を歩く — ひとつの composition

サンプルは「一つのパターン」ではありません。**Fanout-And-Synthesize** の中に **Adversarial Verification** が入り、終わりで軽く generate-and-filter がかかる——`isReal` の finding だけが残ります。

```text
correctness ── audit ── verify ──┐
security    ── audit ── verify ──┤── 確認済みの finding
performance ── audit ── verify ──┤
style       ── audit ── verify ──┘
         fanout                              synthesize
              └── 各 finding: 懐疑的 verify ──┘
```

`pipeline(DIMENSIONS, audit, verify)` が各 dimension に机を渡します。`verify` 内の verifier の `parallel` が敵対の和音です。ふつうのリスト filter が synthesize。`phase` が Review と Verify を印し、journal が各 `agent()` を覚えるので、止まっても audit をやり直さない。

三つの癖がお気に入りの席を失う感触があります。艦隊は二つの dimension で止められず、著者は審判ではなく、トポロジーは途中で漂いません。

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"{len(confirmed)} 件の実在する問題を確認")
    return {"confirmed": confirmed}
```

<details>
<summary>s15 に掛けて、置き換えない</summary>

s15 は依然として host loop です。s16 が足すのは `Workflow` という tool だけです。あなた（またはモデル）が saved の名前を頼み、adapter が script を見つけて走らせます。

本番では、その run は通知付きで背景に置き、セッションは応答し続けられます。teaching CLI は `demo` / `resume` を前景に置き、phase と cache hit を目で追えるようにしています。アイデアは同じで、簡略化したところははっきり言います。main loop は `bash` や `task` を借りるように、tool を一つ借ります。

</details>

## 宝石を回す: 計画を握っているのは誰か

近所を見ると、同じものが別の面を見せます。役に立つ問いは「agent は何人か？」ではなく、**トポロジーを誰が持つか**、仕掛かりの器はどこに置かれるか、です。

| 近所 | 計画を握るもの | 中間結果の置き場 | 向いている用途 |
|------|----------------|------------------|----------------|
| [s06 Subagent](../s06_subagent/) | モデル、一度きり | ほとんど捨てる | 汚い子タスクの隔離 |
| [s13 Agent Teams](../s13_agent_teams/) | Lead がターンごと + mailbox | 共有タスク / メッセージ | 長時間の同僚 |
| [s15 Integrated Harness](../s15_integrated_harness/) | 一つのループ内のモデル | 会話 `messages[]` | 積み上げ型 coding agent |
| **s16 Workflow** | **Script** | **変数 + journal** | 構造化した fan-out と verify |
| [s17 Goal Loop](../s17_goal_loop/) | 停止時の evaluator | 会話を証拠に | 「ゴール全体は終わったか？」 |

より安い道もしばしば勝ちます。skill を軟らかい計画にする、短い multi-agent の会話、手書きの static orchestrator、あるいは大きな一回のモデルターン。構造が単一の context より長く生きねばならないときに、workflow へ手を伸ばします。審査員パネルが聞こえがいいからではありません。

## 棚に戻しておくとき

Workflow は token と調整のコストを使います。ふつうのコーディングの大半は、五人の reviewer を必要としません。

回す前に聞いてください。この仕事は本当にもっと計算と定制 harness を欲しがっているか。ふつうの s15 の一ターン——あるいは一つの誠実な s06 subagent——で足りるなら、そこで止めます。抑制も思想の一部です。並行と専門化は、自分の席を自分で稼がねばなりません。

## 試してみる

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow（real API）
python s16_workflow_runtime/code.py demo     # 固定 fixture。phase を見る
python s16_workflow_runtime/code.py resume   # 同じ runId。cache hit を期待
```

Review が Verify に道を譲るのを見てください。完全な resume で agent が `done` から `cached` へ翻るのを見てください。終わりには短い確認リストがあり——きれいな resume では `agents=0 tokens=0` と出ます。ノートが「温め直しは要らない」と言っている感じです。

## 次へ

s16 はバッチの回し方です。[s17 Goal Loop](../s17_goal_loop/) は戸口で別の問いをします。止めるべきか、もう一ターンか。繰り返せるレシピに硬い「完了」も要るときは、そちらと組んでください。

<!-- translation-sync: zh@v16, en@v16, ja@v16 -->
