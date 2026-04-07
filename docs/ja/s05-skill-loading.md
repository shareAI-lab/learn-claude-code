# s05: Skills

`s01 > s02 > s03 > s04 > [ s05 ] > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *"必要な知識を、必要な時に読み込む"* -- system prompt ではなく tool_result で注入。
>
> **Harness 層**: オンデマンド知識 -- モデルが求めた時だけ渡すドメイン専門性。

## 問題

エージェントにドメイン固有のワークフローを遵守させたい: gitの規約、テストパターン、コードレビューチェックリスト。すべてをシステムプロンプトに入れると、使われないスキルにトークンを浪費する。10スキル x 2000トークン = 20,000トークン、ほとんどが任意のタスクに無関係だ。

## 解決策

```
System prompt (Layer 1 -- always present):
+--------------------------------------+
| You are a coding agent.              |
| Skills available:                    |
|   - git: Git workflow helpers        |  ~100 tokens/skill
|   - test: Testing best practices     |
+--------------------------------------+

When model calls load_skill("git"):
+--------------------------------------+
| tool_result (Layer 2 -- on demand):  |
| <skill name="git">                   |
|   Full git workflow instructions...  |  ~2000 tokens
|   Step 1: ...                        |
| </skill>                             |
+--------------------------------------+
```

第1層: スキル*名*をシステムプロンプトに(低コスト)。第2層: スキル*本体*をtool_resultに(オンデマンド)。

## 仕組み

1. 各スキルは `SKILL.md` ファイルを含むディレクトリとして配置される。

```
skills/
  pdf/
    SKILL.md       # ---\n name: pdf\n description: Process PDF files\n ---\n ...
  code-review/
    SKILL.md       # ---\n name: code-review\n description: Review code\n ---\n ...
```

2. SkillLoaderが `SKILL.md` を再帰的に探索し、ディレクトリ名をスキル識別子として使用する。

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        for f in sorted(skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def get_descriptions(self) -> str:
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'."
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"
```

3. 第1層はシステムプロンプトに配置。第2層は通常のツールハンドラ。

```python
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Skills available:
{SKILL_LOADER.get_descriptions()}"""

TOOL_HANDLERS = {
    # ...base tools...
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}
```

モデルはどのスキルが存在するかを知り(低コスト)、関連する時にだけ読み込む(高コスト)。

## s04からの変更点

| Component      | Before (s04)     | After (s05)                |
|----------------|------------------|----------------------------|
| Tools          | 5 (base + task)  | 5 (base + load_skill)      |
| System prompt  | Static string    | + skill descriptions       |
| Knowledge      | None             | skills/\*/SKILL.md files   |
| Injection      | None             | Two-layer (system + result)|

## 試してみる

```sh
cd learn-claude-code
python agents/s05_skill_loading.py
```

1. `What skills are available?`
2. `Load the agent-builder skill and follow its instructions`
3. `I need to do a code review -- load the relevant skill first`
4. `Build an MCP server using the mcp-builder skill`

## 高完成度システムではどう広がるか

この章の核心は 2 層モデルです。  
まず軽い一覧で「何があるか」を知らせ、必要になったときだけ本文を深く読み込む。これはそのまま有効です。

より完成度の高いシステムでは、その周りに次のような広がりが出ます。

| 観点 | 教材版 | 高完成度システム |
|------|--------|------------------|
| 発見レイヤー | プロンプト内に名前一覧 | 予算付きの専用インベントリやリマインダ面 |
| 読み込み | `load_skill` が本文を返す | 同じ文脈へ注入、別ワーカーで実行、補助コンテキストとして添付など |
| ソース | `skills/` ディレクトリのみ | user、project、bundled、plugin、外部ソースなど |
| 適用範囲 | 常に見える | タスク種別、触ったファイル、明示指示に応じて有効化 |
| 引数 | なし | スキルへパラメータやテンプレート値を渡せる |
| ライフサイクル | 一度読むだけ | compact や再開後に復元されることがある |
| ガードレール | なし | スキルごとの許可範囲や行動制約を持てる |

教材としては、2 層モデルだけで十分です。  
ここで学ぶべき本質は：

**専門知識は最初から全部抱え込まず、必要な時だけ深く読み込む**  
という設計です。
