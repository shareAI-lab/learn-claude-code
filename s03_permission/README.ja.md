# s03: Permission — 実行前に権限を判断する

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → s02 → `s03` → [s04](../s04_hooks/) → s05 → ... → s16 → s17
> *"ツール実行前に権限を判断"* — 権限パイプラインは、どの操作に承認が必要かを決める。
>
> **Harness レイヤー**: 権限 — ツール実行前に一つのゲートを追加。

---

## 課題

s02 の Agent は 5 つのツールを持つ。file tools は `safe_path` で保護されるが、bash は制限なし。「プロジェクトを掃除して」と頼むと、`rm -rf /` を実行しかねない。

安全性はモデルを信頼することではなく、コードに頼る — ツール実行前に判断を挟む。

---

## ソリューション

![Permission Overview](images/permission-overview.ja.svg)

s02 のループは完全に維持される。唯一の変更は、ツール実行前に `check_permission()` を挿入すること — 各ツール呼び出しは 3 つのゲートを固定順序で通過する：ハード拒否が最優先、次にソフト確認、どちらも一致しなければ許可。

3 つのゲートは 3 つの決定に対応する：

| ゲート | 役割 | 一致時 |
|--------|------|--------|
| 1. 拒否リスト | 常に禁止される操作（`rm -rf /`、`sudo`） | 即座に拒否、実行しない |
| 2. ルールマッチング | コンテキスト依存の操作（作業ディレクトリ外への読み書き、`rm` ファイル） | ゲート 3 へ |
| 3. ユーザー承認 | ゲート 2 が一致した場合、ユーザー確認を待機 | ユーザーが許可または拒否を決定 |

3 つのゲートのどれにも一致しない → 直接実行。日常の操作の大部分はこの経路を通る。

---

## 仕組み

![Permission Pipeline](images/permission-pipeline.ja.svg)

**ゲート 1**：ハード拒否リスト。最初に確認し、一致すればブロックメッセージを返す。このリストは権限ゲートの位置を示すための単純な文字列照合であり、完全なセキュリティ境界ではない。

```python
DENY_LIST = [
    "rm -rf /", "sudo", "shutdown", "reboot",
    "mkfs", "dd if=", "> /dev/sda",
]

def check_deny_list(command: str) -> str | None:
    for pattern in DENY_LIST:
        if pattern in command:
            return f"Blocked: '{pattern}' is on the deny list"
    return None
```

**ゲート 2**：ルールマッチング — 「いつユーザーに聞くべきか」を記述する。各ルールはツールとチェック条件を指定する。

```python
import re

DESTRUCTIVE_COMMAND_WORD = re.compile(
    r"(?i)(?:^|[;&|()\n])\s*(?:rm|del)(?=\s|$|[;&|()])"
)

def contains_destructive_command(command: str) -> bool:
    return bool(DESTRUCTIVE_COMMAND_WORD.search(command))

PERMISSION_RULES = [
    {
        "tools": ["read_file", "write_file", "edit_file"],
        "check": lambda args: not (WORKDIR / args.get("path", "")).resolve().is_relative_to(WORKDIR),
        "message": "Access outside workspace",
    },
    {
        "tools": ["bash"],
        "check": lambda args: contains_destructive_command(args.get("command", "")) or any(
            kw in args.get("command", "") for kw in ["rm ", "> /etc/", "chmod 777"]
        ),
        "message": "Potentially destructive command",
    },
]

def check_rules(tool_name: str, args: dict) -> str | None:
    for rule in PERMISSION_RULES:
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None
```

**ゲート 3**：ルールが一致した後、ユーザー入力を待機。

```python
def ask_user(tool_name: str, args: dict, reason: str) -> str:
    print(f"\n⚠  {reason}")
    print(f"   Tool: {tool_name}({args})")
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"
```

**3 つのゲートを直列に接続**、ツール実行前に挿入する：

```python
def check_permission(block) -> bool:
    # ゲート 1: ハード拒否
    if block.name == "bash":
        reason = check_deny_list(block.input.get("command", ""))
        if reason:
            print(f"\n⛔ {reason}")
            return False

    # ゲート 2 + 3: ルールマッチング → ユーザー承認
    reason = check_rules(block.name, block.input)
    if reason:
        decision = ask_user(block.name, block.input, reason)
        if decision == "deny":
            return False

    return True

# agent_loop で — s02 のループに 1 行追加するだけ：
for block in tool_calls:
    if not check_permission(block):           # ← 新規
        results.append({... "content": "Permission denied."})
        continue
    output = TOOL_HANDLERS[block.name](**block.input)  # s02 既存
    results.append(...)
```

---

## s02 からの変更点

| コンポーネント | 変更前 (s02) | 変更後 (s03) |
|---------------|-------------|-------------|
| セキュリティモデル | なし（モデルを信頼） | 3 ゲート権限パイプライン |
| 新規関数 | — | check_deny_list, check_rules, ask_user, check_permission |
| ループ | すべてのツールを直接実行 | 実行前に check_permission() を挿入 |

---

## 試してみよう

```sh
cd learn-claude-code
python s03_permission/code.py
```

以下のプロンプトを試してみよう：

1. `Create a file called test.txt in the current directory`（そのまま通過するはず）
2. `Delete the file test.txt`（bash + rm でゲート 2 が発動）
3. `What files are in the current directory?`（読み取り専用、すべて通過）
4. `Try to write a file to /etc/something`（作業ディレクトリ外への書き込みでゲート 2 が発動）
5. Windows では `del test.txt` と `DEL test.txt` がゲート 2 を発動し、`model`、`delimiter`、`echo del test.txt` は発動しない。

観察のポイント：どの操作がそのまま通過するか？ どれに確認が必要か？ どれが即座に拒否されるか？

---

## 次へ

権限チェックは実装された — しかし、毎回ループ内に `check_permission()` をハードコードしている。ツール実行の前後にログを追加したい場合は？ 特定の操作後に自動的に git commit をトリガーしたい場合は？ このような拡張ロジックがループ内に散らばると、ループはすぐに膨張する。

→ s04 Hooks：ループにフックを追加する。拡張ロジックはフックにぶら下げ、ループはクリーンに保つ。


<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
