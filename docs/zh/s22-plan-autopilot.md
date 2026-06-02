# s22: Plan & Autopilot (计划与自动驾驶)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > [ s22 ] > s23`

> *"先想清楚, 再做"* -- PLAN 模式写方案, 人审核后切换到 AUTOPILOT 执行。
>
> **Harness 层**: 双模式引擎 -- PLAN 规划 + AUTOPILOT 执行，人在回路审核。

## 问题

s21 让 Agent 能读取项目规则，但 Agent 仍然缺少一个关键能力：区分"规划"和"执行"。面对复杂任务（重构认证模块、迁移数据库），Agent 直接开始改代码 -- 改错了回滚代价高。

用户需要：Agent 先写方案，人审核确认后，Agent 再按计划执行。两种模式切换要平滑，计划是执行的约束。

## 解决方案

```
双模式状态机：

  +------+     用户提交任务      +-------+
  | IDLE | --------------------> | PLAN  |
  +------+                       +---+---+
                                    |
                                    | 生成计划 (.omc/plans/<name>.md)
                                    v
                              +----------+
                              | REVIEW   |  <-- 人在回路：审核/修改计划
                              +----+-----+
                                   |
                                   | 用户批准
                                   v
                            +-----------+
                            | AUTOPILOT |  <-- 按计划逐步执行
                            +-----+-----+
                                  |
                         +--------+---------+
                         |                  |
                    执行完成            遇到阻塞
                         |                  |
                         v                  v
                    +--------+        +----------+
                    | DONE   |        | WAITING  | <--- 等待用户解决
                    +--------+        +----+-----+
                                   |
                                   | 用户解除阻塞
                                   v
                            +-----------+
                            | AUTOPILOT |
                            +-----------+

模式职责：
  PLAN      - 只读分析 + 写计划文件，不改生产代码
  REVIEW    - 暂停等待，用户检查计划
  AUTOPILOT - 按计划执行，每步验证
  WAITING   - 阻塞时暂停，报告状态

计划文件格式 (.omc/plans/<name>.md)：
  # Plan: <task name>
  ## Goals
  - [ ] Goal 1
  - [ ] Goal 2
  ## Steps
  1. Step 1 -> verify: <check>
  2. Step 2 -> verify: <check>
  ## Risks
  - Risk 1 -> mitigation
```

## 工作原理

1. **PLAN 模式。** 分析任务，生成计划文件。

```python
def plan_mode(task: str) -> str:
    plan_name = slugify(task)
    plan_path = PLANS_DIR / f"{plan_name}.md"

    response = client.messages.create(
        model=MODEL,
        system=PLAN_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Create a plan: {task}"}],
        tools=[READ_TOOL, GREP_TOOL, GLOB_TOOL],  # 只读工具
        max_tokens=4000,
    )

    # 计划写入 .omc/plans/，不碰生产代码
    plan_path.write_text(response.content[0].text)
    return str(plan_path)
```

2. **REVIEW 模式。** 暂停，等待用户审核。

```python
def review_mode(plan_path: str) -> bool:
    print(f"Plan ready: {plan_path}")
    print("Review the plan, then:")
    print("  /approve  - start execution")
    print("  /revise <feedback>  - revise the plan")
    print("  /cancel  - discard")

    command = wait_for_input(timeout=300)
    if command.startswith("/approve"):
        return True
    if command.startswith("/revise"):
        feedback = command[len("/revise"):].strip()
        return revise_plan(plan_path, feedback)
    return False
```

3. **AUTOPILOT 模式。** 按计划逐步执行，每步验证。

```python
def autopilot_mode(plan_path: str):
    plan = parse_plan(plan_path)
    state = {"step": 0, "completed": [], "errors": []}

    while state["step"] < len(plan["steps"]):
        step = plan["steps"][state["step"]]
        print(f"Step {state['step'] + 1}/{len(plan['steps'])}: {step['description']}")

        result = execute_step(step, state)

        if result["success"]:
            mark_complete(plan_path, state["step"])
            state["completed"].append(state["step"])
        elif result.get("blocked"):
            return wait_for_user(result["block_reason"])
        else:
            state["errors"].append(result["error"])
            if len(state["errors"]) > 3:
                return escalate(plan_path, state)

        state["step"] += 1

    return {"status": "done", "completed": len(state["completed"])}
```

4. **每步验证。** 执行后运行验证检查。

```python
def execute_step(step: dict, state: dict) -> dict:
    # 执行步骤
    response = client.messages.create(
        model=MODEL,
        system=AUTOPILOT_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Execute: {step['description']}"},
            {"role": "user", "content": f"Verify with: {step['verify']}"},
        ],
        tools=ALL_TOOLS,
        max_tokens=8000,
    )

    # 运行验证
    verify_result = run_verification(step["verify"])
    if not verify_result["passed"]:
        # 自动重试一次
        response = retry_step(step, state, verify_result)
        verify_result = run_verification(step["verify"])

    return {
        "success": verify_result["passed"],
        "error": verify_result.get("message"),
        "blocked": verify_result.get("requires_human"),
    }
```

5. **状态持久化。** 保存执行状态到磁盘。

```python
def save_state(plan_path: str, state: dict):
    state_path = PLANS_DIR / f"{plan_path.stem}.state.json"
    state_path.write_text(json.dumps({
        **state,
        "updated_at": datetime.now().isoformat(),
    }, indent=2))
```

## 相对 s21 的变更

| 组件           | 之前 (s21)               | 之后 (s22)                        |
|----------------|--------------------------|-----------------------------------|
| 执行模式       | 单模式 (直接执行)         | 双模式 (PLAN + AUTOPILOT)         |
| 任务流程       | 收到即执行               | 先规划 -> 审核 -> 再执行          |
| 计划文件       | 无                       | .omc/plans/<name>.md             |
| 人在回路       | 审批策略 (命令级)         | 计划审核 (任务级)                  |
| 进度追踪       | TodoWrite                | 计划步骤 + 状态文件                |
| 错误处理       | 失败即停                 | 自动重试 + 3次后升级               |
| 恢复能力       | 无                       | 状态持久化，中断后可继续            |

## 试一试

```sh
cd learn-claude-code
python agents/s22_plan_autopilot.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Plan: Refactor the authentication module to use OAuth2` -- 进入 PLAN 模式
2. `/approve` -- 审核通过后切换到 AUTOPILOT
3. `/revise Add error handling for token expiration` -- 修改计划后重新执行
4. `Watch autopilot execute step by step and verify each step`
5. `Interrupt during execution, then check the saved state and resume`
