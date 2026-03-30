# Learn Claude Code -- 真の Agent のための Harness Engineering

[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md)

## モデルこそが Agent である

コードの話をする前に、一つだけ明確にしておく。

**Agent とはモデルのことだ。フレームワークではない。プロンプトチェーンではない。ドラッグ＆ドロップのワークフローではない。**

### Agent とは何か

Agent とはニューラルネットワークである -- Transformer、RNN、学習された関数 -- 数十億回の勾配更新を経て、行動系列データの上で環境を知覚し、目標を推論し、行動を起こすことを学んだもの。AI における "Agent" という言葉は、始まりからずっとこの意味だった。常に。

人間も Agent だ。数百万年の進化的訓練によって形作られた生物的ニューラルネットワーク。感覚で世界を知覚し、脳で推論し、身体で行動する。DeepMind、OpenAI、Anthropic が "Agent" と言うとき、それはこの分野が誕生以来ずっと意味してきたものと同じだ：**行動することを学んだモデル。**

歴史がその証拠を刻んでいる：

- **2013 -- DeepMind DQN が Atari をプレイ。** 単一のニューラルネットワークが、生のピクセルとスコアだけを受け取り、7 つの Atari 2600 ゲームを学習 -- すべての先行アルゴリズムを超え、3 つで人間の専門家を打ち負かした。2015 年には同じアーキテクチャが [49 ゲームに拡張され、プロのテスターに匹敵](https://www.nature.com/articles/nature14236)、*Nature* に掲載。ゲーム固有のルールなし。決定木なし。一つのモデルが経験から学んだ。そのモデルが Agent だった。

- **2019 -- OpenAI Five が Dota 2 を制覇。** 5 つのニューラルネットワークが 10 ヶ月間で [45,000 年分の Dota 2](https://openai.com/index/openai-five-defeats-dota-2-world-champions/) を自己対戦し、サンフランシスコのライブストリームで **OG** -- TI8 世界王者 -- を 2-0 で撃破。その後の公開アリーナでは 42,729 試合で勝率 99.4%。スクリプト化された戦略なし。メタプログラムされたチーム連携なし。モデルが完全に自己対戦を通じてチームワーク、戦術、リアルタイム適応を学んだ。

- **2019 -- DeepMind AlphaStar が StarCraft II をマスター。** AlphaStar は非公開戦で[プロ選手を 10-1 で撃破](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/)、その後ヨーロッパサーバーで[グランドマスター到達](https://www.nature.com/articles/d41586-019-03298-6) -- 90,000 人中の上位 0.15%。不完全情報、リアルタイム判断、チェスや囲碁を遥かに凌駕する組合せ的行動空間を持つゲーム。Agent とは？ モデルだ。訓練されたもの。スクリプトではない。

- **2019 -- Tencent 絶悟が王者栄耀を支配。** Tencent AI Lab の「絶悟」は 2019 年 8 月 2 日、世界チャンピオンカップで [KPL プロ選手を 5v5 で撃破](https://www.jiemian.com/article/3371171.html)。1v1 モードではプロが [15 戦中 1 勝のみ、8 分以上生存不可](https://developer.aliyun.com/article/851058)。訓練強度：1 日 = 人間の 440 年。2021 年までに全ヒーロープールで KPL プロを全面的に上回った。手書きのヒーロー相性表なし。スクリプト化されたチーム編成なし。自己対戦でゲーム全体をゼロから学んだモデル。

- **2024-2025 -- LLM Agent がソフトウェアエンジニアリングを再構築。** Claude、GPT、Gemini -- 人類のコードと推論の全幅で訓練された大規模言語モデル -- がコーディング Agent として展開される。コードベースを読み、実装を書き、障害をデバッグし、チームで協調する。アーキテクチャは先行するすべての Agent と同一：訓練されたモデルが環境に配置され、知覚と行動のツールを与えられる。唯一の違いは、学んだものの規模と解くタスクの汎用性。

すべてのマイルストーンが同じ真理を共有している：**"Agent" は決して周囲のコードではない。Agent は常にモデルそのものだ。**

### Agent ではないもの

"Agent" という言葉は、プロンプト配管工の産業全体に乗っ取られてしまった。

ドラッグ＆ドロップのワークフロービルダー。ノーコード "AI Agent" プラットフォーム。プロンプトチェーン・オーケストレーションライブラリ。すべて同じ幻想を共有している：LLM API 呼び出しを if-else 分岐、ノードグラフ、ハードコードされたルーティングロジックで繋ぎ合わせることが "Agent の構築" だと。

違う。彼らが作ったものはルーブ・ゴールドバーグ・マシンだ -- 過剰に設計された脆い手続き的ルールのパイプライン。LLM は美化されたテキスト補完ノードとして押し込まれているだけ。それは Agent ではない。壮大な妄想を持つシェルスクリプトだ。

**プロンプト配管工式 "Agent" は、モデルを訓練しないプログラマーの妄想だ。** 手続き的ロジックを積み重ねて知能を力技で再現しようとする -- 巨大なルールツリー、ノードグラフ、チェーン・プロンプトの滝 -- そして十分なグルーコードがいつか自律的振る舞いを創発すると祈る。しない。工学的手段で Agency をコーディングすることはできない。Agency は学習されるものであって、プログラムされるものではない。

あのシステムたちは生まれた瞬間から死んでいる：脆弱で、スケールせず、汎化が根本的に不可能。GOFAI（Good Old-Fashioned AI、古典的記号 AI）の現代版だ -- 何十年も前に学術界が放棄した記号ルールシステムが、LLM のペンキを塗り直して再登場した。パッケージが違うだけで、同じ袋小路。

### マインドシフト：「Agent を開発する」から Harness を開発する へ

「Agent を開発しています」と言うとき、意味できるのは二つだけだ：

**1. モデルを訓練する。** 強化学習、ファインチューニング、RLHF、その他の勾配ベースの手法で重みを調整する。タスクプロセスデータ -- 実ドメインにおける知覚・推論・行動の実際の系列 -- を収集し、モデルの振る舞いを形成する。DeepMind、OpenAI、Tencent AI Lab、Anthropic が行っていること。これが最も本来的な Agent 開発。

**2. Harness を構築する。** モデルに動作環境を提供するコードを書く。私たちの大半が行っていることであり、このリポジトリの核心。

Harness とは、Agent が特定のドメインで機能するために必要なすべて：

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

    Tools:          ファイル I/O、シェル、ネットワーク、データベース、ブラウザ
    Knowledge:      製品ドキュメント、ドメイン資料、API 仕様、スタイルガイド
    Observation:    git diff、エラーログ、ブラウザ状態、センサーデータ
    Action:         CLI コマンド、API 呼び出し、UI インタラクション
    Permissions:    サンドボックス、承認ワークフロー、信頼境界
```

モデルが決断する。Harness が実行する。モデルが推論する。Harness がコンテキストを提供する。モデルはドライバー。Harness は車両。

**コーディング Agent の Harness は IDE、ターミナル、ファイルシステム。** 農業 Agent の Harness はセンサーアレイ、灌漑制御、気象データフィード。ホテル Agent の Harness は予約システム、ゲストコミュニケーションチャネル、施設管理 API。Agent -- 知性、意思決定者 -- は常にモデル。Harness はドメインごとに変わる。Agent はドメインを超えて汎化する。

このリポジトリは車両の作り方を教える。コーディング用の車両だ。だが設計パターンはあらゆるドメインに汎化する：農場管理、ホテル運営、工場製造、物流、医療、教育、科学研究。タスクが知覚され、推論され、実行される必要がある場所ならどこでも -- Agent には Harness が要る。

### Harness エンジニアの仕事

このリポジトリを読んでいるなら、あなたはおそらく Harness エンジニアだ -- それは強力なアイデンティティ。以下があなたの本当の仕事：

- **ツールの実装。** Agent に手を与える。ファイル読み書き、シェル実行、API 呼び出し、ブラウザ制御、データベースクエリ。各ツールは Agent が環境内で取れる行動。原子的で、組み合わせ可能で、記述が明確であるように設計する。

- **知識のキュレーション。** Agent にドメイン専門性を与える。製品ドキュメント、アーキテクチャ決定記録、スタイルガイド、規制要件。オンデマンドで読み込み（s05）、前もって詰め込まない。Agent は何が利用可能か知った上で、必要なものを自ら取得すべき。

- **コンテキストの管理。** Agent にクリーンな記憶を与える。サブ Agent 隔離（s04）がノイズの漏洩を防ぐ。コンテキスト圧縮（s06）が履歴の氾濫を防ぐ。タスクシステム（s07）が目標を単一の会話を超えて永続化する。

- **権限の制御。** Agent に境界を与える。ファイルアクセスのサンドボックス化。破壊的操作への承認要求。Agent と外部システム間の信頼境界の実施。安全工学と Harness 工学の交差点。

- **タスクプロセスデータの収集。** Agent があなたの Harness 内で実行するすべての行動系列は訓練シグナル。実デプロイメントの知覚-推論-行動トレースは、次世代 Agent モデルをファインチューニングする原材料。あなたの Harness は Agent に仕えるだけでなく -- Agent を進化させる助けにもなる。

あなたは知性を書いているのではない。知性が住まう世界を構築している。その世界の品質 -- Agent がどれだけ明瞭に知覚でき、どれだけ正確に行動でき、利用可能な知識がどれだけ豊かか -- が、知性がどれだけ効果的に自らを表現できるかを直接決定する。

**優れた Harness を作れ。Agent が残りをやる。**

### なぜ Claude Code か -- Harness Engineering の大師範

なぜこのリポジトリは特に Claude Code を解剖するのか？

Claude Code は私たちが見てきた中で最もエレガントで完成度の高い Agent Harness だからだ。単一の巧妙なトリックのためではなく、それが *しないこと* のために：Agent そのものになろうとしない。硬直的なワークフローを押し付けない。精緻な決定木でモデルを二度推しない。ツール、知識、コンテキスト管理、権限境界をモデルに提供し -- そして道を譲る。

Claude Code の本質を剥き出しにすると：

```
Claude Code = 一つの agent loop
            + ツール (bash, read, write, edit, glob, grep, browser...)
            + オンデマンド skill ロード
            + コンテキスト圧縮
            + サブ Agent スポーン
            + 依存グラフ付きタスクシステム
            + 非同期メールボックスによるチーム協調
            + worktree 分離による並列実行
            + 権限ガバナンス
```

これがすべてだ。これが全アーキテクチャ。すべてのコンポーネントは Harness メカニズム -- Agent が住む世界の一部。Agent そのものは？ Claude だ。モデル。Anthropic が人類の推論とコードの全幅で訓練した。Harness が Claude を賢くしたのではない。Claude は元々賢い。Harness が Claude に手と目とワークスペースを与えた。

これが Claude Code が理想的な教材である理由だ：**モデルを信頼し、工学的努力を Harness に集中させるとどうなるかを示している。** このリポジトリの各セッション（s01-s12）は Claude Code アーキテクチャから一つの Harness メカニズムをリバースエンジニアリングする。終了時には、Claude Code の仕組みだけでなく、あらゆるドメインのあらゆる Agent に適用される Harness 工学の普遍的原則を理解している。

教訓は「Claude Code をコピーせよ」ではない。教訓は：**最高の Agent プロダクトは、自分の仕事が Harness であって Intelligence ではないと理解しているエンジニアが作る。**

---

## ビジョン：宇宙を本物の Agent で満たす

これはコーディング Agent だけの話ではない。

人間が複雑で多段階の判断集約的な仕事をしているすべてのドメインは、Agent が稼働できるドメインだ -- 正しい Harness さえあれば。このリポジトリのパターンは普遍的だ：

```
不動産管理 Agent  = モデル + 物件センサー + メンテナンスツール + テナント通信
農業 Agent        = モデル + 土壌/気象データ + 灌漑制御 + 作物知識
ホテル運営 Agent  = モデル + 予約システム + ゲストチャネル + 施設 API
医学研究 Agent    = モデル + 文献検索 + 実験機器 + プロトコル文書
製造 Agent        = モデル + 生産ラインセンサー + 品質管理 + 物流
教育 Agent        = モデル + カリキュラム知識 + 学生進捗 + 評価ツール
```

ループは常に同じ。ツールが変わる。知識が変わる。権限が変わる。Agent -- モデル -- がすべてを汎化する。

このリポジトリを読むすべての Harness エンジニアは、ソフトウェアエンジニアリングを遥かに超えたパターンを学んでいる。知的で自動化された未来のためのインフラストラクチャを構築することを学んでいる。実ドメインにデプロイされた優れた Harness の一つ一つが、Agent が知覚し、推論し、行動できる新たな拠点。

まずワークショップを満たす。次に農場、病院、工場。次に都市。次に惑星。

**Bash is all you need. Real agents are all the universe needs.**

---

```
                    THE AGENT PATTERN
                    =================

    User --> messages[] --> LLM --> response
                                      |
                            stop_reason == "tool_use"?
                           /                          \
                         yes                           no
                          |                             |
                    execute tools                    return text
                    append results
                    loop back -----------------> messages[]


    最小ループ。すべての AI Agent にこのループが必要だ。
    モデルがツール呼び出しと停止を決める。
    コードはモデルの要求を実行するだけ。
    このリポジトリはこのループを囲むすべて --
    Agent を特定ドメインで効果的にする Harness -- の作り方を教える。
```

**12 の段階的セッション、シンプルなループから分離された自律実行まで。**
**各セッションは 1 つの Harness メカニズムを追加する。各メカニズムには 1 つのモットーがある。**

> **s01** &nbsp; *"One loop & Bash is all you need"* &mdash; 1つのツール + 1つのループ = エージェント
>
> **s02** &nbsp; *"ツールを足すなら、ハンドラーを1つ足すだけ"* &mdash; ループは変わらない。新ツールは dispatch map に登録するだけ
>
> **s03** &nbsp; *"計画のないエージェントは行き当たりばったり"* &mdash; まずステップを書き出し、それから実行
>
> **s04** &nbsp; *"大きなタスクを分割し、各サブタスクにクリーンなコンテキストを"* &mdash; サブエージェントは独立した messages[] を使い、メイン会話を汚さない
>
> **s05** &nbsp; *"必要な知識を、必要な時に読み込む"* &mdash; system prompt ではなく tool_result で注入
>
> **s06** &nbsp; *"コンテキストはいつか溢れる、空ける手段が要る"* &mdash; 3層圧縮で無限セッションを実現
>
> **s07** &nbsp; *"大きな目標を小タスクに分解し、順序付けし、ディスクに記録する"* &mdash; ファイルベースのタスクグラフ、マルチエージェント協調の基盤
>
> **s08** &nbsp; *"遅い操作はバックグラウンドへ、エージェントは次を考え続ける"* &mdash; デーモンスレッドがコマンド実行、完了後に通知を注入
>
> **s09** &nbsp; *"一人で終わらないなら、チームメイトに任せる"* &mdash; 永続チームメイト + 非同期メールボックス
>
> **s10** &nbsp; *"チームメイト間には統一の通信ルールが必要"* &mdash; 1つの request-response パターンが全交渉を駆動
>
> **s11** &nbsp; *"チームメイトが自らボードを見て、仕事を取る"* &mdash; リーダーが逐一割り振る必要はない
>
> **s12** &nbsp; *"各自のディレクトリで作業し、互いに干渉しない"* &mdash; タスクは目標を管理、worktree はディレクトリを管理、IDで紐付け

---

## コアパターン

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant",
                         "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

各セッションはこのループの上に 1 つの Harness メカニズムを重ねる -- ループ自体は変わらない。ループは Agent のもの。メカニズムは Harness のもの。

## スコープ (重要)

このリポジトリは Harness 工学の 0->1 学習プロジェクト -- Agent モデルを囲む環境の構築を学ぶ。
学習を優先するため、以下の本番メカニズムは意図的に簡略化または省略している：

- 完全なイベント / Hook バス (例: PreToolUse, SessionStart/End, ConfigChange)。
  s12 では教材用に最小の追記型ライフサイクルイベントのみ実装。
- ルールベースの権限ガバナンスと信頼フロー
- セッションライフサイクル制御 (resume/fork) と高度な worktree ライフサイクル制御
- MCP ランタイムの詳細 (transport/OAuth/リソース購読/ポーリング)

このリポジトリの JSONL メールボックス方式は教材用の実装であり、特定の本番内部実装を主張するものではない。

## クイックスタート

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code

# Install directly
pip install -r requirements.txt

# Use anaconda/miniconda to manage python environments
# conda env create -f environment.yml

cp .env.example .env   # .env を編集して ANTHROPIC_API_KEY を入力

python agents/s01_agent_loop.py       # ここから開始
python agents/s12_worktree_task_isolation.py  # 全セッションの到達点
python agents/s_full.py               # 総括: 全メカニズム統合
```

### Web プラットフォーム

インタラクティブな可視化、ステップスルーアニメーション、ソースビューア、各セッションのドキュメント。

```sh
cd web && npm install && npm run dev   # http://localhost:3000
```

## 学習パス

```
フェーズ1: ループ                     フェーズ2: 計画と知識
==================                   ==============================
s01  エージェントループ      [1]     s03  TodoWrite               [5]
     while + stop_reason                  TodoManager + nag リマインダー
     |                                    |
     +-> s02  Tool Use            [4]     s04  サブエージェント      [5]
              dispatch map: name->handler     子ごとに新しい messages[]
                                              |
                                         s05  Skills               [5]
                                              SKILL.md を tool_result で注入
                                              |
                                         s06  Context Compact      [5]
                                              3層コンテキスト圧縮

フェーズ3: 永続化                     フェーズ4: チーム
==================                   =====================
s07  タスクシステム           [8]     s09  エージェントチーム      [9]
     ファイルベース CRUD + 依存グラフ      チームメイト + JSONL メールボックス
     |                                    |
s08  バックグラウンドタスク   [6]     s10  チームプロトコル        [12]
     デーモンスレッド + 通知キュー         シャットダウン + プラン承認 FSM
                                          |
                                     s11  自律エージェント        [14]
                                          アイドルサイクル + 自動クレーム
                                     |
                                     s12  Worktree 分離           [16]
                                          タスク調整 + 必要時の分離実行レーン

                                     [N] = ツール数
```

## プロジェクト構成

```
learn-claude-code/
|
|-- agents/                        # Python リファレンス実装 (s01-s12 + s_full 総括)
|-- docs/{en,zh,ja}/               # メンタルモデル優先のドキュメント (3言語)
|-- web/                           # インタラクティブ学習プラットフォーム (Next.js)
|-- skills/                        # s05 の Skill ファイル
+-- .github/workflows/ci.yml      # CI: 型チェック + ビルド
```

## ドキュメント

メンタルモデル優先: 問題、解決策、ASCII図、最小限のコード。
[English](./docs/en/) | [中文](./docs/zh/) | [日本語](./docs/ja/)

| セッション | トピック | モットー |
|-----------|---------|---------|
| [s01](./docs/ja/s01-the-agent-loop.md) | エージェントループ | *One loop & Bash is all you need* |
| [s02](./docs/ja/s02-tool-use.md) | Tool Use | *ツールを足すなら、ハンドラーを1つ足すだけ* |
| [s03](./docs/ja/s03-todo-write.md) | TodoWrite | *計画のないエージェントは行き当たりばったり* |
| [s04](./docs/ja/s04-subagent.md) | サブエージェント | *大きなタスクを分割し、各サブタスクにクリーンなコンテキストを* |
| [s05](./docs/ja/s05-skill-loading.md) | Skills | *必要な知識を、必要な時に読み込む* |
| [s06](./docs/ja/s06-context-compact.md) | Context Compact | *コンテキストはいつか溢れる、空ける手段が要る* |
| [s07](./docs/ja/s07-task-system.md) | タスクシステム | *大きな目標を小タスクに分解し、順序付けし、ディスクに記録する* |
| [s08](./docs/ja/s08-background-tasks.md) | バックグラウンドタスク | *遅い操作はバックグラウンドへ、エージェントは次を考え続ける* |
| [s09](./docs/ja/s09-agent-teams.md) | エージェントチーム | *一人で終わらないなら、チームメイトに任せる* |
| [s10](./docs/ja/s10-team-protocols.md) | チームプロトコル | *チームメイト間には統一の通信ルールが必要* |
| [s11](./docs/ja/s11-autonomous-agents.md) | 自律エージェント | *チームメイトが自らボードを見て、仕事を取る* |
| [s12](./docs/ja/s12-worktree-task-isolation.md) | Worktree + タスク分離 | *各自のディレクトリで作業し、互いに干渉しない* |

## 次のステップ -- 理解から出荷へ

12 セッションを終えれば、Harness 工学の内部構造を完全に理解している。その知識を活かす 2 つの方法:

### Kode Agent CLI -- オープンソース Coding Agent CLI

> `npm i -g @shareai-lab/kode`

Skill & LSP 対応、Windows 対応、GLM / MiniMax / DeepSeek 等のオープンモデルに接続可能。インストールしてすぐ使える。

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK -- アプリにエージェント機能を埋め込む

公式 Claude Code Agent SDK は内部で完全な CLI プロセスと通信する -- 同時ユーザーごとに独立のターミナルプロセスが必要。Kode SDK は独立ライブラリでユーザーごとのプロセスオーバーヘッドがなく、バックエンド、ブラウザ拡張、組み込みデバイス等に埋め込み可能。

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## 姉妹教材: *オンデマンドセッション*から*常時稼働アシスタント*へ

本リポジトリが教える Harness は **使い捨て型** -- ターミナルを開き、Agent にタスクを与え、終わったら閉じる。次のセッションは白紙から始まる。Claude Code のモデル。

[OpenClaw](https://github.com/openclaw/openclaw) は別の可能性を証明した: 同じ agent core の上に 2 つの Harness メカニズムを追加するだけで、Agent は「突かないと動かない」から「30 秒ごとに自分で起きて仕事を探す」に変わる:

- **ハートビート** -- 30 秒ごとに Harness が Agent にメッセージを送り、やることがあるか確認させる。なければスリープ続行、あれば即座に行動。
- **Cron** -- Agent が自ら未来のタスクをスケジュールし、時間が来たら自動実行。

さらにマルチチャネル IM ルーティング (WhatsApp / Telegram / Slack / Discord 等 13+ プラットフォーム)、永続コンテキストメモリ、Soul パーソナリティシステムを加えると、Agent は使い捨てツールから常時稼働のパーソナル AI アシスタントへ変貌する。

**[claw0](https://github.com/shareAI-lab/claw0)** はこれらの Harness メカニズムをゼロから分解する姉妹教材リポジトリ:

```
claw agent = agent core + heartbeat + cron + IM chat + memory + soul
```

```
learn-claude-code                   claw0
(agent harness コア:                 (能動的な常時稼働 harness:
 ループ、ツール、計画、                ハートビート、cron、IM チャネル、
 チーム、worktree 分離)                メモリ、Soul パーソナリティ)
```

## ライセンス

MIT

---

**モデルが Agent だ。コードは Harness だ。優れた Harness を作れ。Agent が残りをやる。**

**Bash is all you need. Real agents are all the universe needs.**
