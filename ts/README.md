# TypeScript 版 s01–s11 + s13–s15

根目录 `s01_agent_loop/` … `s11_background_tasks/` 和 `s13`–`s15` 里 Python 课程的 TypeScript 1:1 移植，
用来对照阅读。Python 版仍是课程正本，这里只做逐行对照，不改教学结构。

s12（cron 调度）、s16、s17 未移植。

> s06 和 Python 版一样建立在 s04（钩子）之上，**不含** s05 的 `todo_write`。

## 运行

```sh
cd ts
npm install          # 只需一次
npm run s01          # s01 … s11, s13, s14, s15（s12 未移植）
npm run typecheck    # tsc --noEmit
```

⚠️ s09 的 `.memory/` 和 s07 的 `skills/` 一样按 cwd 找。`npm run s09` 会在 `ts/` 下建
`.memory/`，换个目录跑就是另一份记忆库 —— 这是设计如此，不是 bug。

⚠️ **s07 必须在仓库根目录运行**，因为 `SKILLS_DIR = WORKDIR/skills` 是按当前目录找的。
在 `ts/` 下跑会静默得到一个空目录（`(no skills found)`），模型就不知道有技能可用。
`npm run s07` 里已经加了 `cd ..`，所以直接用它就行；用 VS Code 调试时注意 `cwd` 选仓库根目录。

`.env` 读的是仓库根目录那一份（`ANTHROPIC_API_KEY` + `MODEL_ID`），和 Python 版共用。

工作目录是你执行 `npm run` 时所在的目录，也就是 `WORKDIR`。想让 agent 在沙箱里干活：

```sh
cd ../.playground && npx tsx ../ts/s02_tool_use/code.ts
```

## 与 Python 版的对应关系

| Python | TypeScript |
|---|---|
| `run_bash` / `run_read` / … | `runBash` / `runRead` / … |
| `TOOLS` / `TOOL_HANDLERS` / `HOOKS` | 同名 |
| `agent_loop` | `agentLoop` |
| `check_permission` | `checkPermission` |
| `TodoManager` | 同名 |
| `execute_tool` / `run_subagent` / `extract_text` | `executeTool` / `runSubagent` / `extractText` |
| `BASE_TOOLS` / `SUB_TOOLS` / `TASK_TOOL` | 同名 |
| `SkillLoader` / `parse_frontmatter` | `SkillLoader` / `SkillLoader.parseFrontmatter` |
| `yaml.safe_load`（pyyaml） | `YAML.parse`（`yaml` 包） |
| `ContextCompactor` / `snip_compact` / `micro_compact` | `ContextCompactor` / `snipCompact` / `microCompact` |
| `messages[:] = xxx`（原地替换） | `messages.splice(0, messages.length, ...xxx)` |
| `uuid.uuid4().hex` | `randomUUID().replace(/-/g, "")` |
| `path.open("x")`（独占创建） | `fs.writeFileSync(p, data, { flag: "wx" })` |
| `set[tuple[int, int]]` | `Set<string>`，键编码成 `"mi:bi"` |
| `subprocess.run(shell=True, timeout=120)` | `spawnSync(cmd, { shell: true, timeout: 120_000 })` |
| `pathlib.Path` / `is_relative_to` | `node:path` / `startsWith(WORKDIR + path.sep)` |
| `glob.glob(recursive=True)` | `fast-glob`（Node 20 没有 `fs.globSync`） |
| `input()` | `readline/promises` 的 `rl.question()` |

## 二十七处刻意的差异

1. **没有 `**kwargs`**（s02 起）
   ```python
   output = TOOL_HANDLERS[block.name](**block.input)   # 字典解包成关键字参数
   ```
   ```ts
   output = TOOL_HANDLERS[block.name](block.input);    // 传一个参数对象
   ```
   所以 handler 签名是 `(args: { path: string; limit?: number }) => string`，用解构取字段。
   约束不变：**schema 的属性名必须和解构出的字段名逐字一致**。

2. **权限/钩子变成异步**（s03 起）
   `input()` 在 Python 里同步阻塞，Node 的 readline 是 Promise，所以
   `askUser` / `checkPermission` / `permissionHook` / `triggerHooks` 都是 `async`，调用处 `await`。

3. **`.env` 路径要显式写**
   `load_dotenv()` 会从调用文件往上找，`dotenv` 不会，所以每个文件里有：
   ```ts
   dotenv.config({ path: path.resolve(HERE, "../../.env"), override: true, quiet: true });
   ```

4. **s05 少一层容错**
   Python 版解析 `todos` 时先 `json.loads`，失败再 `ast.literal_eval`（能吃下
   `"[{'content': ...}]"` 这种 Python 单引号字面量）。TS 只有 `JSON.parse`，
   没有等价的安全字面量解析器，所以只有一级兜底。

5. **工具 handler 变成可异步**（s06 起）
   `runSubagent` 是一个工具 handler，但它内部要 `await client.messages.create`。
   py 里全程同步，TS 里类型必须放宽：
   ```ts
   type ToolHandler = (args: any) => string | Promise<string>;   // 原来只有 string
   ```
   于是 `executeTool` 里改成 `await handler(block.input)`。
   顺带一个好处：这个类型一旦放宽，后面要加任何 I/O 型工具（HTTP 请求、数据库查询）
   都不用再改派发层了。

6. **方法引用会丢 `this`**（s07）
   ```python
   TOOL_HANDLERS = { "load_skill": SKILL_LOADER.load }   # 绑定方法，this 自带
   ```
   ```ts
   // ❌ 裸传方法引用，运行时 this 是 undefined → 读 this.skills 直接炸
   // load_skill: SKILL_LOADER.load,
   // ✅ 包一层箭头函数
   load_skill: ({ name }: { name: string }) => SKILL_LOADER.load(name),
   ```
   Python 的 `obj.method` 是绑定方法，JS 的 `obj.method` 只是个函数引用 —— 这是移植
   任何"把类方法注册进表里"的代码时最容易踩的坑。

7. **`parse_frontmatter` 的多返回值**（s07）
   py 返回 `tuple[dict, str]`，TS 没有多返回值，改成返回对象
   `{ metadata, body }`，调用处解构。

8. **切片赋值 → `splice`**（s08，本章最危险的一处）
   ```python
   messages[:] = COMPACTOR.prepare(messages, active_request)   # 原地替换整个列表
   ```
   py 的 `messages[:] = xxx` 会**原地改写**列表，外层持有的 `history` 立刻看到新内容。
   TS 没有切片赋值：
   ```ts
   messages.splice(0, messages.length, ...prepared);   // ✅ 原地替换
   // messages = prepared;                             // ❌ 只改局部变量，history 不受影响
   ```
   写错不会报错、不会崩，只是压缩**永远不生效**，历史继续疯涨 —— 典型的静默失效。
   本章把它包成了 `replaceInPlace(messages, next)`。

9. **压缩链全变 async**（s08）
   `summarizeHistory` 要调 API，于是 `compactHistory` / `reactiveCompact` / `prepare`
   全部 `async`，`agentLoop` 里每次调模型前都要 `await COMPACTOR.prepare(...)`。

10. **`estimateChars` 的绝对值和 py 不同**（s08）
    py 的 `json.dumps(messages, default=str)` 把 SDK 块对象转成 repr 字符串
    （`"TextBlock(text='...', type='text')"`），TS 的 `JSON.stringify` 则序列化成完整 JSON。
    两边都能衡量"历史涨了多少"，但**数字不可直接对比**，触发压缩的时机会略有差异。

11. **`split(sep, maxsplit)` 语义相反**（s09）
    ```python
    parts = text.split("---", 2)   # 最多切 2 刀，剩下的**全塞进第 3 项**
    ```
    JS 的 `split(sep, limit)` 是"只取前 limit 项，**剩下的丢掉**"——直接照抄会把
    frontmatter 之后的正文吃掉。改成手写 `indexOf` 切片。

12. **`\w` 在 py 认中文，在 JS 不认**（s09）
    ```python
    re.sub(r"[^\w]+", "-", name.lower())    # py3 的 \w 是 unicode 感知的
    ```
    ```ts
    name.toLowerCase().replace(/[^\p{L}\p{N}_]+/gu, "-")   // 必须 \p{L}\p{N} + u 标志
    ```
    照抄 `\w` 的话，中文记忆名会被整个替换成 `-`，slug 全变成 `"memory"`，
    第二条中文记忆直接覆盖第一条。已实测两边对 `"用户偏好设置"` 都产出同名 slug。

13. **没有 `raw_decode` 等价物**（s09）
    py 用 `json.JSONDecoder().raw_decode(text[pos:])` 从任意位置解出一个 JSON 值
    （用来从模型的散文回复里抠出 `[0, 2]`）。JS 没有这个 API，改成扫描配对括号
    （跳过字符串内的括号和转义）再 `JSON.parse`。已实测两边对
    `'text {"a":1} then [1,[2,3],{"k":"]"}] end'` 这类刁钻输入结果一致。

14. **`@dataclass` 自带的校验消失了**（s10）
    ```python
    task = Task(**data)     # 缺字段 / 多字段 → TypeError，等于一道免费的 schema 校验
    ```
    `JSON.parse` 出来是任意对象，没有这层保护。所以手写了 `taskFromData`：
    检查 6 个字段齐全、没有多余字段、`blockedBy` 是数组。
    不补的话，一个被手改坏的 `.tasks/*.json` 会带着 `undefined` 一路往下跑。

15. **`secrets.token_hex(4)` → `randomBytes(4).toString("hex")`**（s10）
    并且"ID 撞车就重试"的机制从 `open("x")` 的 `FileExistsError`
    改成 `writeFileSync(..., { flag: "wx" })` 判 `error.code === "EEXIST"`。

16. **`!r`（repr）是单引号**（s10）
    ```python
    raise ValueError(f"Invalid task ID: {task_id!r}")   # → Invalid task ID: 'nope'
    ```
    最初我用了 `JSON.stringify` 得到双引号，对拍时被抓出来。错误串是要回传给模型的，
    所以按 py 的单引号对齐。

17. **线程 → 事件循环**（s11，本课程第一个真正的结构性差异）

    | | Python | TypeScript |
    |---|---|---|
    | 并发原语 | `threading.Thread(daemon=True)` | 调 async 函数**不 await** |
    | 互斥 | `threading.Lock` 保护三份共享状态 | **不需要**——JS 单线程，同步代码不会被打断 |
    | 前台 bash | `Popen.communicate()` 阻塞（线程真并行，无所谓） | 必须换成 `spawn` + Promise |
    | 进程组 | `start_new_session=True` + `os.killpg(pid, sig)` | `detached: true` + `process.kill(-pid, sig)` |
    | 退出清理 | `atexit` + `signal.signal(SIGTERM)` | `process.on("exit")` + `process.on("SIGTERM")` |

    第三行是**不做就整章报废**的那个：`spawnSync` 会阻塞整个 Node 进程，
    事件循环停转，后台子进程的 `close` 回调永远等不到执行机会。
    py 那边前后台共用一个阻塞函数没问题，因为线程是真并行的。

    另外 py 在 `SIGTERM` 和 `SIGKILL` 之间 `sleep(0.05)`；Node 的退出钩子必须同步，
    所以省掉了这个间隔。

18. **`fcntl.flock` → `O_EXCL` 锁文件**（s13）
    Node 没有 flock。改成 `fs.openSync(lockPath, "wx")` 自旋抢占，10 秒后抢走陈旧锁。
    可重入靠一个 `taskLockDepth` 计数器（py 用 `threading.local`）。

19. **两把 `threading.RLock` 整个删掉**（s13）
    py 的 `task_lock` / `team_lock` 保护线程交错。JS 单线程：**一段不含 `await` 的
    同步代码执行期间没有任何东西能插进来**。s13 所有临界区（`claimTask` /
    `completeTask` / 协议状态机）都是纯同步的，所以天然原子。
    这是这两个并发模型的实质差别，不是省略 —— 但也意味着：
    **将来若在临界区里加一个 `await`，原子性立刻消失**，得自己引入异步互斥量。

20. **`select.select([sys.stdin], 0.25)` → AbortController**（s13）
    Lead 的 REPL 要同时等"用户输入"和"teammate 事件"。py 轮询 stdin；
    TS 用可中断的 `rl.question(q, { signal })` + 一个 250ms 轮询邮箱的协程，
    邮箱有信时 abort 掉输入等待。

21. **`teammate_threads` → `teammateRuntimes`**（s13）
    py 存 `threading.Thread` 对象（用于登记/清理）。TS 没有线程对象可存，
    改存 runtime 实例本身；`thread.start()` 对应 `void runtime.run()`。

22. **闭包捕获循环变量：py 要技巧，JS 不用**（s14，唯一一处 TS 更简单的差异）
    ```python
    handlers[prefixed] = (lambda *, client=server, tool=raw_name,
                          **kwargs: client.call_tool(tool, kwargs))
    ```
    py 的闭包是 **late binding**：不用默认参数把 `server` / `raw_name` 绑死的话，
    所有闭包都会看到循环结束后的最后一个值。
    ```ts
    handlers[prefixed] = (args: any) => server.callTool(rawName, args);
    ```
    JS 的 `for-of` + `const` 每轮是**新绑定**，直接写就对。

23. **元组键 → 字符串键**（s14）
    ```python
    MCP_HOST_POLICY = {("docs", "search"): "allow", ...}
    ```
    JS 的对象和 Map 都不做元组值比较，键拼成 `"docs/search"`。

24. **`Path.resolve()` 跟随符号链接，`path.resolve()` 不跟随**（s07 + s15）
    对拍时抓到的**真 bug**：`skills/` 是符号链接时，校验永远不成立 →
    技能一个都扫不到，而且不报错。必须用 `fs.realpathSync`。

25. **`splitlines()` vs `split("\n")`**（s02–s15 共 13 个文件）
    ```python
    "l1\nl2\n".splitlines()   # ['l1','l2']      2 项
    ```
    ```js
    "l1\nl2\n".split("\n")    // ["l1","l2",""]  3 项
    ```
    py 的 `splitlines()` **不会因末尾换行多产生空元素**。不修的话每个
    `read_file` 的行数和 `... (N more lines)` 都差 1。统一加了 `splitLines()`。

26. **s15 跨章节加载 s09**
    py 用 `importlib` 动态加载 `s09_memory/code.py` 并**覆写其全局变量**。
    TS 改成静态 `import`（ESM 的 const 无法从外部覆写，改为共享 cwd），
    并给 `ts/s09_memory/code.ts` 加了 main 守卫 —— 不然一 import 就进 REPL。
    `tsconfig.json` 需要 `allowImportingTsExtensions`。

27. **`agent_lock` 必须是真正的异步互斥量**（s15，唯一一处不能靠单线程白嫖）
    py 用 `threading.Lock` 串行化"主 REPL 回合"和"异步事件循环回合"。
    TS 的 `agentLoop` 全是 `await`，中间会让出事件循环 —— 删掉锁两个回合就会
    交错改同一份 `history`。本章实现了 `AsyncMutex`（Promise 链排队），
    并实测严格串行（`A-in,A-out,B-in,B-out`）。
    对比 s13 的第 19 条：那里能删锁，是因为临界区**全是同步代码**。

## 保留的教学特征

和 Python 版一样，**每个文件都是独立可运行的完整实现，没有跨章节 import、没有共享模块**。
重复是刻意的——`diff s01_agent_loop/code.ts s02_tool_use/code.ts` 就能看出这一章加了什么。

同样保留了原版的教学级简化：`DENY_LIST` 只是字符串匹配、`bash` 能绕过 `safePath`、
todo 只存内存不落盘。别当生产代码用。
