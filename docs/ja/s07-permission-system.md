# s07: Permission System

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > [ s07 ] > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *model は「こうしたい」と提案できます。けれど本当に実行する前には、必ず安全 gate を通さなければなりません。*

## この章の核心目標

`s06` まで来ると agent はすでに、

- file を読む
- file を書く
- command を実行する
- plan を持つ
- context を compact する

ことができます。

能力が増えるほど、当然危険も増えます。

- 間違った file を書き換える
- 危険な shell command を実行する
- user がまだ許可していない操作に踏み込む

だからここから先は、

**「model の意図」がそのまま「実行」へ落ちる**

構造をやめなければなりません。

この章で入れるのは、

**tool request を実行前に判定する permission pipeline**

です。

## 併読すると楽になる資料

- model の提案と system の実実行が混ざるなら [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- なぜ tool request を直接 handler に落としてはいけないか不安なら [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)
- `PermissionRule`、`PermissionDecision`、`tool_result` が混ざるなら [`data-structures.md`](./data-structures.md)

## 先に言葉をそろえる

### permission system とは何か

permission system は真偽値 1 個ではありません。

むしろ次の 3 問に順番に答える pipeline です。

1. これは即拒否すべきか
2. 自動で許可してよいか
3. 残りは user に確認すべきか

### permission mode とは何か

mode は、その session 全体の安全姿勢です。

たとえば、

- 慎重に進める
- 読み取りだけ許す
- 安全そうなものは自動通過させる

といった大きな方針です。

### rule とは何か

rule は、

> ある tool request に当たったらどう振る舞うか

を表す小さな条項です。

最小形なら次のような record で表せます。

```python
{
    "tool": "bash",
    "content": "sudo *",
    "behavior": "deny",
}
```

意味は、

- `bash` に対して
- command 内容が `sudo *` に当たれば
- 拒否する

です。

## 最小 permission system の形

0 から手で作るなら、最小で正しい pipeline は 4 段で十分です。

```text
tool_call
  |
  v
1. deny rules
  -> 危険なら即拒否
  |
  v
2. mode check
  -> 現在 mode に照らして判定
  |
  v
3. allow rules
  -> 安全で明確なら自動許可
  |
  v
4. ask user
  -> 残りは確認に回す
```

この 4 段で teaching repo の主線としては十分に強いです。

## なぜ順番がこの形なのか

### 1. deny を先に見る理由

ある種の request は mode に関係なく危険です。

たとえば、

- 明白に危険な shell command
- workspace の外へ逃げる path

などです。

こうしたものは「いま auto mode だから」などの理由で通すべきではありません。

### 2. mode を次に見る理由

mode はその session の大きな姿勢だからです。

たとえば `plan` mode なら、

> まだ review / analysis 段階なので write 系をまとめて抑える

という全体方針を早い段で効かせたいわけです。

### 3. allow を後に見る理由

deny と mode を抜けたあとで、

> これは何度も出てくる安全な操作だから自動で通してよい

というものを allow します。

たとえば、

- `read_file`
- code search
- `git status`

などです。

### 4. ask を最後に置く理由

前段で明確に決められなかった灰色領域だけを user に回すためです。

これで、

- 危険なものは system が先に止める
- 明らかに安全なものは system が先に通す
- 本当に曖昧なものだけ user が判断する

という自然な構図になります。

## 最初に実装すると良い 3 つの mode

最初から mode を増やしすぎる必要はありません。

まずは次の 3 つで十分です。

| mode | 意味 | 向いている場面 |
|---|---|---|
| `default` | rule に当たらないものは user に確認 | 普通の対話 |
| `plan` | write を止め、read 中心で進める | planning / review / analysis |
| `auto` | 明らかに安全な read は自動許可 | 高速探索 |

この 3 つだけでも、

- 慎重さ
- 計画モード
- 流暢さ

のバランスを十分教えられます。

## この章の核になるデータ構造

### 1. PermissionRule

```python
PermissionRule = {
    "tool": str,
    "behavior": "allow" | "deny" | "ask",
    "path": str | None,
    "content": str | None,
}
```

必ずしも最初から `path` と `content` の両方を使う必要はありません。

でも少なくとも rule は次を表現できる必要があります。

- どの tool に対する rule か
- 当たったらどう振る舞うか

### 2. Permission Mode

```python
mode = "default" | "plan" | "auto"
```

これは個々の rule ではなく session 全体の posture です。

### 3. PermissionDecision

```python
{
    "behavior": "allow" | "deny" | "ask",
    "reason": "why this decision was made",
}
```

ここで `reason` を持つのが大切です。

なぜなら permission system は「通した / 止めた」だけではなく、

**なぜそうなったかを説明できるべき**

だからです。

## 最小実装を段階で追う

### 第 1 段階: 判定関数を書く

```python
def check_permission(tool_name: str, tool_input: dict) -> dict:
    # 1. deny rules
    for rule in deny_rules:
        if matches(rule, tool_name, tool_input):
            return {"behavior": "deny", "reason": "matched deny rule"}

    # 2. mode check
    if mode == "plan" and tool_name in WRITE_TOOLS:
        return {"behavior": "deny", "reason": "plan mode blocks writes"}
    if mode == "auto" and tool_name in READ_ONLY_TOOLS:
        return {"behavior": "allow", "reason": "auto mode allows reads"}

    # 3. allow rules
    for rule in allow_rules:
        if matches(rule, tool_name, tool_input):
            return {"behavior": "allow", "reason": "matched allow rule"}

    # 4. fallback
    return {"behavior": "ask", "reason": "needs confirmation"}
```

重要なのは code の華やかさではなく、

**先に分類し、その後で分岐する**

という構造です。

### 第 2 段階: tool 実行直前に接ぐ

permission は tool request が来たあと、handler を呼ぶ前に入ります。

```python
decision = perms.check(tool_name, tool_input)

if decision["behavior"] == "deny":
    return f"Permission denied: {decision['reason']}"

if decision["behavior"] == "ask":
    ok = ask_user(...)
    if not ok:
        return "Permission denied by user"

return handler(**tool_input)
```

これで初めて、

**tool request と real execution の間に control gate**

が立ちます。

## `bash` を特別に気にする理由

すべての tool の中で `bash` は特別に危険です。

なぜなら、

- `read_file` は読むだけ
- `write_file` は書くだけ
- でも `bash` は理論上ほとんど何でもできる

からです。

したがって `bash` をただの文字列入力として見るのは危険です。

成熟した system では、`bash` を小さな executable language として扱います。

教材版でも最低限、次のような危険要素は先に弾く方がよいです。

- `sudo`
- `rm -rf`
- 危険な redirection
- suspicious command substitution
- 明白な shell metacharacter chaining

核心は 1 文です。

**bash は普通の text ではなく、可実行 action の記述**

です。

## 初学者が混ぜやすいポイント

### 1. permission を yes/no の 2 値で考える

実際には `deny / allow / ask` の 3 分岐以上が必要です。

### 2. mode を rule の代わりにしようとする

mode は全体 posture、rule は個別条項です。役割が違います。

### 3. `bash` を普通の string と同じ感覚で通す

execution power が桁違いです。

### 4. deny / allow より先に user へ全部投げる

それでは system 側の safety design を学べません。

### 5. decision に reason を残さない

あとで「なぜ止まったか」が説明できなくなります。

## 拒否トラッキングの意味

教材コードでは、連続拒否を数える簡単な circuit breaker を持たせるのも有効です。

なぜなら agent が同じ危険 request を何度も繰り返すとき、

- mode が合っていない
- plan を作り直すべき
- 別 route を選ぶべき

という合図になるからです。

これは高度な observability ではなく、

**permission failure も agent の progress 状態の一部である**

と教えるための最小観測です。

## この章を読み終えたら何が言えるべきか

1. model の意図は handler へ直結させず、permission pipeline を通すべき
2. `default / plan / auto` の 3 mode だけでも十分に teaching mainline が作れる
3. `bash` は普通の text 入力ではなく、高い実行力を持つ tool なので特別に警戒すべき

## 一文で覚える

**Permission System とは、model の意図をそのまま実行に落とさず、deny / mode / allow / ask の pipeline で安全に変換する層です。**
