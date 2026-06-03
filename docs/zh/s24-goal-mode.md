# s24: 目标模式

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > s22 > s23 > [ s24 ]`

> *"给 Agent 一颗北极星，而不只是一份待办清单"* —— 跨会话持久化的目标。
>
> **Harness 层**: 目标追踪 —— harness 维护一个带有状态、进度和自检能力的持久化目标。

## 问题

到了 s23，Agent 在沙箱内安全运行。但还有一个更深层次的问题：每次会话都是从头开始。Agent 忘记了上次在做什么，用户每次回来都得重新解释目标。一个持续数周的重构任务，每次会话结束就归零。

即使在同一次会话中，Agent 也会偏离方向。任务进行到一半，它去追支线 —— 修复一个 lint 警告而不是交付功能。没有北极星把它拉回来。

用户需要的是：一个跨会话持久的目标，跟踪进度，让 Agent 能自我评估是在推进目标还是在跑偏。

## 解决方案

```
目标生命周期：

  +---------+  启动     +---------+  工作中    +---------+
  | CREATED | --------> | RUNNING | ----------> | PAUSED  |
  |         |            |         |              |         |
  | - 设置   |            | - 工具   |  /goal pause | - 保存  |
  |   目标   |            |   调用   |              |   状态  |
  | - 保存   |            |   推进   |  /goal resum<-| 用户  |
  |   标准   |            |   目标   |  e          |  中断  |
  +---------+            +----+----+              +---------+
                               |                      ^
                         完成  |                       |
                         +------v------+              |
                         | COMPLETED  |<--------------+
                         |            |  /goal resume 失败
                         | - 摘要     |              |
                         | - 归档     |              v
                         +------------+          +---------+
                                          +----->| FAILED  |
                                          |      |         |
                                  max_retries| - 错误    |
                                          |   - 最后   |
                                          |   - 日志   |
                                          +---------+

目标状态文件 (.omc/state/goal.json):
  {
    "goal": "重构认证模块以使用 OAuth2",
    "state": "running",
    "criteria": [
      {"id": 1, "desc": "添加 OAuth2 提供者", "done": true},
      {"id": 2, "desc": "迁移登录流程", "done": true},
      {"id": 3, "desc": "移除遗留 Token", "done": false},
      {"id": 4, "desc": "添加集成测试", "done": false}
    ],
    "progress": "50%",
    "iteration": 14,
    "last_check": "2025-03-15T10:30:00",
    "created_at": "2025-03-10T09:00:00"
  }

自检循环（每 N 次工具调用或 /goal check 时触发）:
  模型生成工具调用
          |
          v
  +------------------------+
  |  是否存在活动的         |
  |  目标？                |
  +---------+--------------+
            |
       +----+----+
       |         |
      是         否 -> 正常执行
       |
       v
  +------------------------+
  |  self_evaluate()       |
  |  "这个工具调用是否      |
  |   在推进目标？"         |
  +---------+--------------+
            |
       +----+----+
       |    |     |
      是   可能   否
       |    |     |
       v    v     v
    执行  谨慎执  警告："这可能
          行      不会推进目标。
                是否继续？"
                      |
                      v
               +------------+
               | 记录偏离    |
               | 更新进度    |
               +------------+
```

## 工作原理

1. **目标创建。** 用户设置一个带有验收标准的持久化目标。

```python
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import json

@dataclass
class Goal:
    goal: str
    criteria: list[dict] = field(default_factory=list)
    state: str = "created"
    progress: str = "0%"
    iteration: int = 0
    created_at: str = ""
    last_check: str = ""
    error: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
```

2. **持久化。** 目标存储在 `.omc/state/goal.json` 中，跨会话重启依然保留。

```python
GOAL_PATH = Path(".omc/state/goal.json")

def save_goal(self):
    GOAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOAL_PATH.write_text(json.dumps(asdict(self), indent=2))

def load_goal() -> Goal | None:
    if not GOAL_PATH.exists():
        return None
    data = json.loads(GOAL_PATH.read_text())
    return Goal(**data)
```

3. **状态转换。** 目标通过一个定义良好的状态机流转。

```python
VALID_TRANSITIONS = {
    "created":   ["running", "failed"],
    "running":   ["paused", "completed", "failed"],
    "paused":    ["running", "failed"],
    "completed": [],
    "failed":    ["created"],
}

def transition(self, new_state: str) -> str:
    if new_state not in VALID_TRANSITIONS.get(self.state, []):
        return f"Cannot go {self.state} -> {new_state}"
    old = self.state
    self.state = new_state
    self.last_check = datetime.now().isoformat()
    self.save_goal()
    return f"Goal: {old} -> {new_state}"
```

4. **自检循环。** 每 N 次工具调用（或按需），Agent 检查是否在正轨上。

```python
def self_evaluate(self, tool_call: dict, context: str) -> dict:
    prompt = f"""目标: {self.goal}
待完成标准: {[c['desc'] for c in self.criteria if not c.get('done')]}
最近工具调用: {json.dumps(tool_call)}
上下文: {context[-500:]}

评估对齐度: aligned（一致）/ drifting（偏离）/ off_track（脱轨）
简要原因（一行）。"""

    response = client.messages.create(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    alignment = extract_alignment(response)
    self.iteration += 1
    self.last_check = datetime.now().isoformat()
    self.save_goal()

    return {
        "alignment": alignment,
        "iteration": self.iteration,
        "progress": self.calculate_progress(),
    }

def calculate_progress(self) -> str:
    total = len(self.criteria)
    if total == 0:
        return "0%"
    done = sum(1 for c in self.criteria if c.get("done"))
    return f"{int(done / total * 100)}%"
```

5. **进度追踪。** 随着 Agent 推进，标准项被逐一标记完成。

```python
def mark_complete(self, criteria_id: int) -> str:
    for c in self.criteria:
        if c["id"] == criteria_id:
            c["done"] = True
            break
    self.progress = self.calculate_progress()
    self.save_goal()

    if all(c.get("done") for c in self.criteria):
        self.transition("completed")
        return f"所有标准已满足。目标完成！"
    return f"进度: {self.progress}"
```

6. **偏离检测与恢复。** 当 Agent 跑偏时，弹出警告。

```python
CHECK_INTERVAL = 10  # 每 10 次工具调用评估一次

def on_tool_call(self, tool_call: dict) -> str | None:
    if self.state != "running":
        return None

    self.iteration += 1
    if self.iteration % CHECK_INTERVAL == 0:
        result = self.self_evaluate(tool_call, self.recent_context)

        if result["alignment"] == "off_track":
            return (
                f"检测到偏离（检查 #{self.iteration}）:\n"
                f"进度: {result['progress']}\n"
                f"目标: {self.goal}\n"
                f"暂停并重新评估？"
            )
        elif result["alignment"] == "drifting":
            return f"注意：可能正在偏离目标。进度: {result['progress']}"
    return None
```

## 相对 s23 的变更

| 组件         | 之前 (s23)                  | 之后 (s24)                            |
|-------------|-----------------------------|---------------------------------------|
| 目标         | 会话内，隐式                 | 持久化目标，显式标准                   |
| 状态         | 仅沙箱模式                   | 目标状态机（5 个状态）                 |
| 持久化       | 沙箱日志                     | 目标保存到 .omc/state/goal.json       |
| 自检         | 无                           | 每 N 次工具调用自动自检                |
| 进度         | 未追踪                       | 基于标准的百分比进度                   |
| 偏离处理     | 无                           | 对齐度评分 + 警告                      |
| 恢复         | 重启后用户重新解释           | 加载目标状态，自动恢复                 |
| 完成         | 用户决定                     | 所有标准满足时自动完成                 |

## 试一试

```sh
cd learn-claude-code
python agents/s24_goal_mode.py
```

试试以下操作：

1. `/goal set Refactor the auth module to use OAuth2` -- 创建带标准的目标
2. `/goal status` -- 查看当前目标状态、进度和标准
3. 观察 Agent 工作；每 10 次工具调用它会自动自检对齐度
4. `/goal check` -- 强制立即自检
5. `/goal pause` -- 暂停目标，保存状态，停止工具执行
6. 重启会话 -- 目标仍然存在
7. `/goal resume` -- 从上次中断处继续
8. `/goal mark 3` -- 标记标准 3 为完成，观察进度更新
9. 完成所有标准 -- 目标自动流转至 COMPLETED 状态
10. `/goal summary` -- 查看完整生命周期：创建、检查、状态转换、完成
