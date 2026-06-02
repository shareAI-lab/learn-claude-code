# s15: Workflow Orchestration (工作流编排)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > [ s15 ] s16 > s17 > s18 > s19`

> *"编排是代码,不是提示词"* -- 确定性的多 agent 管道。
>
> **Harness 层**: 工作流基元 -- harness 脚本控制 agent 流程,不是模型。

## 问题

s14 之后, Agent 可以用任何工具。但复杂任务需要多个 agent 按结构化模式协作。A 应该在 B 之前完成吗? C 和 D 应该并行吗? 模型可以决定,但不可靠 -- 每次调用做出不同的选择。

把流程写在代码里,而不是 prompt 里。

## 解决方案

```
parallel() -- 扇出 N 个独立 agent:
+-----------+     +-----------+     +-----------+
| Agent A   |     | Agent B   |     | Agent C   |   (同时运行)
| 审查      |     | 审查      |     | 审查      |
+-----+-----+     +-----+-----+     +-----+-----+
      |                |                |
      +----------------+----------------+
                       |
                 收集结果

pipeline() -- 每个数据项流经各阶段:
数据1: [阶段1 ---- 阶段2 ---- 阶段3]
数据2:    [阶段1 ---- 阶段2 ---- 阶段3]   (重叠)
```

## 工作原理

三个基元:

1. **`parallel(tasks)`** -- 扇出 N 个 agent 同时运行。

```python
def parallel(tasks):
    # tasks: [{"prompt": "...", "system": "...", "label": "..."}, ...]
    # 返回: [{"label": "...", "result": "..."}, ...]
    threads = []
    for task in tasks:
        t = threading.Thread(target=run_agent, args=(task,))
        threads.append(t); t.start()
    for t in threads:
        t.join()
    return results
```

2. **`pipeline(items, stages)`** -- 数据项流经顺序阶段。

```python
def pipeline(items, stages):
    results = []
    for item in items:
        prev = item
        for stage in stages:
            prev = run_agent(stage["prompt_fn"](item, prev), ...)
        results.append(prev)
    return results
```

3. **`phase(name)`** -- 上下文管理器,用于进度追踪。

```python
with phase("1. 并行审查"):
    reviews = parallel(tasks)
with phase("2. 综合"):
    report = run_agent(synthesis_prompt, ...)
```

## 试一试

```sh
cd learn-claude-code
python agents/s15_workflow_orchestration.py
```

试试这些:

1. `/review` -- 3 agent 并行代码审查 (bug, 风格, 安全)
2. `/demo` -- 完整工作流演示
3. `/pipeline <文本>` -- 对文本运行总结-提取管道
