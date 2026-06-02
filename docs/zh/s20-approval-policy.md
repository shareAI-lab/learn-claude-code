# s20: Approval Policy (审批策略)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > [ s20 ] > s21 > s22 > s23`

> *"不是所有操作都一样危险"* -- 按操作类型自动选择审批级别。
>
> **Harness 层**: 审批策略 -- 模型动作前的安全阀，可配置粒度。

## 问题

s19 之后，Agent 能跨会话持久化记忆。但自主性越强，风险越大。Agent 删了重要文件、改了生产配置、执行了危险命令 -- 用户希望在危险操作发生前被问到，而不是事后才发现。

一刀切的方案也不行：每次 `ls` 都要确认太烦，每次 `rm -rf` 都不确认太险。需要根据操作类型自动匹配审批级别。

## 解决方案

```
四种审批策略：

  full-auto    - 全自动，无需确认（阅读类、只读操作）
  auto-edit    - 自动编辑代码，但需事后回滚能力（写文件、改配置）
  on-request   - 执行前询问用户（运行测试、构建、安装依赖）
  never        - 永远不执行，返回错误（删除文件、git force push）

审批决策流程：

  模型发出工具调用
        |
        v
  +------------------+
  |  审批检查        |
  +--------+---------+
           |
           v
  +------------------+     查找命令对应的策略
  |  策略查找        | -----> settings.json -> approval_policy
  +--------+---------+             (command -> policy mapping)
           |
     +-----+-----+
     |           |
     v           v
  +-------+   +-------+
  |  批准  |   |  拒绝  |   (never 策略直接拒绝)
  +---+---+   +-------+
      |
      | on-request 策略
      v
  +-------+
  |  询问  | -----> 用户确认/拒绝
  +-------+

策略优先级：never > on-request > auto-edit > full-auto
```

## 工作原理

1. **策略配置。** 在 settings.json 中定义命令到策略的映射。

```python
APPROVAL_POLICY = {
    "full-auto": [
        "ls", "cat", "head", "tail", "grep", "find",
        "git status", "git diff", "git log",
    ],
    "auto-edit": [
        "write", "edit", "sed -i",
    ],
    "on-request": [
        "npm install", "pip install",
        "npm run build", "npm test",
        "pytest", "cargo build",
    ],
    "never": [
        "rm -rf", "git push --force",
        "git reset --hard", "drop database",
    ],
}
```

2. **策略查找。** 根据命令前缀匹配策略。

```python
def lookup_policy(command: str) -> str:
    for policy, patterns in reversed(APPROVAL_POLICY.items()):
        for pattern in patterns:
            if command.startswith(pattern):
                return policy
    return "on-request"  # 默认：不确定时询问
```

3. **审批检查。** 根据策略决定是否拦截。

```python
def check_approval(command: str) -> str:
    policy = lookup_policy(command)

    if policy == "full-auto":
        return "approved"
    if policy == "auto-edit":
        return "approved"  # 自动通过，记录日志
    if policy == "never":
        return f"blocked: {command} is prohibited by approval policy"

    # on-request: 等待用户确认
    response = wait_for_user_approval(command, timeout=120)
    return "approved" if response else "denied by user"
```

4. **集成到工具执行。** 在执行前插入审批检查。

```python
def execute_tool(name: str, args: dict) -> str:
    if name == "bash":
        command = args["command"]
        result = check_approval(command)
        if result != "approved":
            return result
        # 继续执行
        return subprocess.run(command, shell=True,
                              capture_output=True, text=True)
    return tool_dispatch[name](args)
```

5. **审批日志。** 记录每次审批决策，用于审计。

```python
approval_log.append({
    "command": command,
    "policy": policy,
    "decision": result,
    "timestamp": time.time(),
})
```

## 相对 s19 的变更

| 组件           | 之前 (s19)           | 之后 (s20)                      |
|----------------|----------------------|---------------------------------|
| 安全机制       | 无                   | 四级审批策略                     |
| 命令执行       | 直接执行             | 先审批后执行                     |
| 配置           | 记忆文件             | settings.json 策略映射           |
| 用户交互       | 无                   | on-request 时暂停等待确认         |
| 审计           | 无                   | 审批决策日志                      |
| 默认行为       | 全部允许             | 不确定时默认询问                  |

## 试一试

```sh
cd learn-claude-code
python agents/s20_approval_policy.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Run "ls -la" - should execute without asking (full-auto)`
2. `Try "rm -rf /tmp/test" - should be blocked (never policy)`
3. `Run "npm install" - should pause and ask for confirmation (on-request)`
4. `Set approval policy to full-auto for all commands, then run anything`
5. `Check the approval log to see what was approved/blocked`
