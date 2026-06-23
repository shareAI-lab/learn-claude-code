# s21: システムプロンプト分析

[中文](../../s21_system_prompts_analysis/README.md) · [English](../../s21_system_prompts_analysis/README.en.md)

s21 は Piebald-AI/claude-code-system-prompts リポジトリを直接分析し、code.py で 515+ 件の実際のプロンプトを動的に取得・分類・集計します。

## 主要ポイント

- データソース: Piebald-AI リポジトリ（Claude Code v2.1.181、515+ プロンプト）
- 分析方法: code.py が README.md を動的取得、正規表現で解析、カテゴリ別集計
- 設計パターン: 多段階分解、条件付きアセンブリ、安全制約、メモリ管理、スキーマ駆動

## 実行

```sh
python s21_system_prompts_analysis/code.py
```

詳細は [s21_system_prompts_analysis/README.md](../../s21_system_prompts_analysis/README.md) を参照
