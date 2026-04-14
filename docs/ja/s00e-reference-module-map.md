# s00e: 参照リポジトリのモジュール対応表

> これは保守者と本気で学ぶ読者向けの校正文書です。  
> 逆向きソースを逐行で読ませるための資料ではありません。
>
> ここで答えたいのは、次の一点です。
>
> **参照リポジトリの高信号なモジュール群と現在の教材の章順を突き合わせると、今のカリキュラム順は本当に妥当なのか。**

## 結論

妥当です。

現在の `s01 -> s19` の順序は大筋で正しく、単純に「ソースツリーの並び順」に合わせるより、実際の設計主幹に近いです。

理由は単純です。

- 参照リポジトリには表層のディレクトリがたくさんある
- しかし本当に設計の重みを持つのは、制御・状態・タスク・チーム・worktree・外部 capability に関する一部のクラスタ
- それらは現在の 4 段階の教材構成ときれいに対応している

したがって、すべきことは「教材をソース木順へ潰す」ことではありません。

すべきことは:

- 今の依存関係ベースの順序を維持する
- 参照リポジトリとの対応を明文化する
- 主線に不要な製品周辺の細部を入れ過ぎない

## この比較で見た高信号クラスタ

主に次のようなモジュール群を見ています。

- `Tool.ts`
- `state/AppStateStore.ts`
- `coordinator/coordinatorMode.ts`
- `memdir/*`
- `services/SessionMemory/*`
- `services/toolUseSummary/*`
- `constants/prompts.ts`
- `tasks/*`
- `tools/TodoWriteTool/*`
- `tools/AgentTool/*`
- `tools/ScheduleCronTool/*`
- `tools/EnterWorktreeTool/*`
- `tools/ExitWorktreeTool/*`
- `tools/MCPTool/*`
- `services/mcp/*`
- `plugins/*`
- `hooks/toolPermission/*`

これだけで、設計主脈絡の整合性は十分に判断できます。

## 対応関係

| 参照リポジトリのクラスタ | 典型例 | 対応する教材章 | この配置が妥当な理由 |
|---|---|---|---|
| Query ループと制御状態 | `Tool.ts`、`AppStateStore.ts`、query / coordinator 状態 | `s00`、`s00a`、`s00b`、`s01`、`s11` | 実システムは `messages[] + while True` だけではない。教材が最小ループから始め、後で control plane を補う流れは正しい。 |
| Tool routing と実行面 | `Tool.ts`、native tools、tool context、実行 helper | `s02`、`s02a`、`s02b` | 参照実装は tools を共有 execution plane として扱っている。教材の分け方は妥当。 |
| セッション計画 | `TodoWriteTool` | `s03` | セッション内の進行整理は小さいが重要な層で、持続タスクより先に学ぶべき。 |
| 一回きりの委譲 | `AgentTool` の最小部分 | `s04` | 参照実装の agent machinery は大きいが、教材がまず「新しい文脈 + サブタスク + 要約返却」を教えるのは正しい。 |
| Skill の発見と読み込み | `DiscoverSkillsTool`、`skills/*`、関連 prompt | `s05` | skills は飾りではなく知識注入層なので、prompt の複雑化より前に置くのが自然。 |
| Context 圧縮と collapse | `services/toolUseSummary/*`、`services/contextCollapse/*` | `s06` | 参照実装に明示的な compact 層がある以上、これを早めに学ぶ構成は正しい。 |
| Permission gate | `types/permissions.ts`、`hooks/toolPermission/*` | `s07` | 実行可否は独立した gate であり、単なる hook ではない。 |
| Hooks と周辺拡張 | `types/hooks.ts`、hook runner | `s08` | 参照実装でも gate と extend は分かれている。順序は現状のままでよい。 |
| Durable memory | `memdir/*`、`services/SessionMemory/*` | `s09` | memory は「何でも残すノート」ではなく、選択的な跨セッション層として扱われている。 |
| Prompt 組み立て | `constants/prompts.ts`、prompt sections | `s10`、`s10a` | 入力は複数 source の合成物であり、教材が pipeline として説明するのは正しい。 |
| Recovery / continuation | query transition、retry、compact retry、token recovery | `s11`、`s00c` | 続行理由は実システムで明示的に存在するため、前段の層を理解した後に学ぶのが自然。 |
| Durable work graph | task record、dependency unlock | `s12` | 会話内の plan と durable work graph を分けている点が妥当。 |
| Live runtime task | `tasks/types.ts`、`LocalShellTask`、`LocalAgentTask`、`RemoteAgentTask` | `s13`、`s13a` | 参照実装の runtime task union は、`TaskRecord` と `RuntimeTaskState` を分けるべき強い根拠になる。 |
| Scheduled trigger | `ScheduleCronTool/*`、`useScheduledTasks` | `s14` | scheduling は runtime work の上に乗る開始条件なので、この順序でよい。 |
| Persistent teammate | `InProcessTeammateTask`、team tools、agent registry | `s15` | 一回限りの subagent から durable actor へ広がる流れが参照実装にある。 |
| Structured protocol | send-message、request tracking、coordinator mode | `s16` | protocol は actor が先に存在して初めて意味を持つ。 |
| Autonomous claim / resume | task claiming、async worker lifecycle、resume logic | `s17` | autonomy は actor と task と protocol の上に成り立つ。 |
| Worktree lane | `EnterWorktreeTool`、`ExitWorktreeTool`、worktree helper | `s18` | worktree は単なる git 小技ではなく、実行レーンと closeout 状態の仕組み。 |
| External capability bus | `MCPTool`、`services/mcp/*`、`plugins/*` | `s19`、`s19a` | 参照実装でも MCP / plugin は外側の platform boundary にある。最後に置くのが正しい。 |

## 特に強く裏付けられた 5 点

### 1. `s03` は `s12` より前でよい

参照実装には:

- セッション内の小さな計画
- 持続する task / runtime machinery

の両方があります。

これは同じものではありません。

### 2. `s09` は `s10` より前でよい

prompt assembly は memory を含む複数 source を組み立てます。

したがって:

- 先に memory という source を理解する
- その後で prompt pipeline を理解する

の順が自然です。

### 3. `s12` は `s13` より前でなければならない

`tasks/types.ts` に見える runtime task union は非常に重要です。

これは:

- durable な仕事目標
- 今まさに動いている実行スロット

が別物であることをはっきり示しています。

### 4. `s15 -> s16 -> s17` の順は妥当

参照実装でも:

- actor
- protocol
- autonomy

の順で積み上がっています。

### 5. `s18` は `s19` より前でよい

worktree はまずローカルな実行境界として理解されるべきです。

そのあとで:

- plugin
- MCP server
- 外部 capability provider

へ広げる方が、心智がねじれません。

## 教材主線に入れ過ぎない方がよいもの

参照リポジトリに実在していても、主線へ入れ過ぎるべきではないものがあります。

- CLI command 面の広がり
- UI rendering の細部
- telemetry / analytics 分岐
- remote / enterprise の配線
- compatibility layer
- ファイル名や行番号レベルの trivia

これらは本番では意味があります。

ただし 0 から 1 の教材主線の中心ではありません。

## 教材側が特に注意すべき点

### 1. Subagent と Teammate を混ぜない

参照実装の `AgentTool` は:

- 一回きりの委譲
- background worker
- persistent teammate
- worktree-isolated worker

をまたいでいます。

だからこそ教材では:

- `s04`
- `s15`
- `s17`
- `s18`

に分けて段階的に教える方がよいです。

### 2. Worktree を「git の小技」へ縮めない

参照実装には keep / remove、resume、cleanup、dirty check があります。

`s18` は今後も:

- lane identity
- task binding
- closeout
- cleanup

を教える章として保つべきです。

### 3. MCP を「外部 tool 一覧」へ縮めない

参照実装には tools 以外にも:

- resources
- prompts
- elicitation / connection state
- plugin mediation

があります。

したがって `s19` は tools-first で入ってよいですが、capability bus という外側の境界も説明すべきです。

## 最終判断

参照リポジトリの高信号クラスタと照らす限り、現在の章順は妥当です。

今後の大きな加点ポイントは、さらに大規模な並べ替えではなく:

- bridge docs の充実
- エンティティ境界の明確化
- 多言語の整合
- web 側での学習導線の明快さ

にあります。

## 一文で覚える

**よい教材順は、ファイルが並んでいる順ではなく、学習者が依存関係に沿って実装を再構成できる順です。**
