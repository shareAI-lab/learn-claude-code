# s03: TodoWrite

`s00 > s01 > s02 > [ s03 ] > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *planning は model の代わりに考えるためのものではありません。いま何をやっているかを、外から見える state にするためのものです。*

## この章が解く問題

`s02` まで来ると agent はすでに、

- file を読む
- file を書く
- command を実行する

ことができます。

するとすぐに別の問題が出ます。

- multi-step task で一歩前の確認を忘れる
- もう終えた確認をまた繰り返す
- 最初は計画しても、数 turn 後には即興に戻る

これは model が「考えられない」からではありません。

問題は、

**現在の plan を explicit に置いておく stable state がないこと**

です。

この章で足すのはより強い tool ではなく、

**今の session で何をどの順で進めているかを外部状態として見えるようにする仕組み**

です。

## 先に言葉をそろえる

### session 内 planning とは何か

ここで扱う planning は long-term project management ではありません。

意味は、

> 今回の user request を終えるために、直近の数手を外へ書き出し、途中で更新し続けること

です。

### todo とは何か

`todo` は特定 product の固有名詞として覚える必要はありません。

この章では単に、

> model が current plan を更新するための入口

として使います。

### active step とは何か

`active step` は、

> いま本当に進めている 1 手

です。

教材版では `in_progress` で表します。

ここで狙っているのは形式美ではなく、

**同時にあれもこれも進めて plan をぼかさないこと**

です。

### reminder とは何か

reminder は model の代わりに plan を作るものではありません。

意味は、

> 数 turn 連続で plan 更新を忘れたときに、軽く plan へ意識を戻すナッジ

です。

## 最初に強調したい境界

この章は task system ではありません。

`s03` で扱うのは、

- session 内の軽量な current plan
- 進行中の focus を保つための外部状態
- turn ごとに書き換わりうる planning panel

です。

ここでまだ扱わないもの:

- durable task board
- dependency graph
- multi-agent 共有 task graph
- background runtime task manager

それらは `s12-s14` であらためて教えます。

この境界を守らないと、初心者はすぐに次を混同します。

- 今この session で次にやる一手
- system 全体に長く残る work goal

## 最小心智モデル

この章を最も簡単に捉えるなら、plan はこういう panel です。

```text
user が大きな仕事を頼む
  |
  v
model が今の plan を書き出す
  |
  v
plan state
  - [ ] まだ着手していない
  - [>] いま進めている
  - [x] 完了した
  |
  v
1 手進むたびに更新する
```

つまり流れはこうです。

1. まず current work を数手に割る
2. 1 つを `in_progress` にする
3. 終わったら `completed` にする
4. 次の 1 つを `in_progress` にする
5. しばらく更新がなければ reminder する

この 5 手が見えていれば、この章の幹はつかめています。

## この章の核になるデータ構造

### 1. PlanItem

最小の item は次のように考えられます。

```python
{
    "content": "Read the failing test",
    "status": "pending" | "in_progress" | "completed",
    "activeForm": "Reading the failing test",
}
```

意味は単純です。

- `content`: 何をするか
- `status`: いまどの段階か
- `activeForm`: 実行中に自然文でどう見せるか

教材コードによっては `id` や `text` を使っていても本質は同じです。

### 2. PlanningState

item だけでは足りません。

plan 全体には最低限、次の running state も要ります。

```python
{
    "items": [...],
    "rounds_since_update": 0,
}
```

`rounds_since_update` の意味は、

> 何 turn 連続で plan が更新されていないか

です。

この値があるから reminder を出せます。

### 3. 状態制約

教材版では次の制約を置くのが有効です。

```text
同時に in_progress は最大 1 つ
```

これは宇宙の真理ではありません。  
でも初学者にとっては非常に良い制約です。

理由は単純で、

**current focus を system 側から明示できる**

からです。

## 最小実装を段階で追う

### 第 1 段階: plan manager を用意する

```python
class TodoManager:
    def __init__(self):
        self.items = []
```

最初はこれで十分です。

ここで導入したいのは UI ではなく、

> plan を model の頭の中ではなく harness 側の state として持つ

という発想です。

### 第 2 段階: plan 全体を更新できるようにする

教材版では item をちまちま差分更新するより、

**現在の plan を丸ごと更新する**

方が理解しやすいです。

```python
def update(self, items: list) -> str:
    validated = []
    in_progress_count = 0

    for item in items:
        status = item.get("status", "pending")
        if status == "in_progress":
            in_progress_count += 1

        validated.append({
            "content": item["content"],
            "status": status,
            "activeForm": item.get("activeForm", ""),
        })

    if in_progress_count > 1:
        raise ValueError("Only one item can be in_progress")

    self.items = validated
    return self.render()
```

ここでやっていることは 2 つです。

- current plan を受け取る
- 状態制約をチェックする

### 第 3 段階: render して可読にする

```python
def render(self) -> str:
    lines = []
    for item in self.items:
        marker = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
        }[item["status"]]
        lines.append(f"{marker} {item['content']}")
    return "\n".join(lines)
```

render の価値は見た目だけではありません。

plan が text として安定して見えることで、

- user が current progress を理解しやすい
- model も自分が何をどこまで進めたか確認しやすい

状態になります。

### 第 4 段階: `todo` を 1 つの tool として loop へ接ぐ

```python
TOOL_HANDLERS = {
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "bash": run_bash,
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

ここで重要なのは、plan 更新を特別扱いの hidden logic にせず、

**tool call として explicit に loop へ入れる**

ことです。

### 第 5 段階: 数 turn 更新がなければ reminder を挿入する

```python
if rounds_since_update >= 3:
    results.insert(0, {
        "type": "text",
        "text": "<reminder>Refresh your plan before continuing.</reminder>",
    })
```

この reminder の意味は「system が代わりに plan を立てる」ではありません。

正しくは、

> plan state がしばらく stale なので、model に current plan を更新させる

です。

## main loop に何が増えるのか

この章以後、main loop は `messages` だけを持つわけではなくなります。

持つ state が少なくとも 2 本になります。

```text
messages
  -> model が読む会話と観察の history

planning state
  -> 今回の session で current work をどう進めるか
```

これがこの章の本当の upgrade です。

agent はもはや単に chat history を伸ばしているだけではなく、

**「いま何をしているか」を外から見える panel として維持する**

ようになります。

## なぜここで task graph まで教えないのか

初心者は planning の話が出るとすぐ、

> だったら durable task board も同時に作った方がよいのでは

と考えがちです。

でも教学順序としては早すぎます。

理由は、ここで理解してほしいのが

**session 内の軽い plan と、長く残る durable work graph は別物**

という境界だからです。

`s03` は current focus の外部化です。  
`s12` 以降は durable task system です。

順番を守ると、後で混ざりにくくなります。

## 初学者が混ぜやすいポイント

### 1. plan を model の頭の中だけに置く

これでは multi-step work がすぐ漂います。

### 2. `in_progress` を複数許してしまう

current focus がぼやけ、plan が checklist ではなく wish list になります。

### 3. plan を一度書いたら更新しない

それでは plan は living state ではなく dead note です。

### 4. reminder を system の強制 planning と誤解する

reminder は軽いナッジであって、plan の中身を system が代行するものではありません。

### 5. session plan と durable task graph を同一視する

この章で扱うのは current request を進めるための軽量 state です。

## この章を読み終えたら何が言えるべきか

1. planning は model の代わりに考えることではなく、current progress を外部 state にすること
2. session plan は durable task system とは別層であること
3. `in_progress` を 1 つに絞ると初心者の心智が安定すること

## 一文で覚える

**TodoWrite とは、「次に何をするか」を model の頭の中ではなく、system が見える外部 state に書き出すことです。**
