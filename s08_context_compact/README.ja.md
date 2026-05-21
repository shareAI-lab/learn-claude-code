# s08: Context Compact — コンテキストはいつか満杯になる、場所を空ける方法が必要

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → s02 → s03 → s04 → s05 → s06 → s07 → `s08` → [s09](../s09_memory/) → s10 → ... → s20
> *"Context will fill up — have a way to make room"* — 4層圧縮戦略、安価なものを先に、高価なものを後に実行。
>
> **Harness レイヤー**: 圧縮 — クリーンな記憶、無限のセッション。

---

## 課題

Agent が動いている途中で、止まってしまう。

bash、read、write は揃っており、能力は十分。しかし 1000 行のファイル（~4000 token）を読み、さらに 30 のファイルを読み、20 のコマンドを実行したとします。各コマンドの出力、各ファイルの内容がすべて `messages` リストに蓄積されます。

コンテキストウィンドウには上限があります。満杯になると、API は即座に拒否します：`prompt_too_long`。

圧縮しなければ、Agent は大規模プロジェクトではまともに動けません。

---

## ソリューション

![Compact Overview](images/compact-overview.ja.svg)

s07 のフック構造、スキルロード、サブ Agent の骨格を維持し、圧縮に焦点を当てるため一部のツールは省略。コアの変更点：各 LLM 呼び出し前に 3 層のプリプロセッサ（0 API）を挿入し、token が閾値を超えた場合は LLM 要約（1 API）をトリガー、API エラー時には緊急トリムを実行。

コア設計：安価なものを先に、高価なものを後に。

---

## 仕組み

![4層圧縮パイプライン](images/compaction-layers.ja.svg)

### L1: snip_compact — 無関係な古い会話を切り捨て

Agent が 80 ラウンドの会話を実行し、`messages` が 160 件まで溜まった。先頭の「hello.py を作って」は現在の作業とほぼ無関係だが、スペースを占有し続けている。

メッセージ数が 50 を超えた場合 → 先頭 3 件（初期コンテキスト）と末尾 47 件（現在の作業）を保持し、中間を切り捨て：

```python
def snip_compact(messages, max_messages=50):
    if len(messages) <= max_messages:
        return messages
    keep_head, keep_tail = 3, max_messages - 3
    snipped = len(messages) - keep_head - keep_tail
    placeholder = {"role": "user",
                   "content": f"[snipped {snipped} messages from conversation middle]"}
    return messages[:keep_head] + [placeholder] + messages[-keep_tail:]
```

メッセージ全体は切り捨てたが、残ったメッセージ内の `tool_result` 内容はまだ蓄積され続けている。34 番目のメッセージに 30KB の古いファイル内容が残っているかもしれない。→ L2。

### L2: micro_compact — 古いツール結果をプレースホルダに置換

![古い結果のプレースホルダ](images/micro-compact.ja.svg)

Agent が連続して 10 個のファイルを読んだ。1〜7 回目の完全な内容はまだコンテキストに残っており、もう不要だが、大量のスペースを占有している。

直近 3 件の `tool_result` の完全な内容のみを保持し、それより古いものは 1 行のプレースホルダに置換：

```python
KEEP_RECENT_TOOL_RESULTS = 3

def micro_compact(messages):
    tool_results = collect_tool_result_blocks(messages)
    if len(tool_results) <= KEEP_RECENT_TOOL_RESULTS:
        return messages
    for _, _, block in tool_results[:-KEEP_RECENT_TOOL_RESULTS]:
        if len(block.get("content", "")) > 120:
            block["content"] = "[Earlier tool result compacted. Re-run if needed.]"
    return messages
```

古い結果はクリーンアップされたが、1 件の新しい結果だけで 500KB の可能性がある。大きなファイルを `cat` するだけでコンテキストがいっぱいになる。→ L3。

### L3: tool_result_budget — 大きな結果をディスクに退避

![大きな結果のディスク退避](images/layer1-budget.ja.svg)

モデルが一度に 5 つの大きなファイルを読み、1 つの user メッセージ内の全 `tool_result` の合計が 500KB に達した。

最後の user メッセージ内のすべての `tool_result` の合計サイズを集計。200KB を超えた場合 → サイズ順にソートし、最大のものから順に `.task_outputs/tool-results/` に退避。コンテキストには `<persisted-output>` マーカー + 先頭 2000 文字のプレビューのみを残す。モデルはマーカーを見て完全な内容がディスク上にあることを認識し、必要に応じて再読み込みできる。

```python
def tool_result_budget(messages, max_bytes=200_000):
    last = messages[-1]
    blocks = [(i, b) for i, b in enumerate(last["content"])
              if b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= max_bytes:
        return messages
    ranked = sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True)
    for idx, block in ranked:
        if total <= max_bytes:
            break
        block["content"] = persist_large_output(block["tool_use_id"], str(block["content"]))
        total = recalculate_total(blocks)
    return messages
```

最初の 3 層はすべて純粋なテキスト/構造操作（0 API 呼び出し）だが、会話内容を「理解」することはできない。コンテキストがまだ大きすぎる可能性がある。→ L4。

### L4: compact_history — LLM 全量要約

![LLM 全量要約](images/auto-compact.ja.svg)

最初の 3 層がすべて実行されたが、超大規模プロジェクトで 30 分間連続作業すると、token がまだ閾値を超えている。

3 ステップのフロー：

1. **transcript を保存**：完全な会話を `.transcripts/` に JSONL 形式で書き出す。transcript は回復可能な記録として保存されるが、モデルのアクティブなコンテキストには要約しか残らない。モデルの現在の推論にとって、詳細はすでにコンテキストにない。教学コードは transcript 検索ツールを提供しない。
2. **LLM で要約を生成**：会話履歴を LLM に送り、現在の目標、重要な発見、変更済みファイル、残りの作業、ユーザーの制約などの重要な情報を保持するよう指示。
3. **メッセージリストを置換**：すべての古いメッセージが 1 件の要約に置き換えられる。教学版は要約のみを保持する。実際の Claude Code は compact 後に直近のファイル、計画、agent/skill/tool などのコンテキストを再付加する。

```python
def compact_history(messages):
    transcript_path = write_transcript(messages)  # 先に完全な会話を保存
    summary = summarize_history(messages)          # LLM で要約を生成
    return [{"role": "user",
             "content": f"[Compacted]\n\n{summary}"}]
```

**サーキットブレーカー**：連続 3 回失敗したらリトライを停止し、無限ループによる API 呼び出しの浪費を防止。

### 緊急: reactive_compact

API がまだ `prompt_too_long`（413）を返すことがある。コンテキストの増加速度が圧縮のトリガー速度を上回る場合。

この時 **reactive_compact** がトリガーされる：compact_history よりもさらに積極的で、末尾からバイト単位の精度で API が受け入れ可能なサイズまで切り詰め、最後の 5 件のメッセージ + 要約のみを保持。

```python
def reactive_compact(messages):
    transcript = write_transcript(messages)
    summary = summarize_history(messages)
    tail = messages[-5:]
    return [{"role": "user",
             "content": f"[Reactive compact]\n\n{summary}"}, *tail]
```

reactive compact にはリトライ上限がある（デフォルト 1 回）。さらに失敗した場合は例外をスローし、無限ループしない。完全なエラー回復ロジックは s11 に委ねる。

### 合わせて実行

```python
def agent_loop(messages):
    reactive_retries = 0
    while True:
        # 3 つのプリプロセッサ（0 API 呼び出し）
        # 順序：budget を先に実行し、大きな内容をプレースホルダ化する前に退避
        messages[:] = tool_result_budget(messages)    # L3: 大きな結果を退避
        messages[:] = snip_compact(messages)          # L1: 中間を切り捨て
        messages[:] = micro_compact(messages)         # L2: 古い結果をプレースホルダに

        # まだ足りない？LLM 要約（1 API 呼び出し）
        if estimate_token_count(messages) > THRESHOLD:
            messages[:] = compact_history(messages)

        try:
            response = client.messages.create(...)
        except PromptTooLongError:
            if reactive_retries < MAX_REACTIVE_RETRIES:
                messages[:] = reactive_compact(messages)  # 緊急対応
                reactive_retries += 1
                continue
            raise  # リトライ上限超過、例外をスロー
        # ... ツール実行 ...

        # compact ツール：モデルが能動的に呼び出した場合、compact_history をトリガー
        if block.name == "compact":
            messages[:] = compact_history(messages)
            results.append({..., "content": "[Compacted. History summarized.]"})
            messages.append({"role": "user", "content": results})
            break  # 現在のターンを終了し、圧縮後のコンテキストで新しく開始
```

**順序は変えられない。** L3（budget）が L2（micro）の前に実行される理由：micro は古い大きな tool_result を 1 行のプレースホルダに置換するため、budget はその前に完全な内容を退避させる必要がある。CC ソースが `applyToolResultBudget` を最初に配置する理由も同じ。

---

## s07 からの変更点

| コンポーネント | 変更前 (s07) | 変更後 (s08) |
|------|-----------|-----------|
| コンテキスト管理 | なし（コンテキストが無限に膨張） | 4 層圧縮パイプライン + 緊急対応 |
| 新規関数 | — | snip_compact, micro_compact, tool_result_budget, compact_history, reactive_compact |
| ツール | bash, read_file, write_file, edit_file, glob, todo_write, task, load_skill (8) | 8 + compact (9) |
| ループ | LLM 呼び出し → ツール実行 | 各ラウンド前に 3 層プリプロセッサを実行 + 閾値で compact_history をトリガー |
| 設計原則 | — | 安価なものを先に、高価なものを後に |

---

## 試してみよう

```sh
cd learn-claude-code
python s08_context_compact/code.py
```

以下のプロンプトを試してみてください：

1. `Read the file README.md, then read code.py, then read s01_agent_loop/README.md`（連続して複数のファイルを読み、L2 の古い結果圧縮を観察）
2. `Read every file in s08_context_compact/`（一度に大量の内容を読み込み、L3 のディスク退避を観察）
3. 20+ ラウンドの対話を繰り返し、`[auto compact]` または `[reactive compact]` が表示されるか観察

観察のポイント：ツール実行のたびに、古い tool_result は圧縮されているか？連続対話で token が閾値を超えたとき、要約が自動的にトリガーされたか？

---

## 次へ

コンテキスト圧縮により、Agent は長時間クラッシュせずに動けるようになった。しかし、圧縮のたびにユーザーが以前に伝えた偏好や制約も一緒に失われてしまう。Agent が重要なことを選択的に記憶できるようにできないか？

s09 Memory → 3 つのサブシステム：何を記憶するかの選択、重要情報の抽出、整理と統合。圧縮を越え、セッションを越えて。

<details>
<summary>CC ソースコードの詳細</summary>

> 以下は CC ソースコード `compact.ts`、`autoCompact.ts`、`microCompact.ts`、`query.ts` の分析に基づく。

### 実行順序の対応

教学版は説明の便宜上 L1/L2/L3/L4 と番号を振っているが、実際の実行順序は番号と完全には一致しない：

| 項目 | 教学版 | Claude Code |
|------|--------|-------------|
| 実行順序 | budget → snip → micro → auto | budget → snip → micro → collapse → auto（`query.ts:379-468`） |
| snip_compact | 先頭 3 + 末尾 47 を保持 | CC はメインスレッドのみ有効；実装はオープンソースリポジトリにない（`HISTORY_SNIP` feature gate）、インターフェースは確認可能：`snipCompactIfNeeded(messages)` → `{ messages, tokensFreed, boundaryMessage? }`、`SnipTool` もモデルが能動的に呼び出し可能。教学版の 3/47 は簡略パラメータ |
| micro_compact | テキストプレースホルダで置換 | 2 つのパス：time-based は直接内容をクリア、cached は API の `cache_edits` を使用（legacy パスは削除済み） |
| micro_compact ホワイトリスト | 位置による（直近 3 件） | time-based は時間閾値でトリガー、cached はカウントでトリガー（`microCompact.ts`） |
| tool_result_budget | 200KB 文字 | 200,000 文字（`toolLimits.ts:49`） |
| compact_history 閾値 | 文字数で推定 | 精密な token 数：`contextWindow - maxOutputTokens - 13_000` |
| 要約の要求 | 5 種類の情報 | 9 つのセクション + `<analysis>`/`<summary>` デュアルタグ |
| 圧縮プロンプト | シンプルなプロンプト | 先頭と末尾に二重の安全ガードでツール呼び出しを禁止 |
| PTL retry | あり（簡略版） | `truncateHeadForPTLRetry()` がメッセージグループ単位でロールバック（`compact.ts:243-290`） |
| 圧縮後のリカバリ | なし（教学版は要約のみ保持） | 直近のファイル、計画、agent/skill/tool などの自動再付加 |
| サーキットブレーカー | 3 回 | 3 回（`autoCompact.ts:70`） |
| reactive リトライ | 1 回 | CC にはより精緻な段階別リトライがある |

### 実行順序の詳細

CC ソース `query.ts` での実際の順序：

1. `applyToolResultBudget`（L379）：まず大きな結果を処理し、完全な内容を退避
2. `snipCompact`（L403）：中間メッセージを切り捨て
3. `microcompact`（L414）：古い結果のプレースホルダ化
4. `contextCollapse`（L441）：独立したコンテキスト管理システム（教学版にはなし）
5. `autoCompact`（L454）：LLM 全量要約

教学版の budget → snip → micro の順序はこれと一致する。教学版には contextCollapse メカニズムがない。

### 完全な定数リファレンス

| 定数 | 値 | ソースファイル |
|------|-----|--------|
| `AUTOCOMPACT_BUFFER_TOKENS` | 13,000 | `autoCompact.ts:62` |
| `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | 3 | `autoCompact.ts:70` |
| `MAX_OUTPUT_TOKENS_FOR_SUMMARY` | 20,000 | `autoCompact.ts:30` |
| `POST_COMPACT_TOKEN_BUDGET` | 50,000 | `compact.ts:123` |
| `POST_COMPACT_MAX_FILES_TO_RESTORE` | 5 | `compact.ts:122` |
| `POST_COMPACT_MAX_TOKENS_PER_FILE` | 5,000 | `compact.ts:124` |
| 時間ベース micro_compact 間隔 | 60 分 | `timeBasedMCConfig.ts` |
| `MAX_COMPACT_STREAMING_RETRIES` | 2 | `compact.ts:131` |

### contextCollapse と sessionMemoryCompact

CC ソースコードには、この教学版では展開していない 2 つのメカニズムが存在する：

- **contextCollapse**：独立したコンテキスト管理システム。有効時には proactive autocompact を抑制し（`autoCompact.ts:215-222`）、collapse の commit/blocking フローがコンテキスト管理を引き継ぐ。ただし manual `/compact` と reactive fallback は独立パスのままで、contextCollapse の影響を受けない。
- **sessionMemoryCompact**：compact_history の前に、CC は既存の session memory（s09 で解説）を使った軽量要約を先に試みる。LLM を呼び出さない。このメカニズムは s09 を学んだ後に振り返るとより理解しやすい。

### 圧縮プロンプトの中身

CC の圧縮プロンプトには 2 つの厳格な要件がある：

1. **ツール呼び出しの絶対禁止**：冒頭が `CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.` で、末尾にも再度 REMINDER がある
2. **先に分析してから要約**：モデルはまず `<analysis>` タグで思考を整理し、その後 `<summary>` タグで正式な要約を出力する。analysis はフォーマット時に除去される

### 教学版の簡略化は意図的

- micro_compact でテキストプレースホルダを使用 → API 層の `cache_edits` 権限がないため
- token を文字数で推定 → 精密な tokenizer は教学の対象外
- 圧縮後のリカバリを省略 → 教学版は要約のみを保持し、ファイルの自動再付加を行わない
- 2 つの補助メカニズムを展開しない → 10% の細部に属する

コア設計思想、安価なものを先に高価なものを後に、は完全に保持されている。

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
