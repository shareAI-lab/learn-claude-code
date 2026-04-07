# s16: Team Protocols

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > [ s16 ] > s17 > s18 > s19`

> *mailbox があるだけでは「話せる team」に過ぎません。protocol が入って初めて、「規則に従って協調できる team」になります。*

## この章が解く問題

`s15` までで teammate 同士は message を送り合えます。

しかし自由文だけに頼ると、すぐに 2 つの問題が出ます。

- 明確な承認 / 拒否が必要な場面で、曖昧な返事しか残らない
- request が複数同時に走ると、どの返答がどの件に対応するのか分からなくなる

特に分かりやすいのは次の 2 場面です。

1. graceful shutdown を依頼したい
2. 高リスク plan を実行前に approval したい

一見別の話に見えても、骨格は同じです。

```text
requester が request を送る
  ->
receiver が明確に response する
  ->
両者が同じ request_id で対応関係を追える
```

この章で追加するのは message の量ではなく、

**追跡可能な request-response protocol**

です。

## 併読すると楽になる資料

- 普通の message と protocol request が混ざったら [`glossary.md`](./glossary.md) と [`entity-map.md`](./entity-map.md)
- `s17` や `s18` に進む前に境界を固めたいなら [`team-task-lane-model.md`](./team-task-lane-model.md)
- request が主システムへどう戻るか見直したいなら [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md)

## 先に言葉をそろえる

### protocol とは何か

ここでの `protocol` は難しい通信理論ではありません。

意味は、

> message の形、処理手順、状態遷移を事前に決めた協調ルール

です。

### request_id とは何か

`request_id` は request の一意な番号です。

役割は 1 つで、

> 後から届く response や status update を、元の request と正確に結びつけること

です。

### request-response pattern とは何か

これも難しく考える必要はありません。

```text
requester: この操作をしたい
receiver: 承認する / 拒否する
```

この往復を、自然文の雰囲気で済ませず、**構造化 record として残す**のがこの章です。

## 最小心智モデル

教学上は、protocol を 2 層で見ると分かりやすくなります。

```text
1. protocol envelope
2. durable request record
```

### protocol envelope

これは inbox を流れる 1 通の構造化 message です。

```python
{
    "type": "shutdown_request",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "payload": {},
}
```

### durable request record

これは request の lifecycle を disk に追う record です。

```python
{
    "request_id": "req_001",
    "kind": "shutdown",
    "from": "lead",
    "to": "alice",
    "status": "pending",
}
```

この 2 層がそろうと system は、

- いま何を送ったのか
- その request は今どの状態か

を両方説明できるようになります。

## この章の核になるデータ構造

### 1. ProtocolEnvelope

protocol message は普通の message より多くのメタデータを持ちます。

```python
message = {
    "type": "shutdown_request",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "payload": {},
    "timestamp": 1710000000.0,
}
```

特に重要なのは次の 3 つです。

- `type`: これは何の protocol message か
- `request_id`: どの request thread に属するか
- `payload`: 本文以外の構造化内容

### 2. RequestRecord

request record は `.team/requests/` に durable に保存されます。

```python
request = {
    "request_id": "req_001",
    "kind": "shutdown",
    "from": "lead",
    "to": "alice",
    "status": "pending",
    "created_at": 1710000000.0,
    "updated_at": 1710000000.0,
}
```

この record があることで、system は message を送ったあとでも request の状態を追い続けられます。

教材コードでは実際に次のような path を使います。

```text
.team/requests/
  req_001.json
  req_002.json
```

これにより、

- request の状態を再読込できる
- protocol の途中経過をあとから確認できる
- main loop が先へ進んでも request thread が消えない

という利点が生まれます。

### 3. 状態機械

この章の state machine は難しくありません。

```text
pending -> approved
pending -> rejected
pending -> expired
```

ここで大事なのは theory ではなく、

**承認系の協調には「いまどの状態か」を explicit に持つ必要がある**

ということです。

## 最小実装を段階で追う

### 第 1 段階: team mailbox の上に protocol line を通す

この章の本質は新しい message type を 2 個足すことではありません。

本質は、

```text
requester が protocol action を開始する
  ->
request record を保存する
  ->
protocol envelope を inbox に送る
  ->
receiver が request_id 付きで response する
  ->
record の status を更新する
```

という一本の durable flow を通すことです。

### 第 2 段階: shutdown protocol を作る

graceful shutdown は「thread を即 kill する」ことではありません。

正しい流れは次です。

1. shutdown request を作る
2. teammate が approve / reject を返す
3. approve なら後始末して終了する

request 側の最小形はこうです。

```python
def request_shutdown(target: str):
    request_id = new_id()
    REQUEST_STORE.create({
        "request_id": request_id,
        "kind": "shutdown",
        "from": "lead",
        "to": target,
        "status": "pending",
    })
    BUS.send(
        "lead",
        target,
        "Please shut down gracefully.",
        "shutdown_request",
        {"request_id": request_id},
    )
```

response 側は request_id を使って同じ record を更新します。

```python
def handle_shutdown_response(request_id: str, approve: bool):
    record = REQUEST_STORE.update(
        request_id,
        status="approved" if approve else "rejected",
    )
```

### 第 3 段階: plan approval も同じ骨格で扱う

高リスクな変更を teammate が即時実行してしまうと危険なことがあります。

そこで plan approval protocol を入れます。

```python
def submit_plan(name: str, plan_text: str):
    request_id = new_id()
    REQUEST_STORE.create({
        "request_id": request_id,
        "kind": "plan_approval",
        "from": name,
        "to": "lead",
        "status": "pending",
        "plan": plan_text,
    })
```

lead はその `request_id` を見て承認または却下します。

```python
def review_plan(request_id: str, approve: bool, feedback: str = ""):
    REQUEST_STORE.update(
        request_id,
        status="approved" if approve else "rejected",
        feedback=feedback,
    )
```

ここで伝えたい中心は、

**shutdown と plan approval は中身は違っても、request-response correlation の骨格は同じ**

という点です。

## Message / Protocol / Request / Task の境界

この章で最も混ざりやすい 4 つを表で分けます。

| オブジェクト | 何を答えるか | 典型 field |
|---|---|---|
| `MessageEnvelope` | 誰が誰に何を送ったか | `from`, `to`, `content` |
| `ProtocolEnvelope` | それが構造化 request / response か | `type`, `request_id`, `payload` |
| `RequestRecord` | その協調フローはいまどこまで進んだか | `kind`, `status`, `from`, `to` |
| `TaskRecord` | 実際の work goal は何か | `subject`, `status`, `owner`, `blockedBy` |

ここで絶対に混ぜないでほしい点は次です。

- protocol request は task そのものではない
- request store は task board ではない
- protocol は協調フローを追う
- task は仕事の進行を追う

## `s15` から何が増えたか

`s15` の team system は「話せる team」でした。

`s16` ではそこへ、

- request_id
- durable request store
- approved / rejected の explicit status
- protocol-specific message type

が入ります。

すると team は単なる chat 集合ではなく、

**追跡可能な coordination system**

に進みます。

## 初学者が混ぜやすいポイント

### 1. request を普通の text message と同じように扱う

これでは承認状態を追えません。

### 2. request_id を持たせない

同時に複数 request が走った瞬間に対応関係が壊れます。

### 3. request の状態を memory 内 dict にしか置かない

プロセスをまたいで追えず、観測性も悪くなります。

### 4. approved / rejected を曖昧な文章だけで表す

state machine が読めなくなります。

### 5. protocol と task を混同する

plan approval request は「plan を実行してよいか」の協調であって、work item 本体ではありません。

## 前の章とどうつながるか

この章は `s15` の mailbox-based team を次の段階へ押し上げます。

- `s15`: teammate が message を送れる
- `s16`: teammate が structured protocol で協調できる

そしてこの先、

- `s17`: idle teammate が自分で task を claim する
- `s18`: task ごとに isolation lane を持つ

へ進む準備になります。

もしここで protocol の境界が曖昧なままだと、後の autonomy や worktree を読むときに

- 誰が誰に依頼したのか
- どの state が協調の state で、どれが work の state か

がすぐ混ざります。

## 教学上の境界

この章でまず教えるべきのは、製品に存在しうる全 protocol の一覧ではありません。

中心は次の 3 点です。

- request と response を同じ `request_id` で結び付けること
- 承認状態を explicit state として残すこと
- team coordination を自由文から durable workflow へ進めること

ここが見えていれば、後から protocol の種類が増えても骨格は崩れません。
