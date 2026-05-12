[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md)

# Learn Claude Code

高完成度の coding-agent harness を、0 から自分で実装できるようになるための教材リポジトリです。

このリポジトリの目的は、実運用コードの細部を逐一なぞることではありません。  
本当に重要な設計主線を、学びやすい順序で理解し、あとで自分の手で作り直せるようになることです。

## このリポジトリが本当に教えるもの

まず一文で言うと:

**モデルが考え、harness がモデルに作業環境を与える。**

その作業環境を作る主な部品は次の通りです。

- `Agent Loop`: モデルに聞く -> ツールを実行する -> 結果を返す
- `Tools`: エージェントの手足
- `Planning`: 大きな作業を途中で迷わせないための小さな構造
- `Context Management`: アクティブな文脈を小さく保つ
- `Permissions`: モデルの意図をそのまま危険な実行にしない
- `Hooks`: ループを書き換えずに周辺機能を足す
- `Memory`: セッションをまたいで残すべき事実だけを保持する
- `Prompt Construction`: 安定ルールと実行時状態から入力を組み立てる
- `Tasks / Teams / Worktree / MCP`: 単体 agent をより大きな作業基盤へ育てる

この教材が目指すのは:

- 主線を順序よく理解できること
- 初学者が概念で迷子にならないこと
- 核心メカニズムと重要データ構造を自力で再実装できること

## あえて主線から外しているもの

実際の製品コードには、agent の本質とは直接関係しない細部も多くあります。

たとえば:

- パッケージングや配布の流れ
- クロスプラットフォーム互換層
- 企業ポリシーやテレメトリ配線
- 歴史互換のための分岐
- 製品統合のための細かな glue code

こうした要素は本番では重要でも、0 から 1 を教える主線には置きません。  
教学リポジトリの中心は、あくまで「agent がどう動くか」です。

## 想定読者

このリポジトリは次の読者を想定しています。

- 基本的な Python が読める
- 関数、クラス、リスト、辞書は分かる
- でも agent システムは初学者でもよい

そのため、書き方の原則をはっきり決めています。

- 新しい概念は、使う前に説明する
- 1つの概念は、できるだけ1か所でまとまって理解できるようにする
- まず「何か」、次に「なぜ必要か」、最後に「どう実装するか」を話す
- 初学者に断片文書を拾わせて自力でつなげさせない

## 学習の約束

この教材を一通り終えたとき、目標は次の 2 つです。

1. 0 から自分で、構造が明快で反復改善できる coding-agent harness を組み立てられること
2. より複雑な実装を読むときに、何が設計主線で何が製品周辺の detail なのかを見分けられること

このリポジトリが重視するのは:

- 重要メカニズムと主要データ構造の高い再現度
- 自分の手で作り直せる実装可能性
- 途中で心智がねじれにくい読み順と説明密度

## 推奨される読み順

日本語版でも主線・bridge doc・web の主要導線は揃えています。  
章順と補助資料は、日本語でもそのまま追えるように保っています。

- 全体マップ: [`docs/ja/s00-architecture-overview.md`](./docs/ja/s00-architecture-overview.md)
- コード読解順: [`docs/ja/s00f-code-reading-order.md`](./docs/ja/s00f-code-reading-order.md)
- 用語集: [`docs/ja/glossary.md`](./docs/ja/glossary.md)
- 教材範囲: [`docs/ja/teaching-scope.md`](./docs/ja/teaching-scope.md)
- データ構造表: [`docs/ja/data-structures.md`](./docs/ja/data-structures.md)

## 初めてこのリポジトリを開くなら

最初から章をばらばらに開かない方が安定します。

最も安全な入口は次の順序です。

1. [`docs/ja/s00-architecture-overview.md`](./docs/ja/s00-architecture-overview.md) で全体図をつかむ
2. [`docs/ja/s00d-chapter-order-rationale.md`](./docs/ja/s00d-chapter-order-rationale.md) で、なぜこの順序で学ぶのかを確認する
3. [`docs/ja/s00f-code-reading-order.md`](./docs/ja/s00f-code-reading-order.md) で、ローカルの `agents/*.py` をどの順で開くか確認する
4. `s01-s06 -> s07-s11 -> s12-s14 -> s15-s19` の 4 段階で主線を順に進める
5. 各段階の終わりで一度止まり、最小版を自分で書き直してから次へ進む

中盤以降で境界が混ざり始めたら、次の順で立て直すのが安定です。

1. [`docs/ja/data-structures.md`](./docs/ja/data-structures.md)
2. [`docs/ja/entity-map.md`](./docs/ja/entity-map.md)
3. いま詰まっている章に近い bridge doc
4. その後で章本文へ戻る

## Web 学習入口

章順、段階境界、章どうしの差分を可視化から入りたい場合は、組み込みの web 教材画面を使えます。

```sh
cd web
npm install
npm run dev
```

開いたあと、まず見ると良いルートは次です。

- `/ja`: 日本語の学習入口。最初にどの読み方を選ぶか決める
- `/ja/timeline`: 主線を順にたどる最も安定した入口
- `/ja/layers`: 4 段階の境界を先に理解する入口
- `/ja/compare`: 2 章の差やジャンプ診断を見る入口

初回読みに最も向くのは `timeline` です。  
途中で境界が混ざったら、先に `layers` と `compare` を見てから本文へ戻る方が安定します。

### 橋渡しドキュメント

これは新しい主線章ではなく、中盤以降の理解をつなぐための補助文書です。

- なぜこの章順なのか: [`docs/ja/s00d-chapter-order-rationale.md`](./docs/ja/s00d-chapter-order-rationale.md)
- このリポジトリのコード読解順: [`docs/ja/s00f-code-reading-order.md`](./docs/ja/s00f-code-reading-order.md)
- 参照リポジトリのモジュール対応: [`docs/ja/s00e-reference-module-map.md`](./docs/ja/s00e-reference-module-map.md)
- クエリ制御プレーン: [`docs/ja/s00a-query-control-plane.md`](./docs/ja/s00a-query-control-plane.md)
- 1リクエストの全ライフサイクル: [`docs/ja/s00b-one-request-lifecycle.md`](./docs/ja/s00b-one-request-lifecycle.md)
- クエリ遷移モデル: [`docs/ja/s00c-query-transition-model.md`](./docs/ja/s00c-query-transition-model.md)
- ツール制御プレーン: [`docs/ja/s02a-tool-control-plane.md`](./docs/ja/s02a-tool-control-plane.md)
- ツール実行ランタイム: [`docs/ja/s02b-tool-execution-runtime.md`](./docs/ja/s02b-tool-execution-runtime.md)
- Message / Prompt パイプライン: [`docs/ja/s10a-message-prompt-pipeline.md`](./docs/ja/s10a-message-prompt-pipeline.md)
- ランタイムタスクモデル: [`docs/ja/s13a-runtime-task-model.md`](./docs/ja/s13a-runtime-task-model.md)
- MCP 能力レイヤー: [`docs/ja/s19a-mcp-capability-layers.md`](./docs/ja/s19a-mcp-capability-layers.md)
- Teammate・Task・Lane モデル: [`docs/ja/team-task-lane-model.md`](./docs/ja/team-task-lane-model.md)
- エンティティ地図: [`docs/ja/entity-map.md`](./docs/ja/entity-map.md)

### 4 段階の主線

1. `s01-s06`: まず単体 agent のコアを作る
2. `s07-s11`: 安全性、拡張性、記憶、prompt、recovery を足す
3. `s12-s14`: 一時的な計画を持続的なランタイム作業へ育てる
4. `s15-s19`: チーム、プロトコル、自律動作、分離実行、外部 capability routing へ進む

### 主線の章

| 章 | テーマ | 得られるもの |
|---|---|---|
| `s00` | Architecture Overview | 全体マップ、用語、学習順 |
| `s01` | Agent Loop | 最小の動く agent ループ |
| `s02` | Tool Use | 安定したツール分配 |
| `s03` | Todo / Planning | 可視化されたセッション計画 |
| `s04` | Subagent | 委譲時の新鮮な文脈 |
| `s05` | Skills | 必要な知識だけを後から読む仕組み |
| `s06` | Context Compact | アクティブ文脈を小さく保つ |
| `s07` | Permission System | 実行前の安全ゲート |
| `s08` | Hook System | ループ周辺の拡張点 |
| `s09` | Memory System | セッションをまたぐ長期情報 |
| `s10` | System Prompt | セクション分割された prompt 組み立て |
| `s11` | Error Recovery | 続行・再試行・停止の分岐 |
| `s12` | Task System | 永続タスクグラフ |
| `s13` | Background Tasks | 非ブロッキング実行 |
| `s14` | Cron Scheduler | 時間起点のトリガー |
| `s15` | Agent Teams | 永続チームメイト |
| `s16` | Team Protocols | 共有された協調ルール |
| `s17` | Autonomous Agents | 自律的な認識・再開 |
| `s18` | Worktree Isolation | 分離実行レーン |
| `s19` | MCP & Plugin | 外部 capability routing |

## クイックスタート

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env
```

その後、`.env` に `ANTHROPIC_API_KEY` または互換エンドポイントを設定してから:

```sh
python agents/s01_agent_loop.py
python agents/s18_worktree_task_isolation.py
python agents/s19_mcp_plugin.py
python agents/s_full.py
```

おすすめの進め方:

1. まず `s01` を動かし、最小ループが本当に動くことを確認する
2. `s00` を読みながら `s01 -> s11` を順に進める
3. 単体 agent 本体と control plane が安定して理解できてから `s12 -> s19` に入る
4. 最後に `s_full.py` を見て、全部の機構を一枚の全体像に戻す

## 各章の読み方

各章は、次の順序で読むと理解しやすいです。

1. この機構がないと何が困るか
2. 新しい概念は何か
3. 最小で正しい実装は何か
4. 状態はどこに置かれるのか
5. それがループにどう接続されるのか
6. この章ではどこで一度止まり、何を後回しにしてよいのか

もし読んでいて:

- 「これは主線なのか、補足なのか」
- 「この状態は結局どこにあるのか」

と迷ったら、次を見直してください。

- [`docs/ja/teaching-scope.md`](./docs/ja/teaching-scope.md)
- [`docs/ja/data-structures.md`](./docs/ja/data-structures.md)
- [`docs/ja/entity-map.md`](./docs/ja/entity-map.md)

## 構成

```text
learn-claude-code/
├── agents/              # 章ごとの実行可能な Python 参考実装
├── docs/zh/             # 中国語の主線文書
├── docs/en/             # 英語文書
├── docs/ja/             # 日本語文書
├── skills/              # s05 で使う skill ファイル
├── web/                 # Web 教学プラットフォーム
└── requirements.txt
```

## 言語の状態

中国語が正本であり、更新も最も速いです。

- `zh`: 最も完全で、最もレビューされている
- `en`: 主線章と主要な橋渡し文書が利用できる
- `ja`: 主線章と主要な橋渡し文書が利用できる

最も深く、最も更新の速い説明を追うなら、まず中国語版を優先してください。

## 最終目標

読み終わるころには、次の問いに自分の言葉で答えられるようになるはずです。

- coding agent の最小状態は何か
- `tool_result` がなぜループの中心なのか
- どういう時に subagent を使うべきか
- permissions、hooks、memory、prompt、task がそれぞれ何を解決するのか
- いつ単体 agent を tasks、teams、worktrees、MCP へ成長させるべきか

それを説明できて、自分で似たシステムを作れるなら、このリポジトリの目的は達成です。
