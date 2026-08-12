# s16: Workflow Runtime — オーケストレーションをコードに書く

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

[s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *計画をチャットの中だけに置かない。* 順番はスクリプトが持ち、一歩ごとの判断はモデルが持つ。
>
> **Harness 層**: オーケストレーション — 単一 agent ループの上で、マルチ agent スクリプトを走らせる。

## 問題

あなたはすでに、ひとつのループの中でモデルにファイルを読ませ、コードを直し、エラーを見させることができます。ところが仕事によっては、**順番が最初から分かっている**ものがあります。次元ごとにレビューし、次に意地悪な検証、最後にまとめる——という具合です。その順番をチャットの記憶にだけ預けていると、モデルは途中で「完了」と言い、自分の宿題を甘く採点し、圧縮を何度か経ると「X を触るな」さえ消えます。

柔らかい会話は、並列も、結果の形の安定も、落ちてからの再開も支えきれません。もっとおしゃべりの上手なモデルが欲しいのではありません。**書き下ろされたオーケストレーション**が欲しいのです。

## 解決策

```text
  あなたの会話 ──► Workflow(...) ──► 結果が一条で戻る
                    │
                    ▼
            スクリプト: agent / pipeline / parallel
                    │
                    ▼
              変数 + journal（半成品はここに。スレに詰め込まない）
```

ヘルパー（サブ agent）は相変わらず考えます。**スクリプト**がループ・分配・マージを持ちます。中間結果は変数と journal に置き、親の対話には入れません。

一言でいうと：**オーケストレーションを「知性」から「構造」へ移す。**

![静的 harness と動的 workflow](images/dynamic-vs-static.png)

*左：汎用の固定パイプライン。右：このタスク向けに裁断したオーケストレーション。*

Claude Code には二つの扉があります。**動的**——モデルがこのタスク用に JS を書く（`script` / `scriptPath`）。**保存済み**——良いスクリプトを `name` + `args` で再実行。外側には SDK で先に書き切る静的オーケストレーションもあります。本章は **Python の教材用 runtime**（JS VM なし）です。考えは揃え、デモは「保存済み」の扉を使います。製品ではモデルはスクリプトを出せます——ここでは JS を走らせないだけです。

## 仕組み

**1. 三つの動詞**

```text
  agent      一人のヘルパー、一件の仕事（schema で次に渡せる JSON も可）
  pipeline   各 item が自分の段階を進む（既定。同期しない）
  parallel   全部揃ってから先へ（バリア。多用しない）
```

失敗時：`parallel` のその枠は `null`。`pipeline` はその item を捨てます。艦隊は丸ごと沈みません。マージ前にフィルタしてください。

**2. 再開はノートで。チャット記憶ではない**

journal は `agent()` の**呼び出し順**で記帳します。再開は最長の未変更プレフィックスを再生し、最初の変更から先は全部ライブです。本番の JS runtime は `Date.now()` / `Math.random()` を禁じます——ノートがずれないように。教材スクリプトも決定的に書いてください。

```text
  journal  [A] [B] [C] [D]
  再開      命中 命中 ✂ ライブ
```

**3. サンプル一つ：Fanout + Adversarial**

`review-changes` は「一つのパターン」ではありません。**Fanout** の中に **Adversarial** が入ります。次元ごとに `pipeline(audit, verify)`、検証で `parallel` に意地悪させ、残った finding だけ残します。

```text
  correctness ── 監査 ── 検証 ──┐
  security    ── 監査 ── 検証 ──┤── confirmed
  performance ── 監査 ── 検証 ──┤
  style       ── 監査 ── 検証 ──┘
```

```python
# code.py 抜粋 — 形だけ見ればよい
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [f for r in results if r for f in r["confirmed"]]
    return {"confirmed": confirmed}
```

艦隊は早逃げできず、著者は自分の審判にならず、トポロジも疲れたチャットのたびに書き換わりません。

<details>
<summary>よくある六つの形（パターン庫）</summary>

![六種 Workflow モード](images/six-workflow-patterns.png)

| パターン | 人の言葉 | 原語のスケッチ |
|------|------|----------|
| Classify-And-Act | 仕分けしてから適任へ | `agent` → 分岐 → `agent` |
| Fanout-And-Synthesize | 分けてやり、またまとめる | `pipeline` / `parallel` → 統合 |
| Adversarial Verification | 狐に鶏小屋を採点させない | 産出 → `parallel(verify)` → フィルタ |
| Generate-And-Filter | まず多く作り、それから篩 | `parallel(gens)` → フィルタ |
| Tournament | 一対一で優勝を決める | 審判 `agent` |
| Loop Until Done | 「まだ新しい？」なら続ける | `while` + 停止 + `budget` |

`review-changes` ≈ Fanout + Adversarial。調査系はよく 分配 → フィルタ → 検証 → 統合 と積みます。

</details>

<details>
<summary>動的 / 保存済み / 静的と公式原語図</summary>

```python
# 教材スケッチ
Workflow({ "name": "review-changes", "args": { "changes": "..." } })
# Claude Code はさらに: script | scriptPath | resumeFromRunId
```

![Workflow 原語](images/workflow-primitives.png)

</details>

<details>
<summary>信頼できない入力：読み書きを隔離</summary>

チケットを読む agent が、同時に PR を開ける鍵を持ってはいけません。読み手は読むだけ → 要約。信頼側は要約だけ見て動きます。

```text
  バックログ → [隔離: 読 / 重複除去 / 要約] → [信頼: 実行]
```

![隔離分流](images/quarantine-triage.png)

</details>

計画を握るのは誰か。s06 は一回きりの委譲、s13 はメール箱つきの仲間、s15 は単一ループのチャット、**s16 はスクリプト + journal**、s17 は入り口で「全体は終わったか」と聞きます。普通の数ファイルの修正なら s15 か一つの s06 で足りることが多い。Workflow は token と調整のコストが要ります——**構造が一度の会話より長生きしなければならない**ときだけ手を伸ばしてください。

## 試してみる

```bash
python s16_workflow_runtime/code.py demo
python s16_workflow_runtime/code.py resume
```

一回目は Review → Verify を見てください。同じ run の二回目は `cached` がほとんど（理想は `agents=0 tokens=0`）。完全なホストに載せるなら引数なしで `code.py` を。

s15 はあいかわらずそのループです。ここに増えるのは `Workflow` ツールだけ。[s17](../s17_goal_loop/) は別の問いをします。もう止まっていい？

<!-- translation-sync: zh@v19, en@v19, ja@v19 -->
