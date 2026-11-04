# s17: Goal Loop：モデルが停止を提案し、独立した evaluator が継続するかを決める

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s15 → [s16](../s16_workflow_runtime/) → `s17`

> *「モデルが tool call をやめたのは、一つの turn を止めたいという意味にすぎない。goal 全体が完了したかは別の evaluator が判断する。」*
>
> **Harness layer：継続実行。** 各 turn の終わりで完了条件を確認し、未完了なら次の turn を始めます。

---

![Goal Loop 全体像](images/goal-loop-overview.svg)

s01 から、agent loop の終了条件は単純でした。モデルが tool を呼ばなくなったら、program は return します。

通常の会話には十分ですが、「すべての test が通るまで直す」「acceptance criteria をすべて満たす」といった task では足りないことがあります。モデルは一部を終えただけで、作業全体が完了したと考えるかもしれません。新しい `tool_use` がないことは、現在の turn が終わったことを示すだけで、goal 全体の達成までは証明しません。

`/goal` は本当に return する前に、独立した判断を一つ追加します。

## /goal は session-scoped Stop hook

次のように入力します。

```text
/goal pytest tests/auth が exit code 0 で終了し、lint error もない
```

program は完了条件を保存し、その条件を現在の task としてすぐ main model に渡します。「作業を開始して」と別の prompt を送る必要はありません。

main model が tool call をやめると、loop は return の前に Goal Stop hook を実行します。

```python
if tool_results:
    messages.append({"role": "user", "content": tool_results})
    continue

decision = await self.goal.evaluate_after_turn(self.messages)
if decision.action == "block":
    self.messages.append({
        "role": "user",
        "content": decision.reason,
    })
    continue

return SessionResult(text=text, status=decision.action)
```

active Goal がなければ hook はそのまま stop を許可し、return 条件は s01 と同じです。

## evaluator と作業モデルを分ける

main model はコードを変更し、command を実行し、問題を解決します。Goal evaluator は別の model call であり、完了条件の判断だけを担当します。

evaluator は `GoalController` が持つ Goal Gate 内部の依存です。main loop の外にある別の終了経路ではありません。

この章には独立した `CommandQueue` がありません。評価が停止を block すると、controller は理由を同じ `messages[]` へ直接追加し、次の turn を始めます。より大きな host では user input、background result、continuation command を session へ戻す共有 queue を使えますが、それは host 全体の transport であり、Goal Gate が所有する部品ではありません。Gate の中へ描くと、「誰が判断するか」と「判断をどの経路で戻すか」が混ざります。

evaluator が見るものは次の三つです。

- active Goal の条件；
- 現在までの conversation；
- worker が conversation に書き戻した tool result。

evaluator は tool を持ちません。file を読んだり、test を再実行したりはできません。conversation にすでに現れた内容だけで判断します。

```json
{
  "ok": false,
  "reason": "conversation に pytest の exit code がまだありません",
  "impossible": false
}
```

`ok=true` は条件を満たしたことを表します。`ok=false` なら次の turn が必要です。task を完了できない状況なら `impossible=true` を返せます。

## conversation が判断材料になる

evaluator は現在の conversation を読みます。tool result、worker の説明、background task notification はすべて message として入り、判断はそれらに実際に何が書かれているかで決まります。

evaluator への入力は直近の完全な message を残します。最新の 1 message だけで長すぎる場合は、その先頭と末尾を残し、1 件の tool result が判断 request 全体を埋めないようにします。

だからといって、根拠のない「tests passed」を必ず受け入れるわけではありません。evaluator prompt は conversation にある具体的な結果に基づくよう求め、報告されていない command の成功を仮定しないよう指示します。

それでも text を読むモデルであるため、重要な結果が conversation に明確に現れているかが reliability を左右します。worker の system prompt には次の方針を入れます。

> verification command を実行したら、独立した evaluator が確認できるよう、command と result を明確に報告する。

Goal Loop は test framework ではありません。実際の verification は tool が行います。Goal evaluator は、その結果が現在の作業記録に現れているかを判断するだけです。

## 良い完了条件は確認できる

「コードを良くする」だけでは曖昧で、evaluator は何をもって良いとするか判断できません。

有用な条件には三つの情報があります。

1. **End state：** 完了時に何が成立しているべきか；
2. **Check：** どの command や output がそれを証明するか；
3. **Constraints：** 作業中に壊してはいけないものは何か。

例えば：

```text
/goal authentication migration を完了し、pytest tests/auth が exit code 0 になり、
tests/auth 以外の test file は変更しない
```

自動実行の turn 数を制限したい場合は、Goal の内部に固定 budget を隠さず、main loop の global turn limit を使います。

```bash
MAX_TURNS=20 python s17_goal_loop/code.py \
  "/goal npm run typecheck が exit code 0 になるまで type error を修正する"
```

## 未完了なら同じ loop に戻る

条件が未達の場合、evaluator は短い理由を返します。

```text
完全な test result がありません。pytest tests/auth を実行し、exit code を報告してください。
```

program はその理由を `messages[]` に追加し、現在の `while` loop で `continue` します。user が「続けて」と入力しなくても、main model は次の turn を始めます。

別の continuation queue はありません。Goal evaluation は loop の return 境界で行われ、未完了の作業も同じ場所から loop に戻ります。

## background work が終わる前には判断しない

Workflow、background command、その他の async task は、main model の turn が終わっても実行中かもしれません。

重要な結果が conversation に戻っていない状態で判断するのは早すぎます。Goal Stop hook は `defer` を返し、Goal を active のまま残して evaluator call を省きます。task が完了すると、host は completion message を `submit_background_result()` に渡します。その message が同じ `messages[]` に入り、loop が再開します。

Workflow notification に機械的な特権はありません。他の message と同じように conversation に入り、evaluator が中身の実際の結果を確認します。

## 自動継続にも出口が必要

Goal には隠れた「default 20 turn budget」はありません。完了条件は各 turn のあとに evaluator が改めて判断します。

ただし、一つの request を永久に占有する仕組みにはできません。この章では Goal の外側に二つの共通出口を残します。

- main loop の global `max_turns`；
- Stop hook が連続で stop を拒否できる回数の上限。

上限に達したら user に control を返します。goal を完了扱いにはせず、勝手に clear もしません。user は status を確認し、情報を追加して続けるか、goal を clear できます。

evaluator call が失敗した場合も同じです。自動継続を止め、goal を active のまま残し、判断できないのに成功と報告せず error を返します。

## 確認、置換、clear

一つの session に active Goal は一つだけです。

```text
/goal
```

現在の条件、経過時間、evaluation 回数、main Agent の token 使用量、直近の evaluator reason を表示します。

```text
/goal 新しい完了条件
```

以前の Goal を置き換え、新しい条件ですぐ作業を始めます。

```text
/goal clear
```

active Goal を clear します。`stop`、`off`、`reset`、`none`、`cancel` も alias として利用できます。

`GoalController.restore()` は、host が保存した `goal_status` event から active Goal を復元できます。この章の CLI は session 全体を永続化しません。完了、失敗、clear 済みの Goal は再起動しません。条件は引き継ぎますが、turn count、経過時間、token baseline は新しく計算します。

## コードに追加したもの

これは S04 Kernel を土台にした独立 mechanism の例です。5 つの base tools と 4 種類の hooks を保ち、Goal 用の 4 部品を追加します。

| 部品 | 役割 |
|---|---|
| `GoalState` | 条件、evaluation 回数、開始時刻、直近の理由を保存する |
| `PromptGoalEvaluator` | 独立した model call で conversation を判断する |
| `GoalController` | Goal の設定、確認、clear と Stop hook を担当する |
| `AgentSession` | 元の return 境界へ Goal 判断を接続する |

接続箇所は数行です。

```python
decision = await self.goal.evaluate_after_turn(self.messages)
if decision.action == "block":
    continue
return SessionResult(text=text, status=decision.action)
```

## 実行してみる

dependency を install し、`.env` を準備します。

```bash
pip install -r requirements.txt

# .env
ANTHROPIC_API_KEY=...
MODEL_ID=...

# optional: Goal evaluator に小さな model を使う
GOAL_EVALUATOR_MODEL_ID=...
```

interactive session を開始します。

```bash
python s17_goal_loop/code.py
```

次に入力します。

```text
/goal python -m pytest が exit code 0 で終了する
```

command line から直接 Goal を設定することもできます。

```bash
python s17_goal_loop/code.py "/goal python -m pytest が exit code 0 で終了する"
```

## s16 との関係

s16 は「複数の仕事をどう実行するか」を扱いました。どの step を並列化し、結果をどう検証し、中断後にどう resume するかを決めます。

s17 は「task 全体が完了したか」を扱います。Workflow が正常に終了しても、user の最終要件をまだ満たしていないかもしれません。Workflow result が conversation に入ったあと、Goal evaluator が session を止めるか続けるかを決めます。

どちらも単独で利用できます。同じ host に接続すると、Workflow の completion message が conversation に入り、Goal Loop が task 全体を続けるか判断します。

<!-- translation-sync: zh@v6, en@v6, ja@v6 -->
