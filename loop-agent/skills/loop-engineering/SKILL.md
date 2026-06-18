---
name: loop-engineering
description: Loop Engineering Agent — 架构约定、编码模式、测试规范
---

# Loop Engineering Agent — 项目知识

## 架构概述

七阶段循环：Trigger → Discover → Allocate → Execute(Maker) → Verify(Checker) → Integrate → Persist

核心循环不变，所有机制围绕 `run_agent()` 的 while 循环层叠。

## 编码约定

- Python 3.10+，使用 `dataclass` 定义数据结构
- 路径操作用 `pathlib.Path`，不用 `os.path`
- 配置集中在 `config.py`，不硬编码
- 状态持久化到 `.loop-state.json`（原子写入）
- Mock 数据在 `mock_data/` 目录，JSON 格式

## 工具模式

```python
# 工具分发映射（s02 模式）
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
}

# 子代理使用 fresh messages[]（s06 模式）
messages = [{"role": "user", "content": task_description}]
```

## Maker-Checker 协议

- **Maker**: 拥有 bash/read/write/edit 工具，50 轮上限，在 worktree 中工作
- **Checker**: 只有 read/glob 工具，20 轮上限，输出 APPROVED/REJECTED
- 拒绝后：记录反馈到 `LoopState.history[].feedback`，下次重试时注入
- 3 次拒绝：标记 `needs_human_review`

## 测试模式

```bash
# 单元测试
pytest loop-agent/tests/test_state.py -v

# 集成测试（mock LLM）
pytest loop-agent/tests/test_orchestrator.py -v

# 全量测试
pytest loop-agent/tests/ -v
```

## PR 规范

- 标题格式: `Auto-fix: {task_title}`
- Body 包含: 触发源、任务描述、变更文件、验证状态
- 分支命名: `wt/{branch_name}`（worktree 隔离）
