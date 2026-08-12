# s16: Workflow Runtime — レシピをコードに書く

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *「ターンごとのチャットは、10 秒ごとにシェフへメールするようなものです。Workflow は厨房が従えるレシピです。」*
>
> **Harness 層**: Orchestration — single-agent loop の上で multi-agent script を実行します。

---

友だちとチャットだけで料理している場面を想像してください。「玉ねぎを切って」と送り、返事を待ち、「できた？」、次は「フライパンを……」。一品ならまだよいです。二十卓の宴会では、チャット自体がボトルネックになります。手順を忘れ、同じ指示を繰り返し、スマホが落ちたら最初からやり直しです。

ふつうの「モデルが指揮者」な会話も同じです。**Workflow** は書かれたレシピです。厨房（runtime）がそれに従い、助手（subagent）が判断し、途中の器はカウンターに置かれます —— グループチャットの中ではありません。

## 問題

s01 から s15 まで、各ラウンドでモデルが次の tool を選びます。直前の発見で次の道が変わるタスクには向いています。

一方、形が先に分かっている仕事もあります。

- 複数の観点で多くのファイルを review する
- 調査 → 検証 → 統合
- N 個のモジュールを同じやり方で移行する

計画を `messages[]` の中だけで「覚えている」と、三つのことが起きます。orchestration の雑音で context が埋まる、途中で計画がずれる、落ちたら完了済みの作業までやり直す。

必要なのは並行性、安定した結果の形、そして再開です。会話履歴だけにそれを預けるのは弱いです。

## 一息でいうアイデア

**計画をコードへ移します。** Subagent は相変わらず判断します。script がループ、扇状の分配、マージを持ちます。中間結果は変数にあり、会話には入りません。

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

1 回の `Workflow` tool call が、その script 実行を始めます。実行中に lifecycle / progress event が出て、最後に launch 情報・result・task state を含む tool result が返ります。

## ふたつの入口

Claude Code は、workflow の始め方について正直です。

| 入口 | 渡すもの | いつ使うか |
|------|----------|------------|
| **Dynamic** | オーケストレーション用の JavaScript（`script`、あとから `scriptPath`） | モデルが**このタスク用**にレシピを書く |
| **Saved** | `name` + `args` | 良いレシピを例えば `.claude/workflows/` に保存し、名前で再実行する |

厨房は同じです。Dynamic は「今レシピを書く」、Saved は「カード箱から引く」です。

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

4 つの review dimension が同じ 2 段階の道を通ります。

```text
correctness ── audit ── verify ──┐
security    ── audit ── verify ──┤── 確認済み finding を統合
performance ── audit ── verify ──┤
style       ── audit ── verify ──┘
```

1. **Review** — 各 dimension の auditor が構造化 findings を返します。
2. **Verify** — 各 finding を敵対的チェッカーへ（verify stage 内で `parallel`）。
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

[s17 Goal Loop](../s17_goal_loop/) は独立した評価器に聞きます。止めるべきか、もう一ターンか。

<!-- translation-sync: zh@v11, en@v11, ja@v11 -->
