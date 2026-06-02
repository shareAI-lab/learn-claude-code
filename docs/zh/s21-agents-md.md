# s21: AGENTS.md (项目指令继承链)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > [ s21 ] > s22 > s23`

> *"越靠近代码的规则越重要"* -- 目录树遍历 + 合并，最近文件优先。
>
> **Harness 层**: 指令继承 -- 从项目根到工作目录，自动聚合上下文规则。

## 问题

s20 控制 Agent 能做什么，但没告诉 Agent 应该怎么做。每个项目有自己的代码风格、测试约定、部署流程。把全部规则塞进系统提示太长，放在单个配置文件里又不够灵活 -- 子模块有自己的规则。

Agent 进入一个目录时，需要知道：项目级规则 + 子目录特定规则。最近的规则覆盖远处的规则。

## 解决方案

```
目录树中的 AGENTS.md 继承链：

/ (项目根)
|-- AGENTS.md          <-- 项目级指令 (基础)
|-- src/
|   |-- AGENTS.md      <-- 源码级指令 (覆盖/补充)
|   `-- components/
|       `-- AGENTS.md  <-- 组件级指令 (最优先)
|-- tests/
|   `-- AGENTS.md      <-- 测试级指令
`-- docs/

当 Agent 进入 src/components/ 时，合并顺序（从远到近）：

  1. /AGENTS.md            (项目级，最低优先级)
  2. /src/AGENTS.md        (源码级，覆盖项目级)
  3. /src/components/AGENTS.md  (组件级，最高优先级)

合并结果 = [项目级] + [源码级新增/覆盖] + [组件级新增/覆盖]

合并规则：
  - 同一名下的指令：最近文件优先
  - 不同的指令：全部保留，按距离排序
  - 格式：Markdown，每节用 ## 分隔

有效距离：
  - 向上最多查找 5 级目录
  - 遇到 .git 根或 project_root 停止
```

## 工作原理

1. **目录树遍历。** 从当前工作目录向上查找所有 AGENTS.md。

```python
def collect_agents_md(cwd: Path) -> list[Path]:
    agents_mds = []
    max_depth = 5
    current = Path(cwd).resolve()

    for _ in range(max_depth):
        candidate = current / "AGENTS.md"
        if candidate.is_file():
            agents_mds.append(candidate)
        # 停止条件
        if (current / ".git").is_dir() or (current / "package.json").is_file():
            break
        parent = current.parent
        if parent == current:  # 到达根目录
            break
        current = parent

    return agents_mds  # 从近到远
```

2. **解析单个 AGENTS.md。** 提取各节指令。

```python
def parse_agents_md(path: Path) -> dict[str, str]:
    content = path.read_text()
    sections = {}
    current_section = "_top"

    for line in content.split("\n"):
        if line.startswith("## "):
            current_section = line.replace("## ", "").strip()
            sections[current_section] = ""
        elif current_section in sections:
            sections[current_section] += line + "\n"

    return sections
```

3. **合并指令。** 最近文件的指令覆盖远处同名指令。

```python
def merge_directives(paths: list[Path]) -> dict[str, str]:
    # paths 从近到远，反转后从远到近合并
    merged = {}
    for path in reversed(paths):
        sections = parse_agents_md(path)
        for section, content in sections.items():
            if section not in merged:
                merged[section] = content
            else:
                # 最近优先：后写入的覆盖
                merged[section] = content
    return merged
```

4. **生成合并后的上下文。** 格式化为 Agent 可读的指令块。

```python
def build_context(cwd: Path) -> str:
    paths = collect_agents_md(cwd)
    if not paths:
        return ""

    merged = merge_directives(paths)
    source_files = [p.relative_to(cwd) for p in paths]

    lines = [f"<agents-md sources=\"{', '.join(source_files)}\">"]
    for section, content in merged.items():
        lines.append(f"## {section}\n{content}")
    lines.append("</agents-md>")
    return "\n".join(lines)
```

5. **注入系统提示。** 在 Agent 启动时自动附加。

```python
def get_system_prompt(base: str, cwd: Path) -> str:
    agents_context = build_context(cwd)
    if agents_context:
        return base + "\n\n" + agents_context
    return base
```

## 相对 s20 的变更

| 组件           | 之前 (s20)               | 之后 (s21)                        |
|----------------|--------------------------|-----------------------------------|
| 项目上下文     | 无                       | AGENTS.md 继承链                  |
| 指令来源       | 系统提示 (单一)           | 多层 AGENTS.md 合并               |
| 粒度           | 全局                     | 目录级，最近优先                   |
| 查找范围       | 无                       | 向上 5 级，遇项目根停止            |
| 合并策略       | 无                       | 同名覆盖 + 异名保留               |
| 系统提示       | 静态                     | 动态拼接，随工作目录变化           |

## 试一试

```sh
cd learn-claude-code
python agents/s21_agents_md.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Create AGENTS.md in root with coding conventions, then enter src/ and check context`
2. `Add AGENTS.md in src/ that overrides the testing convention`
3. `Navigate to a deep subdirectory and verify the merged instructions`
4. `Remove the root AGENTS.md and observe the context change`
5. `Test the 5-level depth limit by creating a deep directory chain`
