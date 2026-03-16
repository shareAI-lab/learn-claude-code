# Learn Claude Code -- 0 から 1 へ構築する nano Claude Code-like agent

[English](./README.md) | [简体中文](./README-zh.md) | [日本語](./README-ja.md) | [繁體中文](./README-zhtw.md)

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


    これは最小ループだ。すべての AI コーディングエージェントに必要な土台になる。
    本番のエージェントには、ポリシー・権限・ライフサイクル層が追加される。
```

**12 の段階的セッション、シンプルなループから分離された自律実行まで。**
**各セッションは1つのメカニズムを追加する。各メカニズムには1つのモットーがある。**

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

各セッションはこのループの上に1つのメカニズムを重ねる -- ループ自体は変わらない。

## スコープ (重要)

このリポジトリは、nano Claude Code-like agent を 0->1 で構築・学習するための教材プロジェクトです。
学習を優先するため、以下の本番メカニズムは意図的に簡略化または省略しています。

- 完全なイベント / Hook バス (例: PreToolUse, SessionStart/End, ConfigChange)。  
  s12 では教材用に最小の追記型ライフサイクルイベントのみ実装している。
- ルールベースの権限ガバナンスと信頼フロー
- セッションライフサイクル制御 (resume/fork) と高度な worktree ライフサイクル制御
- MCP ランタイムの詳細 (transport/OAuth/リソース購読/ポーリング)

このリポジトリの JSONL メールボックス方式は教材用の実装であり、特定の本番内部実装を主張するものではありません。

## クイックスタート

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
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

12 セッションを終えれば、エージェントの内部構造を完全に理解している。その知識を活かす 2 つの方法:

### Kode Agent CLI -- オープンソース Coding Agent CLI

> `npm i -g @shareai-lab/kode`

Skill & LSP 対応、Windows 対応、GLM / MiniMax / DeepSeek 等のオープンモデルに接続可能。インストールしてすぐ使える。

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK -- アプリにエージェント機能を埋め込む

公式 Claude Code Agent SDK は内部で完全な CLI プロセスと通信する -- 同時ユーザーごとに独立のターミナルプロセスが必要。Kode SDK は独立ライブラリでユーザーごとのプロセスオーバーヘッドがなく、バックエンド、ブラウザ拡張、組み込みデバイス等に埋め込み可能。

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## 姉妹教材: *オンデマンドセッション*から*常時稼働アシスタント*へ

本リポジトリが教えるエージェントは **使い捨て型** -- ターミナルを開き、タスクを与え、終わったら閉じる。次のセッションは白紙から始まる。これが Claude Code のモデル。

[OpenClaw](https://github.com/openclaw/openclaw) は別の可能性を証明した: 同じ agent core の上に 2 つのメカニズムを追加するだけで、エージェントは「突かないと動かない」から「30 秒ごとに自分で起きて仕事を探す」に変わる:

- **ハートビート** -- 30 秒ごとにシステムがエージェントにメッセージを送り、やることがあるか確認させる。なければスリープ続行、あれば即座に行動。
- **Cron** -- エージェントが自ら未来のタスクをスケジュールし、時間が来たら自動実行。

さらにマルチチャネル IM ルーティング (WhatsApp / Telegram / Slack / Discord 等 13+ プラットフォーム)、永続コンテキストメモリ、Soul パーソナリティシステムを加えると、エージェントは使い捨てツールから常時稼働のパーソナル AI アシスタントへ変貌する。

**[claw0](https://github.com/shareAI-lab/claw0)** はこれらのメカニズムをゼロから分解する姉妹教材リポジトリ:

```
claw agent = agent core + heartbeat + cron + IM chat + memory + soul
```

```
learn-claude-code                   claw0
(エージェントランタイムコア:          (能動的な常時稼働アシスタント:
 ループ、ツール、計画、                ハートビート、cron、IM チャネル、
 チーム、worktree 分離)                メモリ、Soul パーソナリティ)
```

## ライセンス

MIT

---

**モデルがエージェントだ。私たちの仕事はツールを与えて邪魔しないこと。**
