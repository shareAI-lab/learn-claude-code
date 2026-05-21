# s16: Team Protocols — チームメイト間には取り決めが必要

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → ... → s14 → s15 → `s16` → [s17](../s17_autonomous_agents/) → s18 → s19 → s20
> *"チームメイト間には取り決めが必要"* — request-response パターンが全てのネゴシエーションを駆動。
>
> **Harness 層**: プロトコル — Agent 間の構造化ハンドシェイク。

---

## 課題

s15 のチームメイトは仕事ができるが、連携は緩い：Lead がメッセージを送り、チームメイトが返信するだけで、構造化されたプロトコルがない。2 つのシナリオで問題が露呈する：

**シャットダウン**：Lead が Alice にシャットダウンを頼む。スレッドを強制終了すると、書きかけのファイルがディスクに残る。ハンドシェイクが必要：Lead がリクエストを送信、Alice が收尾後に確認。

**計画承認**：Bob が認証モジュールのリファクタリングを提案、高リスク操作。Lead が Bob の計画を確認し、承認後に実行すべき。

これら 2 つのシナリオは同じ構造：一方がリクエストを送信、もう一方が返信、両者は同じ ID で関連付けられる。状態機械が追跡：pending → approved / rejected。

---

## ソリューション

![Team Protocols Overview](images/team-protocols-overview.ja.svg)

教学版は前章までの Agent 能力の流れを受け継ぎ、S15 のチーム通信の上に構造化プロトコルを追加する。プロトコル機構に集中するため、完全なエラーリカバリ、メモリ、スキルシステムは省略。追加：**ProtocolState**（リクエスト状態追跡）、**dispatch_message**（メッセージタイプ別ルーティング）、**match_response**（request_id でリクエストとレスポンスを関連付け、型検証付き）。

2 つのプロトコル、1 つの仕組み：

| プロトコル | 方向 | 用途 |
|-----------|------|------|
| shutdown_request / response | Lead → チームメイト | 丁寧なシャットダウンハンドシェイク |
| plan_approval_request / response | チームメイト → Lead | 計画承認プロトコルの例 |

> 教学版は計画承認の request-response メッセージフローをデモするが、実行ゲーティング（未承認時の bash/write_file 拦截）は未実装。真实 CC にはチームメイト向けの permission gating 機構がある。

---

## 仕組み

### ProtocolState: リクエスト状態

各プロトコルリクエストは、送信者、受信者、現在の状態、ペイロードを記録する状態レコードを作成：

```python
@dataclass
class ProtocolState:
    request_id: str      # 一意 ID、例 "req_004281"
    type: str            # "shutdown" | "plan_approval"
    sender: str          # 送信者
    target: str          # 受信者
    status: str          # pending | approved | rejected
    payload: str         # 計画テキストまたはシャットダウン理由
    created_at: float    # タイムスタンプ

pending_requests: dict[str, ProtocolState] = {}
```

リクエスト送信時にレコードを作成、レスポンス受信時に `request_id` で該当レコードを見つけて状態を更新。

### 4 ステッププロトコルフロー

シャットダウンを例にした完全な流れ：

```
1. Lead がリクエスト送信
   req_id = new_request_id()           # "req_004281"
   pending_requests[req_id] = ProtocolState(type="shutdown", status="pending", ...)
   BUS.send("lead", "alice", "shutdown_request", metadata={"request_id": req_id})

2. チームメイト受信 → dispatch
   inbox = BUS.read_inbox("alice")
   msg_type = msg["type"]              # "shutdown_request"
   → handle_shutdown_request() にルーティング

3. チームメイト返信
   BUS.send("alice", "lead", "shutdown_response",
            metadata={"request_id": req_id, "approve": True})

4. Lead がレスポンス受信 → match
   match_response("shutdown_response", req_id, approve=True)
   pending_requests[req_id].status = "approved"
```

`request_id` はチェーン全体を貫く関連キー、リクエストが持ち出し、レスポンスが持ち帰る。

### dispatch_message: タイプ別ルーティング

チームメイトの inbox は通常メッセージとプロトコルメッセージの両方を受信。`handle_inbox_message` がメッセージタイプで振り分け：

```python
def handle_inbox_message(name, msg, messages):
    msg_type = msg.get("type", "message")
    req_id = msg.get("metadata", {}).get("request_id", "")

    if msg_type == "shutdown_request":
        BUS.send(name, "lead", "Shutting down.", "shutdown_response",
                 {"request_id": req_id, "approve": True})
        return True   # ループ停止

    if msg_type == "plan_approval_response":
        approve = msg["metadata"].get("approve", False)
        messages.append({"role": "user",
            "content": "[Plan approved]" if approve else "[Plan rejected]"})
    return False       # 継続
```

新しいプロトコルタイプの追加は新しい `if` 分岐を追加するだけ。

### match_response: 型検証

`match_response` は `request_id` で状態を見つけるだけでなく、レスポンスタイプがリクエストタイプと一致するか検証：

```python
def match_response(response_type, request_id, approve):
    state = pending_requests.get(request_id)
    if not state:
        return
    if state.type == "shutdown" and response_type != "shutdown_response":
        return  # タイプ不一致、スキップ
    if state.type == "plan_approval" and response_type != "plan_approval_response":
        return
    if state.status != "pending":
        return  # 既に解決済み、重複をスキップ
    state.status = "approved" if approve else "rejected"
```

shutdown_response が誤って plan_approval リクエストを承認することはない。

### 統一 inbox コンシューマ：consume_lead_inbox

`check_inbox` ツールとメインループ末尾の両方が同じ `consume_lead_inbox()` 関数を呼び出す。プロトコルメッセージを先にルーティングしてから残りの内容を返す。メッセージが消費されてもプロトコル状態が更新されない問題を防ぐ：

```python
def consume_lead_inbox(route_protocol=True) -> list[dict]:
    msgs = BUS.read_inbox("lead")
    if route_protocol:
        for msg in msgs:
            meta = msg.get("metadata", {})
            req_id = meta.get("request_id", "")
            msg_type = msg.get("type", "")
            if req_id and msg_type.endswith("_response"):
                match_response(msg_type, req_id, meta.get("approve", False))
    return msgs
```

メインループは inbox メッセージを `history` に注入し、LLM が確認して反応できるようにする。

### チームメイト idle loop：終了ではなく待機

s15 のチームメイトは 10 ラウンドで終了。s16 のチームメイトは LLM が非 tool_use を返した後 idle 待機に入る：inbox をポーリング、shutdown_request に応答して終了、または新メッセージで作業継続。

```
LLM が非 tool_use を返す
  → idle: 毎秒 inbox をポーリング
  → shutdown_request 受信 → shutdown_response 返信 → 終了
  → 新メッセージ受信 → messages に注入 → LLM ターン継続
```

教学版は Lead への idle_notification を省略。真实 CC は idle 時に `idle_notification` を送信、Lead はチームメイトが空いていることを知り、新しいタスクを割り当て可能。

### 組み合わせて実行

```
1. Lead: "Alice にファイルを作成させ、その後シャットダウン"
2. Lead → spawn_teammate("alice", "backend", "config.py を作成")
3. alice スレッド起動 → write_file("config.py", "...") → 完了 → idle
4. Lead → request_shutdown("alice")
   → BUS.send("shutdown_request", {request_id: "req_000142"})
5. alice idle ポーリング受信 → handle_shutdown_request
   → BUS.send("shutdown_response", {request_id: "req_000142", approve: True})
6. Lead consume_lead_inbox → match_response("req_000142", approve=True)
   → pending_requests["req_000142"].status = "approved"
   → inbox メッセージが history に注入、LLM がシャットダウン結果を確認
```

シャットダウンハンドシェイク完了：リクエスト → 確認 → シャットダウン。各ステップは `request_id` で追跡。

---

## s15 からの変更

| コンポーネント | 変更前 (s15) | 変更後 (s16) |
|--------------|------------|------------|
| 連携方法 | 緩いテキストメッセージ | 構造化 request-response プロトコル |
| リクエスト追跡 | なし | ProtocolState + pending_requests dict |
| メッセージルーティング | 全てテキストとして処理 | dispatch_message がタイプ別にルーティング |
| シャットダウン | 自然終了またはスレッド強制終了 | request_id ハンドシェイク機構 |
| 計画承認 | なし | メッセージフローの例（実行ゲーティングなし） |
| 新規メッセージ型 | message, result | + shutdown_request/response, plan_approval_request/response |
| チームメイトライフサイクル | 最大 10 ラウンド | idle loop（inbox メッセージを待機） |
| Lead inbox | check_inbox とメインループが別々に読み取り | 統一 consume_lead_inbox |
| Lead ツール | 14 (s15) | 14（コアツールセットに request_shutdown、request_plan、review_plan を追加） |
| チームメイトツール | 4 (s15) | + submit_plan (5) |

---

## 試してみる

```sh
cd learn-claude-code
python s16_team_protocols/code.py
```

以下のプロンプトを試してください：

1. `Spawn alice as a backend dev. Ask her to create a file. Then request her shutdown.`
2. `Spawn bob with a refactoring task. Have him submit a plan first. Then review and approve it.`

観察ポイント：シャットダウンハンドシェイクは完了しているか（リクエスト → 確認 → シャットダウン）？`pending_requests` の状態は正しく遷移しているか？`request_id` はリクエストとレスポンス間で一貫しているか？idle チームメイトは shutdown_request を受信できるか？

---

## 次の章

s15-s16 では、Lead が各チームメイトにタスクを割り当てる必要がある。"Alice はこれ、Bob はあれ"。ボードに 10 個の未認領タスクがあれば、Lead が手動で assign しなければならない。

チームメイトが自分でボードを見て認領できたらどうか？Lead はタスクを作成するだけで、チームメイトが自分で発見、認領、完了する。

s17 Autonomous Agents → チームメイトの自己組織化、リーダーの割り当て不要。

<details>
<summary>CC ソースコード深掘り</summary>

CC のチームプロトコル実装（`teammateMailbox.ts`、1184 行）は教学版と同じコア構造：request_id + approve/reject の request-response パターン。違いは以下の通り：

**シャットダウンプロトコル**：CC のシャットダウンは三方向通信（`teammateMailbox.ts:720-763`、`SendMessageTool.ts:268-430`）。Lead が `shutdown_request` を送信、チームメイトが `shutdown_approved`（または理由付き `shutdown_rejected`）で返信、システムが `teammate_terminated` で全関係者に通知。確認後、システムが自動的に pane（tmux/iTerm2）をクリーンアップ、タスクを unassign、team config からメンバーを削除（`useInboxPoller.ts:677-800`）。教学版は `shutdown_response` で統一命名、真实源码は `shutdown_approved` と `shutdown_rejected` の 2 つの独立したメッセージ型に分割。

**計画承認**：真实源码では plan approval request は `ExitPlanModeV2Tool.ts:263-312` で plan-mode-required チームメイトが plan mode を終了する際に生成される。`useInboxPoller.ts:599-661` は現在自動的に approval を書き戻し、リクエストを Lead にコンテキスト（regular message）として渡す。`SendMessageTool.ts:434-518` は明示的な approve/reject response 能力を保持、承認時に同時に `permissionMode` を設定可能（例："承認するが plan mode で実行"）、レスポンスにはチームメイトが修正して再提出するための `feedback` 文字列を含めることができる。単純な「Lead が手動で review_plan ツールを使う」フローではない。

**メッセージ形式**：CC のプロトコルメッセージは構造化 JSON（Zod schema 検証付き）、教学版はシンプルな type + metadata dict。フィールド名も統一されていない：permission は `request_id`（`teammateMailbox.ts:453-462`）、shutdown と plan approval は `requestId`（`teammateMailbox.ts:684-763`）。

**実行ゲーティング**：CC のチームメイトには完全な permission gating がある。未承認の高リスク操作は拦截され、オプションではない。教学版はメッセージフローのみをデモ。

**汎用性**：教学版の 1 つの FSM（pending → approved | rejected）が 2 つのプロトコルに対応する簡略化は正しい。CC の全プロトコルメッセージは同じ request id 関連機構を共有。

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
