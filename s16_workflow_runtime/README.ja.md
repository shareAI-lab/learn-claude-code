# s16: Workflow Runtime — レシピをコードに書く

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *「ターンごとのチャットは、10 秒ごとにシェフへメールするようなものです。Workflow は厨房が従えるレシピです。」*
>
> **Harness 層**: Orchestration — single-agent loop の上で multi-agent script を実行します。
>
> モデルを信頼し、harness をエンジニアリングする。Workflow は orchestration 層での harness 設計です。

---

友だちとチャットだけで料理している場面を想像してください。「玉ねぎを切って」と送り、返事を待ち、「できた？」、次は「フライパンを……」。一品ならまだよいです。二十卓の宴会では、チャット自体がボトルネックになります。手順を忘れ、同じ指示を繰り返し、スマホが落ちたら最初からやり直しです。

ふつうの「モデルが指揮者」な会話も同じです。**Workflow** は書かれたレシピです。厨房（runtime）がそれに従い、助手（subagent）が判断し、途中の器はカウンターに置かれます —— グループチャットの中ではありません。

## そもそも harness は何のため？

デフォルトの Claude Code harness は、コーディング型の仕事に強いです。直す、走らせる、エラーを読む、また試す —— すべて同じループの中です。

ある種の仕事には、その上に**定制の harness** が要ります。深い調査、セキュリティ分析、agent teams、大規模な code review。SDK でその harness を先に手書きしてもよいです。あるいは —— ここが dynamic の発想ですが —— Claude に**このタスク用の harness をその場で書かせ**、走らせ、良いものを保存できます。

コースのモットーを一段上げるとこうなります。各ステップの中ではモデルを信頼する。ステップ同士の構造はエンジニアリングで決める。

## 問題: ひとつの窓、三つの失敗

s01 から s15 まで、モデルは**同じ** context の中で計画と実行をします。直前の発見で次が決まるタスクには向いています。長く、大規模に並行し、硬い構造が要り、あるいは敵対的な検証が要る仕事では脆くなります。

Claude Code の設計者は、その単一ウィンドウで起きやすい三つの失敗に名前を付けています。平たい言葉では:

| 失敗モード | どんな感じか |
|------------|--------------|
| **Agentic laziness（途中で切り上げ）** | 50 項目の review のうち 35 で「完了」と言う |
| **Self-preferential bias（自己びいき）** | 自分の発見を自分で採点すると甘くなる —— 狐が鶏小屋を採点する |
| **Goal drift（目標の漂流）** | もともとの「X には触るな」が多ターンと圧縮のあいだに薄れる |

会話履歴は、並行性・安定した結果の形・再開の三つを同時に預ける場所としても弱いです。多くのファイルを review する、調査してから検証する、N 個のモジュールを同じやり方で移す —— こうした仕事は**形が先に分かっている**ので、なおさらその三つが要ります。

## 一息でいうアイデア

**オーケストレーションを「賢さ」から「構造」へ移します。**

Subagent は相変わらず判断します —— それぞれきれいな context と、焦点の定まった仕事で。**script** がループ、扇状の分配、マージを持ちます。中間結果は変数（と journal）にあり、会話には入りません。分かれた助手 + script が握る制御フローが、laziness・自己チェックの偏り・drift への対抗策です。

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

1 回の `Workflow` tool call が、その script 実行を始めます。実行中に lifecycle / progress event が出て、最後に launch 情報・result・task state を含む tool result が返ります。

## ふたつの入口 — dynamic と static

Claude Code は同じ厨房への入口を二つ開いています。

| 入口 | 渡すもの | いつ使うか |
|------|----------|------------|
| **Dynamic** | オーケストレーション用の JavaScript（`script`、あとから `scriptPath`） | モデルが**このタスク用**にレシピを書く |
| **Saved** | `name` + `args` | 良いレシピを例えば `.claude/workflows/` に保存し、名前で再実行する |

厨房は同じです。Dynamic は「今レシピを書く」、Saved は「カード箱から引く」—— 良い dynamic run の残した、再利用できる残りです。

このレッスンの外にはいとこもあります。**static** harness（あらかじめ書く Agent SDK / `claude -p` の编排）です。static はあらゆるエッジケース向けなので、どうしても汎用になります。dynamic は*この*タスク向けの特注です。形が合ったら saved にします。

**このレッスンは Python の teaching runtime です。** 同じアイデアを、1 行ずつ読める形で示します。デモは名前で saved workflow を登録します。概念は Claude Code の script 世界と 1:1 です。「モデルは実行可能コードを渡せない」と Claude Code について主張するのは誤りでした。ここでは単に、完全な JS インタプリタを埋め込まないだけです。

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

## プリミティブを学校のバザーで

学校のバザーでたくさんのケーキを焼くとします。各テーブルは 混ぜる → 焼く → 箱詰め。助手が味見と判断をし、レシピが順番を決めます。

| Primitive | 厨房での意味 |
|-----------|--------------|
| `agent(prompt, {schema, label, phase})` | 助手ひとりに一つの仕事を頼む |
| `pipeline(items, *stages)` | **既定。** 各ケーキが自分で混ぜ→焼き→箱詰めを通る。A が箱詰め中でも、B はまだ混ぜているかもしれない |
| `parallel(thunks)` | **すべての**トレイが戻るまで待つ — 次の段が本当に全部の結果を必要とするときだけ |
| `phase(title)` | 進捗ボードに「今は焼き工程」と出す |
| `log(message)` | 短いステータスを一声 |
| `workflow(name, args)` | 小さなレシピを呼ぶ（ネストは 1 段） |
| `args` | この run に渡す材料リスト |
| `budget` | 使える「オーブン分」（token） |

既定は `pipeline` です。次の段が直前の結果をすべてまとめて必要とするときだけ `parallel` を使います —— 全トレイを味見してから採点表を書く、といった場合です。

```python
# 各 dimension が独立して audit → verify を通る（stage 間に barrier なし）。
results = await ctx.pipeline(DIMENSIONS, audit, verify)
confirmed = [f for r in results if r for f in r["confirmed"]]
```

## 味のあるパターン（一覧の投げ売りではない）

パターンはレシピのスタイルだと思ってください。サンプル `review-changes` が頼るのは主に三つです。

| パターン | 平たい意味 | サンプルでは |
|----------|------------|--------------|
| **Fan-out-and-synthesize** | 仕事を分け、きれいな机で進め、あとでまとめる | 4 つの dimension が `pipeline` で audit し、確認リストへ |
| **Adversarial verification** | 別の助手が前の成果をあえて疑う | 各 finding が verify agent を通ってから残る |
| **Generate-and-filter** | 候補を出し、検査を通ったものだけ残す | findings 入り → `isReal` だけ出し |

同じ道具箱には、あとで出会うスタイルもあります。**classify-and-act**（種類で振り分け）、**tournament**（競わせて勝者を選ぶ）、**loop-until-done**（新しいものがなくなるまで回す）。コストに見合う、より明確で安全な結果が取れるときだけ使います。

## 答えを機械が読める形に

助手が散文で返してくると、次の stage は finding と verdict を reliably に対応づけられません。`schema` を渡します。runtime は JSON を求め、検証し、だめなら**1 回だけ**再試行します。それでもだめならその call はエラーになります（下の null 分離を参照）。

```python
out = await ctx.agent(
    f"この変更に {dimension} 関連の問題がないか確認してください:\n{changes}",
    schema=FINDINGS_SCHEMA,
    label=f"audit:{dimension}",
)
# out は "findings" を持つ dict であり、段落ではない
```

あなたとの会話は自然言語でよいです。パイプラインには合うソケットが必要です。

## 助手がひとり失敗したとき

トレイがひとつ焦げても、艦隊全体を止めてはいけません。

- **`parallel`**: 失敗した thunk はそのスロットで `null` / `None` になります。gather 自体は reject しません。
- **`pipeline`**: 失敗した stage は**その item** を `null` / `None` にし、残りの stage をスキップします。他の item は進み続けます。

マージ前に注意して絞り込みます。よくあるのは `if r` / `.filter(Boolean)` です。

```python
verdicts = await ctx.parallel([...])  # いくつかは None かもしれない
confirmed = [
    f for f, v in zip(findings, verdicts)
    if v and v.get("isReal")
]
```

## Journal と resume

各 run には `runId` があります。`agent()` が終わるたびに、runtime は disk 上の journal へ 1 行追記します。ノートだと思ってください。助手がオーブンから戻った順ではなく、あなたが**呼んだ**順です。

resume（`resume_from_run_id` / `resumeFromRunId`）では script をまた先頭から走らせますが：

1. 呼び出し順で、各 `agent()` を次の journal 行と照合します。
2. **最長の未変更プレフィックス** → cache hit（即座に再生）。
3. **最初の**変更または未完了 call でプレフィックスが切れます。
4. **それ以降はすべて live** — journal の後ろに古い key が残っていても、黙って hit しません。

本物の JS workflow runtime が `Date.now()` / `Math.random()` / 引数なしの `new Date()` を禁じるのはこのためです。非決定的な時計や乱数は prompt や呼び出し順を変え、ノートが合わなくなります。この Python デモは完全なサンドボックスではありません —— それでも script は決定的に書いてください。

```text
journal:  [A ✓] [B ✓] [C ✓] [D ✓]
resume:   A hit → B hit → C 変更 → D は live（古い D への silent hit なし）
```

## サンプルを歩く: `review-changes`

4 つの review dimension が同じ 2 段階の道を通ります —— fan-out、敵対的 verify、filter。

```text
correctness ── audit ── verify ──┐
security    ── audit ── verify ──┤── 確認済み finding を統合
performance ── audit ── verify ──┤
style       ── audit ── verify ──┘
```

1. **Review** — 各 dimension の auditor が構造化 findings を返します（きれいな机 → 混線が減る）。
2. **Verify** — 各 finding を敵対的チェッカーへ（verify stage 内で `parallel`）。書いた本人が審判を兼ねない。
3. 本物とされたものだけ残し、severity で並べます。

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"{len(confirmed)} 件の実在する問題を確認")
    return {"confirmed": confirmed}
```

## s15 へのつなぎ方

s15 は依然として host loop です。s16 が足すのは一つの tool、`Workflow` だけです。モデル（またはあなた）が saved name を渡し、adapter が registry を解決して script を走らせます。

| | Claude Code / Pi（製品） | この teaching CLI |
|--|--------------------------|-------------------|
| Script 言語 | サンドボックス内の JavaScript | 読める Python 関数 |
| Dynamic 入口 | モデルが `script` を書く / `scriptPath` を編集 | 文書で説明。デモは saved の `name` |
| 実行中の host | バックグラウンド + 通知でセッションが応答し続ける | 観察しやすいよう `demo` / `resume` は前景 |
| アイデア | 同じ primitives、journal、prefix resume | teaching model — 簡略化は明示する |

main loop が workflow エンジンになるわけではありません。`bash` や `task` を借りるのと同じく、tool をひとつ借ります。

## 近所: 計画を握っているのは誰か

Workflow は「agent を増やす」ことではありません。**トポロジーを誰が持つか**を変えます。

| 近所 | 計画を握るもの | 中間結果の置き場 | 向いている用途 |
|------|----------------|------------------|----------------|
| [s06 Subagent](../s06_subagent/) | モデル、一度きり | 最終 summary 以外は捨てる | 汚い子タスクを隔離 |
| [s13 Agent Teams](../s13_agent_teams/) | Lead モデルがターンごと + mailbox | 共有タスク / メッセージ | 長時間の同僚、人間らしい協働 |
| [s15 Integrated Harness](../s15_integrated_harness/) | 一つのループ内のモデル | 会話 `messages[]` | 積み上げ型の coding agent |
| **s16 Workflow** | **Script** | **Script 変数 + journal** | 既知 / 大規模な構造化 fan-out + verify |
| [s17 Goal Loop](../s17_goal_loop/) | 停止境界の evaluator | 会話を証拠にする | 「ゴール全体は終わったか？」 |

より安い代替もしばしば勝ちます。skill / prompt を軟らかい計画にする、短い multi-agent チャット、手書きの static SDK orchestrator、あるいは単に大きな一回のモデルターン。単一 context より長く構造を保ちたいときに workflow へ手を伸ばします —— 審査員パネルが聞こえがいいからではありません。

## Workflow を*使わない*とき

Workflow は token と調整コストがかかります。ふつうのコーディングの大半は、5 人の reviewer パネルを**必要としません**。

聞いてください。この仕事は本当にもっと計算と定制 harness が要るか？ ふつうの s15 の一ターン（や一つの s06 subagent）で足りるなら、そこで止めます。抑制も設計思想の一部です —— 並行と専門化は、そのコストを回収しなければなりません。

## 試してみる

```bash
python s16_workflow_runtime/code.py          # s15 host + Workflow tool（real API）
python s16_workflow_runtime/code.py demo     # 固定 fixture: phase と agent を観察
python s16_workflow_runtime/code.py resume   # 同じ runId。prefix はすべて cache hit になるはず
```

見るポイント:

- `workflow_phase` が Review、続いて Verify
- 各 `workflow_agent` が初回は `done`、完全 resume では `cached`
- 末尾の短い confirmed リスト。全 hit の resume は `agents=0 tokens=0`

## s15 との対比 → 次は s17

| | s15 Integrated Harness | s16 Workflow Runtime |
|--|------------------------|----------------------|
| loop | 1 つ、モデル駆動 | 同じ loop。1 つの tool が script を実行 |
| 次の step を決めるもの | モデルが毎ラウンド | script がバッチの形を持つ |
| multi-agent | 一度きりの subagent | script 化・再開可能な `agent()` |
| 失敗 / resume | 会話メモリ頼り | null 分離 + journal prefix |

**s16 = バッチの回し方。s17 = ゴール全体が終わったかどうか。**

[s17 Goal Loop](../s17_goal_loop/) は独立した評価器に聞きます。止めるべきか、もう一ターンか。繰り返せる workflow に硬い完了条件も要るときは、そちらと組み合わせます。

<!-- translation-sync: zh@v12, en@v12, ja@v12 -->
