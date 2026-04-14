# s15: Agent Teams

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > [ s15 ] > s16 > s17 > s18 > s19`

> *subagent は一回きりの委譲に向く。team system が解くのは、「誰かが長く online で残り、繰り返し仕事を受け取り、互いに協調できる」状態です。*

## この章が本当に解きたい問題

`s04` の subagent は、main agent が作業を小さく切り出すのに十分役立ちます。

ただし subagent には明確な境界があります。

```text
生成される
  ->
少し作業する
  ->
要約を返す
  ->
消える
```

これは一回きりの調査や短い委譲にはとても向いています。  
しかし、次のような system を作りたいときには足りません。

- テスト担当の agent を長く待機させる
- リファクタ担当とテスト担当を並行して持ち続ける
- ある teammate が後のターンでも同じ責任を持ち続ける
- lead が後で同じ teammate へ再び仕事を振る

つまり今不足しているのは「model call を 1 回増やすこと」ではありません。

不足しているのは:

**名前・役割・inbox・状態を持った、長期的に存在する実行者の集まり**

です。

## 併読のすすめ

- teammate と `s04` の subagent をまだ同じものに見てしまうなら、[`entity-map.md`](./entity-map.md) に戻ります。
- `s16-s18` まで続けて読むなら、[`team-task-lane-model.md`](./team-task-lane-model.md) を手元に置き、teammate、protocol request、task、runtime slot、worktree lane を混ぜないようにします。
- 長く生きる teammate と background 実行の runtime slot が混ざり始めたら、[`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) で goal / execution の境界を先に固めます。

## まず用語をはっきり分ける

### teammate とは何か

ここでの `teammate` は:

> 名前、役割、inbox、lifecycle を持ち、複数ターンにまたがって system 内へ残る agent

のことです。

重要なのは「賢い helper」ではなく、**持続する actor** だという点です。

### roster とは何か

`roster` は team member の名簿です。

少なくとも次を答えられる必要があります。

- 今 team に誰がいるか
- その人の role は何か
- その人は idle か、working か、shutdown 済みか

### mailbox とは何か

`mailbox` は各 teammate が持つ受信箱です。

他の member はそこへ message を送ります。  
受信側は、自分の次の work loop に入る前に mailbox を drain します。

この設計の利点は、協調が次のように見えることです。

- 誰が誰に送ったか
- どの member がまだ未読か
- どの message が actor 間通信なのか

## 最小心智モデル

この章をいちばん壊れにくく理解する方法は、各 teammate を次のように見ることです。

> 自分の `messages`、自分の mailbox、自分の agent loop を持った長期 actor

```text
lead
  |
  +-- spawn alice (tester)
  +-- spawn bob (refactorer)
  |
  +-- send message -> alice inbox
  +-- send message -> bob inbox

alice
  |
  +-- 自分の messages
  +-- 自分の inbox
  +-- 自分の agent loop

bob
  |
  +-- 自分の messages
  +-- 自分の inbox
  +-- 自分の agent loop
```

この章の一番大事な対比は次です。

- subagent: 一回きりの探索 helper
- teammate: 長く存在し続ける協調 member

## それまでの章にどう接続するか

`s15` は単に「人数を増やす章」ではありません。  
`s12-s14` でできた task / runtime / schedule の上に、**長く残る実行者層**を足す章です。

接続の主線は次です。

```text
lead が「長く担当させたい仕事」を見つける
  ->
teammate を spawn する
  ->
team roster に登録する
  ->
mailbox に仕事の手がかりや依頼を送る
  ->
teammate が自分の inbox を drain する
  ->
自分の agent loop と tools を回す
  ->
結果を message / task update として返す
```

ここで見失ってはいけない境界は 4 つです。

1. `s12-s14` が作ったのは work layer であり、ここでは actor layer を足している
2. `s15` の default はまだ lead 主導である
3. structured protocol は次章 `s16`
4. autonomous claim は `s17`

つまりこの章は、team system の中でもまだ:

- 名付ける
- 残す
- 送る
- 受け取る

という基礎層を作っている段階です。

## 主要データ構造

### `TeamMember`

```python
member = {
    "name": "alice",
    "role": "tester",
    "status": "working",
}
```

教学版では、まずこの 3 つが揃っていれば十分です。

- `name`: 誰か
- `role`: 何を主に担当するか
- `status`: 今どういう状態か

最初から大量の field を足す必要はありません。  
この章で大事なのは「長く存在する actor が立ち上がること」です。

### `TeamConfig`

```python
config = {
    "team_name": "default",
    "members": [member1, member2],
}
```

通常は次のような場所に置きます。

```text
.team/config.json
```

この record があると system は再起動後も、

- 以前誰がいたか
- 誰がどの role を持っていたか

を失わずに済みます。

### `MessageEnvelope`

```python
message = {
    "type": "message",
    "from": "lead",
    "to": "alice",
    "content": "Please review auth module.",
    "timestamp": 1710000000.0,
}
```

`envelope` は「本文だけでなくメタ情報も含めて包んだ 1 件の message record」です。

これを使う理由:

- sender が分かる
- receiver が分かる
- message type を分けられる
- mailbox を durable channel として扱える

## 最小実装の進め方

### Step 1: まず roster を持つ

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.team_dir = team_dir
        self.config_path = team_dir / "config.json"
        self.config = self._load_config()
```

この章の起点は roster です。  
roster がないまま team を語ると、結局「今この場で数回呼び出した model たち」にしか見えません。

### Step 2: teammate を spawn する

```python
def spawn(self, name: str, role: str, prompt: str):
    member = {"name": name, "role": role, "status": "working"}
    self.config["members"].append(member)
    self._save_config()

    thread = threading.Thread(
        target=self._teammate_loop,
        args=(name, role, prompt),
        daemon=True,
    )
    thread.start()
```

ここで大切なのは thread という実装選択そのものではありません。  
大切なのは次のことです。

**一度 spawn された teammate は、一回限りの tool call ではなく、継続する lifecycle を持つ**

### Step 3: 各 teammate に mailbox を持たせる

教学版で一番分かりやすいのは JSONL inbox です。

```text
.team/inbox/alice.jsonl
.team/inbox/bob.jsonl
```

送信側:

```python
def send(self, sender: str, to: str, content: str):
    with open(f"{to}.jsonl", "a") as f:
        f.write(json.dumps({
            "type": "message",
            "from": sender,
            "to": to,
            "content": content,
            "timestamp": time.time(),
        }) + "\n")
```

受信側:

1. すべて読む
2. JSON として parse する
3. 読み終わったら inbox を drain する

ここで教えたいのは storage trick ではありません。

教えたいのは:

**協調は shared `messages[]` ではなく、mailbox boundary を通して起こる**

という構造です。

### Step 4: teammate は毎ラウンド mailbox を先に確認する

```python
def teammate_loop(name: str, role: str, prompt: str):
    messages = [{"role": "user", "content": prompt}]

    while True:
        inbox = bus.read_inbox(name)
        for item in inbox:
            messages.append({"role": "user", "content": json.dumps(item)})

        response = client.messages.create(...)
        ...
```

この step をあいまいにすると、読者はすぐこう誤解します。

- 新しい仕事を与えるたびに teammate を再生成するのか
- 元の context はどこに残るのか

正しくは:

- teammate は残る
- messages も残る
- 新しい仕事は inbox 経由で入る
- 次ラウンドに入る前に mailbox を見る

です。

## Teammate / Subagent / Runtime Slot をどう分けるか

この段階で最も混ざりやすいのはこの 3 つです。  
次の表をそのまま覚えて構いません。

| 仕組み | 何に近いか | lifecycle | 核心境界 |
|---|---|---|---|
| subagent | 一回きりの外部委託 helper | 作って、少し働いて、終わる | 小さな探索文脈の隔離 |
| runtime slot | 実行中の background slot | その実行が終われば消える | 長い execution を追跡する |
| teammate | 長期に残る team member | idle と working を行き来する | 名前、role、mailbox、独立 loop |

口語的に言い換えると:

- subagent: 「ちょっと調べて戻ってきて」
- runtime slot: 「これは裏で走らせて、あとで知らせて」
- teammate: 「あなたは今後しばらくテスト担当ね」

## ここで教えるべき境界

この章でまず固めるべきは 3 つだけです。

- roster
- mailbox
- 独立 loop

これだけで「長く残る teammate」という実体は十分立ち上がります。

ただし、まだここでは教え過ぎない方がよいものがあります。

### 1. protocol request layer

つまり:

- どの message が普通の会話か
- どの message が `request_id` を持つ構造化 request か

これは `s16` の範囲です。

### 2. autonomous claim layer

つまり:

- teammate が自分で仕事を探すか
- どの policy で self-claim するか
- resume は何を根拠に行うか

これは `s17` の範囲です。

`s15` の default はあくまで:

- lead が作る
- lead が送る
- teammate が受ける

です。

## 初学者が特によくやる間違い

### 1. teammate を「名前付き subagent」にする

名前が付いていても、実装が

```text
spawn -> work -> summary -> destroy
```

なら本質的にはまだ subagent です。

### 2. team 全員で 1 本の `messages` を共有する

これは一見簡単ですが、文脈汚染がすぐ起きます。

各 teammate は少なくとも:

- 自分の messages
- 自分の inbox
- 自分の status

を持つべきです。

### 3. roster を durable にしない

system を止めた瞬間に「team に誰がいたか」を完全に失うなら、長期 actor layer としてはかなり弱いです。

### 4. mailbox なしで shared variable だけで会話させる

実装は短くできますが、teammate 間協調の境界が見えなくなります。  
教学 repo では durable mailbox を置いた方が、読者の心智がずっと安定します。

## 学び終わったら言えるべきこと

少なくとも次の 4 つを自分の言葉で説明できれば、この章の主線は掴めています。

1. teammate の本質は「多 model」ではなく「長期に残る actor identity」である
2. team system の最小構成は「roster + mailbox + 独立 loop」である
3. subagent と teammate の違いは lifecycle の長さにある
4. teammate と runtime slot の違いは、「actor identity」か「live execution」かにある

## 次章で何を足すか

この章が解いているのは:

> team member が長く存在し、互いに message を送り合えるようにすること

次章 `s16` が解くのは:

> message が単なる自由文ではなく、追跡・承認・拒否・期限切れを持つ protocol object になるとき、どう設計するか

つまり `s15` が「team の存在」を作り、`s16` が「team の構造化協調」を作ります。
