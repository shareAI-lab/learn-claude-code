# s23: Sandbox Modes (沙箱模式)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > s22 > [ s23 ]`

> *"给 Agent 一个安全andbox"* -- 根据命令风险自动选择沙箱级别。
>
> **Harness 层**: 沙箱隔离 -- 命令分类 + 风险分级，把危险操作关在笼子里。

## 问题

s22 的 PLAN/AUTOPILOT 解决了"做什么"的问题，s20 的审批策略控制了"能否做"。但还有一个问题：在哪里做？Agent 直接在用户机器上跑 `pip install` 或 `chmod 777` -- 即使审批通过了，副作用也可能不可逆。

需要按命令风险分级：安全命令直接在本地跑，危险命令放进沙箱。沙箱提供隔离的执行环境，失败不影响宿主机。

## 解决方案

```
四种沙箱模式：

  none       - 无隔离，直接在宿主机执行（只读命令）
  restricted - 限制网络 + 限制写入目录（普通写操作）
  container  - Docker 容器隔离（安装依赖、修改系统配置）
  virtual    - 完整虚拟机隔离（高风险操作、网络请求）

命令分类与沙箱决策流：

  命令进入
    |
    v
  +------------------+
  |  命令分类        |
  +--------+---------+
           |
    +------+------+-----+-----+
    v      v      v       v
  只读    写文件  安装    网络
  操作    操作    操作    操作
    |      |      |       |
    v      v      v       v
  none  restricted container virtual
    |      |      |       |
    +------+------+-------+
           |
           v
  +------------------+
  |  沙箱执行器       |
  +--------+---------+
           |
     +-----+-----+
     |           |
     v           v
  +-------+   +-------+
  | 直接执行 | | 沙箱执行 |
  +-------+   +---+---+
                 |
          +------+------+
          |      |      |
          v      v      v
     restricted container virtual
          |
     限制网络 + 限制写入范围

沙箱配置：

  restricted:
    writable_dirs: [cwd, /tmp]
    network: false
    env: 继承宿主机

  container:
    image: python:3.12-slim
    volume: [cwd:/workspace]
    network: false (默认)
    working_dir: /workspace

  virtual:
    image: ubuntu-24.04-mini
    network: isolated (无出站)
    forwarded_ports: [指定端口]
```

## 工作原理

1. **命令分类器。** 根据命令特征判断风险等级。

```python
COMMAND_CATEGORIES = {
    "read": {
        "patterns": ["ls", "cat", "head", "tail", "grep", "find", "stat",
                      "git status", "git diff", "git log", "pwd", "whoami"],
        "sandbox": "none",
    },
    "write": {
        "patterns": ["echo", "tee", "touch", "mkdir", "cp", "mv",
                      "sed -i", "git add", "git commit"],
        "sandbox": "restricted",
    },
    "install": {
        "patterns": ["pip install", "npm install", "apt-get", "yum",
                      "cargo install", "go install", "brew install"],
        "sandbox": "container",
    },
    "network": {
        "patterns": ["curl", "wget", "httpie", "scp", "rsync",
                      "ssh", "git push", "git pull"],
        "sandbox": "virtual",
    },
}
```

2. **风险查找。** 匹配命令到对应沙箱模式。

```python
def classify_command(command: str) -> str:
    for category, config in COMMAND_CATEGORIES.items():
        for pattern in config["patterns"]:
            if pattern in command:
                return config["sandbox"]
    return "restricted"  # 默认：不确定时限制
```

3. **沙箱执行器。** 根据沙箱模式选择执行方式。

```python
def execute_in_sandbox(command: str, sandbox: str, cwd: str) -> str:
    if sandbox == "none":
        return subprocess.run(command, shell=True,
                              capture_output=True, text=True,
                              timeout=300).stdout

    if sandbox == "restricted":
        return run_restricted(command, cwd)

    if sandbox == "container":
        return run_in_container(command, cwd)

    if sandbox == "virtual":
        return run_in_vm(command, cwd)
```

4. **Restricted 模式。** 限制写入目录和网络访问。

```python
def run_restricted(command: str, cwd: str) -> str:
    import resource

    # 限制写入目录
    allowed_paths = [cwd, "/tmp"]
    env = {**os.environ, "HOME": cwd}

    result = subprocess.run(
        command, shell=True, capture_output=True, text=True,
        timeout=300, cwd=cwd, env=env,
    )

    # 验证写入范围
    for output_file in get_created_files(cwd):
        if not any(output_file.startswith(p) for p in allowed_paths):
            raise PermissionError(f"Write outside allowed dirs: {output_file}")

    return result.stdout
```

5. **Container 模式。** 使用 Docker 容器隔离。

```python
def run_in_container(command: str, cwd: str) -> str:
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{cwd}:/workspace:rw",
            "-w", "/workspace",
            "--network=none",
            "python:3.12-slim",
            "sh", "-c", command,
        ],
        capture_output=True, text=True, timeout=300,
    )
    return result.stdout
```

6. **Virtual 模式。** 完整虚拟机隔离（使用 Firecracker 或类似技术）。

```python
def run_in_vm(command: str, cwd: str) -> str:
    # 启动隔离 VM
    vm = VMManager.launch(image="ubuntu-24.04-mini")
    try:
        # 挂载工作目录
        vm.mount(cwd, "/workspace")
        # 执行命令
        result = vm.exec(command, timeout=300)
        return result.stdout
    finally:
        vm.shutdown()  # 用完即毁
```

7. **沙箱决策日志。** 记录每条命令的沙箱选择。

```python
sandbox_log.append({
    "command": command,
    "category": category,
    "sandbox": sandbox,
    "duration_ms": elapsed,
    "timestamp": time.time(),
})
```

## 相对 s22 的变更

| 组件           | 之前 (s22)               | 之后 (s23)                        |
|----------------|--------------------------|-----------------------------------|
| 执行环境       | 宿主机直接执行           | 四级沙箱隔离                      |
| 命令安全       | 审批策略 (通过/拒绝)      | 审批 + 沙箱 (通过但隔离)          |
| 写操作         | 直接写磁盘               | restricted 模式，限制写入范围      |
| 依赖安装       | 污染宿主机环境           | container 模式，容器内隔离         |
| 网络操作       | 直接访问网络             | virtual 模式，虚拟机隔离           |
| 只读操作       | 直接执行                 | none 模式，保持直接执行            |
| 审计           | 计划执行日志             | + 沙箱决策日志                     |

## 试一试

```sh
cd learn-claude-code
python agents/s23_sandbox_modes.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Run "ls -la" - should execute with no sandbox (none mode)`
2. `Run "echo hello > test.txt" - should use restricted sandbox`
3. `Run "pip install requests" - should use container sandbox`
4. `Run "curl http://example.com" - should use virtual sandbox`
5. `Check the sandbox log to see how each command was classified`
