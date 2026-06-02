# s16: Model Routing / Tier Selection (模型路由/分层)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > [ s16 ] s17 > s18 > s19`

> *"大多数任务不需要最聪明的模型"* -- 按复杂度路由。
>
> **Harness 层**: 分层选择 -- harness 为每个任务选择合适的模型。

## 问题

s15 之后,工作流会启动大量 agent。如果每个都用 Opus,成本爆炸。如果每个都用 Haiku,质量下降。正确答案:按任务匹配合适的模型。

## 解决方案

```
用户: "Fix typo in README"
 |
 v
[分类器]  关键词: "typo" -> 简单
 |
 v
[Haiku]  (快速,便宜) -----------------> 结果

用户: "Refactor auth module"
 |
 v
[分类器]  关键词: "refactor" -> 复杂
 |
 v
[Opus]  (慢,贵,聪明) -----------------> 结果

分层对比:
+--------+--------+---------+---------+-----------+
| 分层   | 模型   | 速度    | 成本    | 用途      |
+--------+--------+---------+---------+-----------+
| Haiku  | 快     | ~1x     | ~1x     | 查询,简单 |
+--------+--------+---------+---------+-----------+
| Sonnet | 中等   | ~3x     | ~5x     | 标准工作   |
+--------+--------+---------+---------+-----------+
| Opus   | 聪明   | ~10x    | ~50x    | 复杂分析   |
+--------+--------+---------+---------+-----------+
```

## 工作原理

1. **分类任务。** 基于关键词的启发式 (生产环境使用学习分类器)。

```python
SIMPLE_KEYWORDS = {"typo", "rename", "format", "trivial"}
COMPLEX_KEYWORDS = {"architect", "refactor", "debug", "security audit"}

def classify_task(query):
    q = query.lower()
    for kw in SIMPLE_KEYWORDS:
        if kw in q: return "haiku"
    for kw in COMPLEX_KEYWORDS:
        if kw in q: return "opus"
    return "sonnet"  # 默认
```

2. **带回退的执行。** 便宜模型失败则升级。

```python
def run_with_fallback(prompt, tier):
    tiers = ["haiku", "sonnet", "opus"]
    for t in tiers[tiers.index(tier):]:
        result = run_agent(prompt, model=M[TIER[t]])
        if len(result) > 50:
            return result
```

## 试一试

```sh
cd learn-claude-code
python agents/s16_model_routing.py
```

试试这些:

1. `/classify "Fix the typo in line 42"` -- 查看分层路由
2. `/cost "Refactor the authentication module"` -- 查看成本估算
3. `/route "What files are in src/?"` -- 自动路由并执行
4. `/demo` -- 批量分类多个查询
