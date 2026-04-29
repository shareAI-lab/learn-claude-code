# s17: Secure Extension Harness (セキュア拡張ハーネス)

`s02 > s13 > s14 | s15 | s16 > [ s17 ]`

> *"プロダクションハーネスの核心は機能の多さではなく、各層の責任の明確さにある"*
>
> **Harness 層**: セキュリティパイプライン -- すべての防御層を1つの実行パスに構成。

## 問題

s13-s16はそれぞれスタンドアロンのエージェントとして動作する。本番システムではすべての層が単一の実行パイプライン内で連携する必要がある。

## 解決策

各層は1つの質問にのみ答える:

| 層 | 質問 | 出典 |
|----|------|------|
| Hook | "このアクションを傍受すべきか？" | s15 |
| 分類器 | "このコマンドの意図は何か？" | s14 |
| 権限 | "この意図は許可されるか？" | s13 |
| 実行 | "実行して結果を返す" | s02 + s16 |

## 動作原理

1. `execute_tool()` がすべてのツール呼び出しに対して5層パイプラインを実行。
2. 各層は独立 -- どれか1つを削除しても他は動作する。
3. REPLコマンド: `/security`, `/hooks`, `/mcp`, `/audit`。

## s16からの変更点

| コンポーネント | 変更前 (s13-s16単体) | 変更後 (s17) |
|---------------|---------------------|-------------|
| セキュリティパイプライン | 各章が単独で実行 | 統合`execute_tool`パイプライン |
| 分類器 | 単独実行 | Hook -> Classify -> Permissionフローに組み込み |
| Hooks | 単独実行 | パイプラインの最初と最後の層 |
| MCP | 単独実行 | パイプライン実行層の一部 |

## 試してみる

```sh
cd learn-claude-code
python agents/s17_secure_extension_harness.py
```

1. `list all python files` (全層通過 -> 許可)
2. `run rm -rf /` (分類器が拒否 -> ブロック)
3. `write a test file and show audit log` (PostToolUseフックが記録 -> `/audit`)
4. `search for 'PermissionGuard' via MCP` (MCPツールがパイプライン経由で呼ばれる)
5. `register a hook that blocks all pip commands` (動的フック登録)
