# エンティティ地図

> この文書は「単語が似て見えるが、同じものではない」という混乱をほどくための地図です。

## 何を分けるための文書か

- [`glossary.md`](./glossary.md) は「この言葉は何か」を説明します
- [`data-structures.md`](./data-structures.md) は「コードではどんな形か」を説明します
- この文書は「どの層に属するか」を分けます

## まず層を見る

```text
conversation layer
  - message
  - prompt block
  - reminder

action layer
  - tool call
  - tool result
  - hook event

work layer
  - work-graph task
  - runtime task
  - protocol request

execution layer
  - subagent
  - teammate
  - worktree lane

platform layer
  - MCP server
  - memory record
  - capability router
```

## 混同しやすい組

### `Message` vs `PromptBlock`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| `Message` | 会話履歴の内容 | 安定した system rule ではない |
| `PromptBlock` | system instruction の断片 | 直近の会話イベントではない |

### `Todo / Plan` vs `Task`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| `todo / plan` | セッション内の進行ガイド | durable work graph ではない |
| `task` | durable な work node | その場の思いつきではない |

### `Work-Graph Task` vs `RuntimeTaskState`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| work-graph task | 仕事目標と依存関係の node | 今動いている executor ではない |
| runtime task | live execution slot | durable dependency node ではない |

### `Subagent` vs `Teammate`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| subagent | 一回きりの委譲 worker | 長期に存在する team member ではない |
| teammate | identity を持つ persistent collaborator | 使い捨て summary worker ではない |

### `ProtocolRequest` vs normal message

| エンティティ | 何か | 何ではないか |
|---|---|---|
| normal message | 自由文のやり取り | 追跡可能な approval workflow ではない |
| protocol request | `request_id` を持つ構造化要求 | 雑談テキストではない |

### `Task` vs `Worktree`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| task | 何をするか | ディレクトリではない |
| worktree | どこで分離実行するか | 仕事目標そのものではない |

### `Memory` vs `CLAUDE.md`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| memory | 後の session でも価値がある事実 | project rule file ではない |
| `CLAUDE.md` | 安定した local rule / instruction surface | user 固有の long-term fact store ではない |

### `MCPServer` vs `MCPTool`

| エンティティ | 何か | 何ではないか |
|---|---|---|
| MCP server | 外部 capability provider | 1 個の tool 定義ではない |
| MCP tool | server が公開する 1 つの capability | 接続面全体ではない |

## 速見表

| エンティティ | 主な役割 | 典型的な置き場 |
|---|---|---|
| `Message` | 会話履歴 | `messages[]` |
| `PromptParts` | 入力 assembly の断片 | prompt builder |
| `PermissionRule` | 実行可否の判断 | settings / session state |
| `HookEvent` | lifecycle extension point | hook layer |
| `MemoryEntry` | durable fact | memory store |
| `TaskRecord` | durable work goal | task board |
| `RuntimeTaskState` | live execution slot | runtime manager |
| `TeamMember` | persistent actor | team config |
| `MessageEnvelope` | teammate 間の構造化 message | inbox |
| `RequestRecord` | protocol workflow state | request tracker |
| `WorktreeRecord` | isolated execution lane | worktree index |
| `MCPServerConfig` | 外部 capability provider 設定 | plugin / settings |

## 一文で覚える

**システムが複雑になるほど、単語を増やすことよりも、境界を混ぜないことの方が重要です。**
