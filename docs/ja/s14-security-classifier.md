# s14: Security Classifier (セキュリティ分類器)

`s02 > s13 > [ s14 ] | s15 | s16 > s17`

> *"正規表現はパターンを見る; LLMは意図を見る"*
>
> **Harness 層**: セキュリティ分類 -- コマンドの意図を判断する。

## 問題

s13の正規表現はコマンドの「形」しかマッチできない。`rm -rf build/` と `rm -rf /` は正規表現には同じに見える。

## 解決策

2層分類パイプライン:

- **Layer 1** (正規表現): 15の既知の危険パターン、ゼロコスト、即座にマッチ。
- **Layer 2** (LLM): 意図を理解して未知のコマンドを分類。

## 動作原理

1. `SecurityClassifier.quick_scan()` が15の正規パターンをO(1)でチェック。
2. `SecurityClassifier.llm_classify()` がコマンドをLLMに送信して意図分析。
3. `classify()` がフルパイプラインを実行: クイックスキャン -> ホワイトリスト -> LLM。

## s13からの変更点

| コンポーネント | 変更前 (s13) | 変更後 (s14) |
|---------------|-------------|-------------|
| 分類方式 | 正規表現パターンマッチングのみ | 正規クイックスキャン + LLM分類 |
| 未知のコマンド | デフォルト許可 | LLMがsafe/moderate/dangerousを判断 |
| 誤検知 | 高い | 低い (LLMは意図を理解) |
| コスト | ゼロ | ホワイトリスト無料 + LLM ~10 tokens/呼び出し |

## 試してみる

```sh
cd learn-claude-code
python agents/s14_security_classifier.py
```

1. `delete the build/ directory` (LLMがmoderateと判定 -> 確認)
2. `list all python files` (ホワイトリスト -> 許可)
3. `run git push --force origin main` (正規パターン -> 拒否)
4. `run pip install numpy` (LLMがmoderateと判定 -> 確認)
5. `create a new file called test.py` (LLMがsafeと判定 -> 許可)
