# s17: Autonomous Agents

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > [ s17 ] > s18 > s19`

> *本当にチームらしくなる瞬間は、人数が増えたときではなく、空いている teammate が次の仕事を自分で拾えるようになったときです。*

## この章が解く問題

`s16` まで来ると、チームにはすでに次のものがあります。

- 長く生きる teammate
- inbox
- protocol request / response
- task board

それでも、まだ 1 つ大きな詰まりが残っています。

**仕事の割り振りが lead に集中しすぎることです。**

たとえば task board に ready な task が 10 個あっても、

- Alice はこれ
- Bob はこれ
- Charlie はこれ

と lead が 1 件ずつ指名し続けるなら、team は増えても coordination の中心は 1 人のままです。

この章で入れるのは、

**空いている teammate が、自分で board を見て、取ってよい task を安全に claim する仕組み**

です。

## 併読すると楽になる資料

- teammate / task / runtime slot の境界が怪しくなったら [`team-task-lane-model.md`](./team-task-lane-model.md)
- `auto-claim` を読んで runtime record の置き場所が曖昧なら [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)
- 長期 teammate と一回限りの subagent の違いが薄れたら [`entity-map.md`](./entity-map.md)

## 先に言葉をそろえる

### 自治とは何か

ここで言う `autonomous` は、

> 何の制御もなく勝手に暴走すること

ではありません。

正しくは、

> 事前に与えたルールに従って、空いている teammate が次の仕事を自分で選べること

です。

つまり自治は自由放任ではなく、**規則付きの自律再開**です。

### claim とは何か

`claim` は、

> まだ owner が付いていない task を「今から自分が担当する」と確定させること

です。

「見つける」だけでは不十分で、**owner を書き込み、他の teammate が同じ task を取らないようにする**ところまでが claim です。

### idle とは何か

`idle` は終了でも停止でもありません。

意味は次の通りです。

> 今この teammate には active work がないが、まだ system の中で生きていて、新しい input を待てる状態

です。

## 最小心智モデル

この章を最も簡単に捉えるなら、teammate の lifecycle を 2 フェーズで見ます。

```text
WORK
  |
  | 今の作業を終える / idle を選ぶ
  v
IDLE
  |
  +-- inbox に新着がある -> WORK
  |
  +-- task board に claimable task がある -> claim -> WORK
  |
  +-- 一定時間なにもない -> shutdown
```

ここで大事なのは、

**main loop を無限に回し続けることではなく、idle 中に何を見て、どの順番で resume するか**

です。

## この章の核になるデータ構造

### 1. Claimable Predicate

最初に理解すべきなのは、

> どんな task なら「この teammate が今 claim してよい」と判定できるのか

です。

教材コードでは、判定は単に `status == "pending"` では終わりません。

```python
def is_claimable_task(task: dict, role: str | None = None) -> bool:
    return (
        task.get("status") == "pending"
        and not task.get("owner")
        and not task.get("blockedBy")
        and _task_allows_role(task, role)
    )
```

この 4 条件はそれぞれ別の意味を持ちます。

- `status == "pending"`: まだ開始していない
- `not owner`: まだ誰も担当していない
- `not blockedBy`: 前提 task が残っていない
- `_task_allows_role(...)`: この teammate の role が claim policy に合っている

最後の条件が特に重要です。

task は今の教材コードでは次のような role 制約を持てます。

- `claim_role`
- `required_role`

たとえば、

```python
{
    "id": 7,
    "subject": "Implement login page",
    "status": "pending",
    "owner": "",
    "blockedBy": [],
    "claim_role": "frontend",
}
```

なら、空いている teammate 全員が取れるわけではありません。

**frontend role の teammate だけが claim 候補になります。**

### 2. Claim 後の TaskRecord

claim が成功すると、task record は少なくとも次のように更新されます。

```python
{
    "id": 7,
    "owner": "alice",
    "status": "in_progress",
    "claimed_at": 1710000000.0,
    "claim_source": "auto",
}
```

この中で初心者が見落としやすいのは `claimed_at` と `claim_source` です。

- `claimed_at`: いつ取られたか
- `claim_source`: 手動か自動か

これがあることで system は、

- 今だれが担当しているか
- その担当は lead の指名か
- それとも idle scan による auto-claim か

をあとから説明できます。

### 3. Claim Event Log

task file の更新だけでは、今の最終状態しか見えません。

そこでこの章では claim 操作を別の append-only log にも書きます。

```text
.tasks/claim_events.jsonl
```

中身のイメージはこうです。

```python
{
    "event": "task.claimed",
    "task_id": 7,
    "owner": "alice",
    "role": "frontend",
    "source": "auto",
    "ts": 1710000000.0,
}
```

この log があると、

- task がいつ取られたか
- 誰が取ったか
- 手動か自動か

が current state とは別に追えます。

### 4. Durable Request Record

`s17` は autonomy を追加する章ですが、`s16` の protocol line を捨てる章ではありません。

そのため shutdown や plan approval の request は引き続き disk に保存されます。

```text
.team/requests/{request_id}.json
```

これは重要です。

なぜなら autonomous teammate は、

> protocol を無視して好きに動く worker

ではなく、

> 既存の protocol system の上で、idle 時に自分で次の仕事を探せる teammate

だからです。

### 5. Identity Block

compact の後や idle からの復帰直後は、teammate が自分の identity を見失いやすくなります。

そのため教材コードには identity block の再注入があります。

```python
{
    "role": "user",
    "content": "<identity>You are 'alice', role: frontend, team: default. Continue your work.</identity>",
}
```

さらに短い assistant acknowledgement も添えています。

```python
{"role": "assistant", "content": "I am alice. Continuing."}
```

この 2 行は装飾ではありません。

ここで守っているのは次の 3 点です。

- 私は誰か
- どの role か
- どの team に属しているか

## 最小実装を段階で追う

### 第 1 段階: WORK と IDLE を分ける

まず teammate loop を 2 フェーズに分けます。

```python
while True:
    run_work_phase(...)
    should_resume = run_idle_phase(...)
    if not should_resume:
        break
```

これで初めて、

- いま作業中なのか
- いま待機中なのか
- 次に resume する理由は何か

を分けて考えられます。

### 第 2 段階: idle では先に inbox を見る

`idle` に入ったら最初に見るべきは task board ではなく inbox です。

```python
def idle_phase(name: str, messages: list) -> bool:
    inbox = bus.read_inbox(name)
    if inbox:
        messages.append({
            "role": "user",
            "content": json.dumps(inbox),
        })
        return True
```

理由は単純で、

**明示的に自分宛てに来た仕事の方が、board 上の一般 task より優先度が高い**

からです。

### 第 3 段階: inbox が空なら role 付きで task board を走査する

```python
unclaimed = scan_unclaimed_tasks(role)
if unclaimed:
    task = unclaimed[0]
    claim_result = claim_task(
        task["id"],
        name,
        role=role,
        source="auto",
    )
```

ここでの要点は 2 つです。

- `scan_unclaimed_tasks(role)` は role を無視して全件取るわけではない
- `source="auto"` を書いて claim の由来を残している

つまり自治とは、

> 何でも空いていれば奪うこと

ではなく、

> role、block 状態、owner 状態を見たうえで、今この teammate に許された仕事だけを取ること

です。

### 第 4 段階: claim 後は identity と task hint を両方戻す

claim 成功後は、そのまま resume してはいけません。

```python
ensure_identity_context(messages, name, role, team_name)
messages.append({
    "role": "user",
    "content": f"<auto-claimed>Task #{task['id']}: {task['subject']}</auto-claimed>",
})
messages.append({
    "role": "assistant",
    "content": f"{claim_result}. Working on it.",
})
return True
```

この段で context に戻しているのは 2 種類の情報です。

- identity: この teammate は誰か
- fresh work item: いま何を始めたのか

この 2 つがそろって初めて、次の WORK phase が迷わず進みます。

### 第 5 段階: 長時間なにもなければ shutdown する

idle teammate を永久に残す必要はありません。

教材版では、

> 一定時間 inbox も task board も空なら shutdown

という単純な出口で十分です。

ここでの主眼は resource policy の最適化ではなく、

**idle からの再開条件と終了条件を明示すること**

です。

## なぜ claim は原子的でなければならないか

`atomic` という言葉は難しく見えますが、ここでは次の意味です。

> claim 処理は「全部成功する」か「起きない」かのどちらかでなければならない

理由は race condition です。

Alice と Bob が同時に同じ task を見たら、

- Alice も `owner == ""` を見る
- Bob も `owner == ""` を見る
- 両方が自分を owner として保存する

という事故が起こりえます。

そのため教材コードでも lock を使っています。

```python
with claim_lock:
    task = load(task_id)
    if task["owner"]:
        return "already claimed"
    task["owner"] = name
    task["status"] = "in_progress"
    save(task)
```

初心者向けに言い換えるなら、

**claim は「見てから書く」までを他の teammate に割り込まれずに一気に行う**

必要があります。

## identity 再注入が重要な理由

これは地味ですが、自治の品質を大きく左右します。

compact の後や long-lived teammate の再開時には、context 冒頭から次の情報が薄れがちです。

- 私は誰か
- 何 role か
- どの team か

この状態で work を再開すると、

- role に合わない判断をしやすくなる
- protocol 上の責務を忘れやすくなる
- それまでの persona がぶれやすくなる

だから教材版では、

> idle から戻る前、または compact 後に identity が薄いなら再注入する

という復帰ルールを置いています。

## `s17` は `s16` を上書きしない

ここは誤解しやすいので強調します。

`s17` で増えるのは autonomy ですが、だからといって `s16` の protocol layer が消えるわけではありません。

両者はこういう関係です。

```text
s16:
  request_id を持つ durable protocol

s17:
  idle teammate が board を見て次の仕事を探せる
```

つまり `s17` は、

**protocol がある team に autonomy を足す章**

であって、

**自由に動く worker 群へ退化させる章**

ではありません。

## 前の章とどうつながるか

この章は前の複数章が初めて強く結びつく場所です。

- `s12`: task board を作る
- `s15`: persistent teammate を作る
- `s16`: request / response protocol を作る
- `s17`: 指名がなくても次の work を自分で取れるようにする

したがって `s17` は、

**受け身の team から、自分で回り始める team への橋渡し**

と考えると分かりやすいです。

## 自治するのは long-lived teammate であって subagent ではない

ここで `s04` と混ざる人が多いです。

この章の actor は one-shot subagent ではありません。

この章の teammate は次の特徴を持ちます。

- 名前がある
- role がある
- inbox がある
- idle state がある
- 複数回 task を受け取れる

一方、subagent は通常、

- 一度 delegated work を受ける
- 独立 context で処理する
- summary を返して終わる

という使い方です。

また、この章で claim する対象は `s12` の task であり、`s13` の runtime slot ではありません。

## 初学者が混ぜやすいポイント

### 1. `pending` だけ見て `blockedBy` を見ない

task が `pending` でも dependency が残っていればまだ取れません。

### 2. role 条件を無視する

`claim_role` や `required_role` を見ないと、間違った teammate が task を取ります。

### 3. claim lock を置かない

同一 task の二重 claim が起こります。

### 4. idle 中に board しか見ない

これでは明示的な inbox message を取りこぼします。

### 5. event log を書かない

「いま誰が持っているか」は分かっても、

- いつ取ったか
- 自動か手動か

が追えません。

### 6. idle teammate を永遠に残す

教材版では shutdown 条件を持たせた方が lifecycle を理解しやすくなります。

### 7. compact 後に identity を戻さない

長く動く teammate ほど、identity drift が起きやすくなります。

## 教学上の境界

この章でまず掴むべき主線は 1 本です。

**idle で待つ -> 安全に claim する -> identity を整えて work に戻る**

ここで学ぶ中心は自治の骨格であって、

- 高度な scheduler 最適化
- 分散環境での claim
- 複雑な fairness policy

ではありません。

その先へ進む前に、読者が自分の言葉で次の 1 文を言えることが大切です。

> autonomous teammate とは、空いたときに勝手に暴走する worker ではなく、inbox と task board を規則通りに見て、取ってよい仕事だけを自分で取りにいける長期 actor である。
