# s13：系统提示词 —— 动态环境感知拼装

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ]`

> *"提示词知道自己运行在哪里"* —— OS、路径、Shell、用户，全部运行时注入。
>
> **Harness 层**：提示词 —— 基于真实环境状态拼装，绝不硬编码。

## 问题

一个写着 `"You are a coding agent at /home/user/project"` 的系统提示词，只在一台机器上能跑。换一个用户、换一个 OS、换一个 Shell —— 提示词就开始撒谎。智能体接着会建议不存在的命令、解析不了的路径、没安装的工具。

硬编码环境信息会导致三类故障：

1. **OS 命令错误** —— `ls` vs `dir`、`cat` vs `type`、`/usr/bin/python3` vs `C:\Python313\python.exe`
2. **路径错误** —— `/home/alice` vs `C:\Users\alice`、`/tmp` vs `%TEMP%`
3. **Shell 语义错误** —— bash 通配符、PowerShell cmdlet、cmd.exe 怪癖

系统提示词必须反映*真实的*运行时环境：哪个 OS、哪个 Shell、哪个用户、哪些路径存在、哪些工具在 PATH 上。

## 方案

```
环境探测                            系统提示词拼装
+-----------------------+        +-----------------------------+
| OS / 平台             |        | [identity]                  |
| Python 版本           | -----> | [environment]               |
| 工作目录              |        | [tools_available]           |
| Home / temp 路径      |        | [workspace]                 |
| Shell + 环境变量      |        | [safety_constraints]        |
| PATH 上的工具         |        +-----------------------------+
| 用户 / 主机名         |                     |
+-----------------------+                     v
                                    打印 / 发送给 LLM
```

六个分段，两种加载策略：

| 分段               | 策略      | 内容                                     | 来源                       |
|-------------------|-----------|------------------------------------------|----------------------------|
| identity          | 始终加载  | 智能体身份与行为准则                     | 静态                       |
| environment       | 始终加载  | OS、Python、Shell、用户、主机            | `platform`, `os`, `getpass`|
| tools_available   | 始终加载  | PATH 上存在哪些工具                      | `shutil.which`             |
| workspace         | 始终加载  | cwd、home、temp、项目根                  | `pathlib`, `os`            |
| safety_constraints| 始终加载  | 路径边界、危险命令                       | 静态规则                   |
| project_context   | 按需加载  | git 分支、项目文件（如有）               | `subprocess`, `pathlib`    |

核心设计：提示词中的每一个事实都是*运行时探测*出来的，不是手敲的。同一份脚本在 Windows、macOS、Linux 上都能产出正确的提示词，无需改动。

## 工作原理

### 1. 探测 OS 与平台

```python
import platform, os

def probe_os() -> dict:
    return {
        "system": platform.system(),        # Windows / Darwin / Linux
        "release": platform.release(),      # 10 / 23.4.0 / 5.15.0
        "machine": platform.machine(),      # AMD64 / arm64 / x86_64
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
        "is_windows": os.name == "nt",
        "is_macos": platform.system() == "Darwin",
        "is_linux": platform.system() == "Linux",
    }
```

### 2. 探测路径

```python
from pathlib import Path

def probe_paths() -> dict:
    return {
        "cwd": str(Path.cwd()),
        "home": str(Path.home()),
        "temp": str(Path(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")))),
        "python_executable": sys.executable,
    }
```

### 3. 探测 Shell 与用户

```python
import getpass

def probe_user_shell() -> dict:
    return {
        "user": getpass.getuser(),
        "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC", "unknown"),
        "hostname": platform.node(),
    }
```

### 4. 探测 PATH 上的可用工具

```python
import shutil

def probe_tools() -> dict:
    candidates = ["git", "python", "python3", "node", "npm", "docker", "make", "curl"]
    return {name: shutil.which(name) for name in candidates if shutil.which(name)}
```

### 5. 拼装系统提示词

```python
def assemble_system_prompt(env: dict) -> str:
    sections = [
        IDENTITY,
        format_environment(env),
        format_tools(env["tools"]),
        format_workspace(env["paths"]),
        SAFETY_CONSTRAINTS,
    ]
    if env.get("project"):
        sections.append(format_project(env["project"]))
    return "\n\n".join(sections)
```

### 6. 按环境指纹缓存

每轮都重新探测太浪费。对环境 dict 做哈希，只在变化时才重新拼装。

```python
def get_system_prompt(env: dict) -> str:
    key = json.dumps(env, sort_keys=True, default=str)
    if key == _last_key and _last_prompt:
        return _last_prompt  # cache hit
    _last_key = key
    _last_prompt = assemble_system_prompt(env)
    return _last_prompt
```

## 相比 s10 的演进

s10 引入了 `PROMPT_SECTIONS` 和 `assemble_system_prompt(context)`，但 context 很单薄 —— 只有 `enabled_tools`、`workspace`、`memories`。提示词仍然假设是 Unix 环境。

| 维度               | s10                          | s13                                  |
|-------------------|------------------------------|--------------------------------------|
| OS 探测            | 无                           | `platform.system()` + 标志位         |
| 路径解析           | 硬编码 `WORKDIR`             | `Path.cwd()`、`Path.home()`、`TEMP`  |
| Shell 感知         | 无                           | 探测 `SHELL` / `COMSPEC`             |
| 工具可用性         | `TOOLS` 静态列表             | `shutil.which()` 探测 PATH           |
| 用户 / 主机        | 无                           | `getpass.getuser()`、`platform.node()`|
| 项目上下文         | 无                           | git 分支 + 项目文件（可选）          |
| 缓存键             | `json.dumps(context)`        | `json.dumps(env)`（更宽的指纹）      |

## 试一下

```sh
cd learn-claude-code
python s13_system_prompt_manager.py
```

观察重点：

1. 脚本会逐条打印探测到的环境信息
2. 最终拼装好的系统提示词会以代码块形式打印
3. 在 Windows 上会显示 `system: Windows`、`shell: ...powershell...`
4. 在 macOS 上会显示 `system: Darwin`、`shell: /bin/zsh`
5. 再次运行会显示 `[cache hit]`，因为环境没变

试试这些实验：

1. `python s13_system_prompt_manager.py` —— 打印拼装好的提示词
2. `python s13_system_prompt_manager.py --json` —— 输出环境 dict 的 JSON
3. `python s13_system_prompt_manager.py --raw` —— 只打印提示词，不带装饰
4. 切换目录（`cd /tmp && python .../s13_system_prompt_manager.py`）—— 观察 workspace 分段的变化

## 为什么这件事重要

会撒谎的系统提示词比没有提示词更糟。智能体会信任它。如果提示词说 `"Use bash"` 但实际在 Windows 上，智能体执行 `ls -la` 就会收到 `CommandNotFoundException`。如果提示词说 `"Working directory: /home/user"` 但 cwd 实际是 `C:\Users\user`，智能体建议的每一个相对路径都是错的。

动态探测让提示词*诚实*。同一份代码在任何地方运行，产出的提示词都与现实匹配。这是可移植智能体的基石：发布一份代码，跑在任意 OS 上，提示词自己适配。

## 下一步

提示词现在能反映环境了。但智能体在工具调用失败时仍然无法恢复 —— 路径错误、文件缺失、权限拒绝。下一步是错误恢复：捕获、分类、修复后重试。

<!-- translation-sync: zh@v1 -->
