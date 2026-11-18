/**
 * s10_task_system.ts - Task System
 *
 * TypeScript 1:1 port of s10_task_system/code.py
 *
 *     .tasks/
 *       task_a1b2c3d4.json  {status: completed, blockedBy: []}
 *       task_e5f6a7b8.json  {status: pending, blockedBy: [task_a1b2c3d4]}
 *       task_11223344.json  {status: pending, blockedBy: [task_e5f6a7b8]}
 *
 *     Dependency graph:
 *
 *     +-----------+      +-----------+      +-----------+
 *     | schema    | ---> | API       | ---> | tests     |
 *     | completed |      | pending   |      | pending   |
 *     +-----------+      +-----------+      +-----------+
 *
 *     canStart(API) is true because schema is completed.
 *
 *     Task lifecycle:
 *
 *     pending --claim_task--> in_progress --complete_task--> completed
 *
 * 注意：TASKS_DIR = WORKDIR/.tasks，按运行时的当前目录找。
 *
 * TS-vs-Python 差异（本章新增三处）:
 *   1. py 的 @dataclass + Task(**data) 本身就是一道校验：字段缺了或多了直接 TypeError。
 *      TS 的 JSON.parse 出来是任意对象，没有这层保护，所以手写 taskFromData 校验。
 *   2. secrets.token_hex(4) -> randomBytes(4).toString("hex")
 *   3. py 用 open("x") 的 FileExistsError 做"ID 撞车就重试"；
 *      TS 用 writeFileSync(..., { flag: "wx" }) 并判断 err.code === "EEXIST"。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s10
 */

import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline/promises";

import Anthropic from "@anthropic-ai/sdk";
import dotenv from "dotenv";
import fg from "fast-glob";

const HERE = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(HERE, "../../.env"), override: true, quiet: true });

if (process.env.ANTHROPIC_BASE_URL) {
    delete process.env.ANTHROPIC_AUTH_TOKEN;
}

const WORKDIR = process.cwd();
const client = new Anthropic({ baseURL: process.env.ANTHROPIC_BASE_URL });
const MODEL: string = process.env.MODEL_ID ?? "";
if (!MODEL) throw new Error("MODEL_ID is required (see .env)");

const SYSTEM =
    `You are a coding agent at ${WORKDIR}. ` +
    "Use task tools to track dependencies and progress. Create all task nodes " +
    "first. After create_task returns runtime-generated IDs, use update_task " +
    "with those exact IDs to add dependencies.";

const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- New in s10: persistent task records --

const TASKS_DIR = path.join(WORKDIR, ".tasks");
const TASK_ID_PATTERN = /^task_[0-9a-f]{8}$/;
const TASK_STATUSES = ["pending", "in_progress", "completed"] as const;

// py: @dataclass Task
type Task = {
    id: string;
    subject: string;
    description: string;
    status: string;
    owner: string | null;
    blockedBy: string[];
};

const TASK_FIELDS = ["id", "subject", "description", "status", "owner", "blockedBy"];

/**
 * py 里 Task(**data) 自带校验：缺字段或多字段都会 TypeError。
 * TS 的 JSON.parse 没有这层保护，所以显式补上。
 */
// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
    const lines = text.split(/\r\n|\n|\r/);
    if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
    return lines;
}

function taskFromData(data: any): Task {
    if (typeof data !== "object" || data === null || Array.isArray(data)) {
        throw new Error("Task file is not an object");
    }
    for (const field of TASK_FIELDS) {
        if (!(field in data)) throw new Error(`Task file is missing field: ${field}`);
    }
    for (const key of Object.keys(data)) {
        if (!TASK_FIELDS.includes(key)) {
            throw new Error(`Task file has unexpected field: ${key}`);
        }
    }
    if (!Array.isArray(data.blockedBy)) throw new Error("blockedBy must be a list");
    return {
        id: String(data.id),
        subject: String(data.subject),
        description: String(data.description),
        status: String(data.status),
        owner: data.owner === null || data.owner === undefined ? null : String(data.owner),
        blockedBy: data.blockedBy.map((item: any) => String(item)),
    };
}

class TaskStore {
    directory: string;

    constructor(directory: string) {
        this.directory = directory;
    }

    private root(create = false): string {
        if (create) fs.mkdirSync(this.directory, { recursive: true });
        const root = path.resolve(this.directory);
        const workdir = path.resolve(WORKDIR);
        if (!(root === workdir || root.startsWith(workdir + path.sep))) {
            throw new Error("Task store escapes the workspace");
        }
        return root;
    }

    private taskPath(taskId: string, createRoot = false): string {
        if (typeof taskId !== "string" || !TASK_ID_PATTERN.test(taskId)) {
            // py: f"Invalid task ID: {task_id!r}" —— repr 用单引号
            throw new Error(`Invalid task ID: '${taskId}'`);
        }
        const root = this.root(createRoot);
        const target = path.resolve(root, `${taskId}.json`);
        if (!target.startsWith(root + path.sep)) {
            // py: f"Invalid task ID: {task_id!r}" —— repr 用单引号
            throw new Error(`Invalid task ID: '${taskId}'`);
        }
        return target;
    }

    exists(taskId: string): boolean {
        const target = this.taskPath(taskId);
        return fs.existsSync(target) && fs.statSync(target).isFile();
    }

    create(subject: string, description = ""): Task {
        subject = subject.trim();
        if (!subject) throw new Error("Task subject cannot be empty");

        this.root(true);
        for (let attempt = 0; attempt < 100; attempt++) {
            const task: Task = {
                id: `task_${randomBytes(4).toString("hex")}`,
                subject,
                description,
                status: "pending",
                owner: null,
                blockedBy: [],
            };
            try {
                // py: open("x") —— 独占创建，已存在则抛 FileExistsError
                fs.writeFileSync(this.taskPath(task.id, true), JSON.stringify(task, null, 2), {
                    encoding: "utf8",
                    flag: "wx",
                });
                return task;
            } catch (error: any) {
                if (error?.code === "EEXIST") continue;
                throw error;
            }
        }
        throw new Error("Could not allocate a unique task ID");
    }

    /** Return whether taskId transitively depends on targetId. */
    private dependsOn(taskId: string, targetId: string): boolean {
        const pending = [taskId];
        const visited = new Set<string>();
        while (pending.length > 0) {
            const current = pending.pop()!; // py: pending.pop() 也是从末尾取，LIFO
            if (current === targetId) return true;
            if (visited.has(current)) continue;
            visited.add(current);
            pending.push(...this.load(current).blockedBy);
        }
        return false;
    }

    updateDependencies(taskId: string, addBlockedBy: string[]): Task {
        if (!Array.isArray(addBlockedBy)) {
            throw new Error("addBlockedBy must be a list of task IDs");
        }

        const task = this.load(taskId);
        if (task.status !== "pending" || task.owner !== null) {
            throw new Error(
                `Task ${taskId} dependencies can only be updated while pending and unowned`,
            );
        }

        // py: dict.fromkeys(...) —— 去重且保序
        const dependencies = [...new Set(addBlockedBy)];
        for (const dependency of dependencies) {
            if (dependency === taskId) throw new Error("Task cannot depend on itself");
            if (!this.exists(dependency)) {
                throw new Error(`Dependency not found: ${dependency}`);
            }
            if (!task.blockedBy.includes(dependency) && this.dependsOn(dependency, taskId)) {
                throw new Error(`Dependency cycle detected: ${taskId} -> ${dependency}`);
            }
        }

        for (const dependency of dependencies) {
            if (!task.blockedBy.includes(dependency)) task.blockedBy.push(dependency);
        }
        this.save(task);
        return task;
    }

    save(task: Task): void {
        fs.writeFileSync(
            this.taskPath(task.id, true),
            JSON.stringify(task, null, 2),
            "utf8",
        );
    }

    load(taskId: string): Task {
        const data = JSON.parse(fs.readFileSync(this.taskPath(taskId), "utf8"));
        const task = taskFromData(data);
        if (task.id !== taskId) throw new Error(`Task file ID does not match ${taskId}`);
        if (!(TASK_STATUSES as readonly string[]).includes(task.status)) {
            throw new Error(`Invalid task status: ${task.status}`);
        }
        return task;
    }

    list(): Task[] {
        if (!fs.existsSync(this.directory)) return [];
        const root = this.root();
        const files = fg.sync("task_*.json", { cwd: root, onlyFiles: true }).sort();
        return files.map((filename) => this.load(path.basename(filename, ".json")));
    }
}

const TASKS = new TaskStore(TASKS_DIR);

function createTask(subject: string, description = ""): Task {
    return TASKS.create(subject, description);
}

function updateTask(taskId: string, addBlockedBy: string[]): Task {
    return TASKS.updateDependencies(taskId, addBlockedBy);
}

function loadTask(taskId: string): Task {
    return TASKS.load(taskId);
}

function listTasks(): Task[] {
    return TASKS.list();
}

function getTask(taskId: string): string {
    return JSON.stringify(loadTask(taskId), null, 2);
}

function incompleteDependencies(task: Task): string[] {
    const incomplete: string[] = [];
    for (const dependency of task.blockedBy) {
        try {
            if (loadTask(dependency).status !== "completed") incomplete.push(dependency);
        } catch {
            // py: except (FileNotFoundError, ValueError) —— 读不出来就当成未完成
            incomplete.push(dependency);
        }
    }
    return incomplete;
}

function canStart(taskId: string): boolean {
    return incompleteDependencies(loadTask(taskId)).length === 0;
}

function claimTask(taskId: string, owner = "agent"): string {
    const task = loadTask(taskId);
    if (task.status !== "pending") return `Task ${taskId} is ${task.status}, cannot claim`;

    const dependencies = incompleteDependencies(task);
    if (dependencies.length > 0) {
        // py 打印的是 list 的 repr，形如 ['task_xxx']
        return `Blocked by: [${dependencies.map((d) => `'${d}'`).join(", ")}]`;
    }

    task.owner = owner;
    task.status = "in_progress";
    TASKS.save(task);
    console.log(`  [claim] ${task.subject} -> in_progress (owner: ${owner})`);
    return `Claimed ${task.id} (${task.subject})`;
}

function completeTask(taskId: string, owner = "agent"): string {
    const task = loadTask(taskId);
    if (task.status !== "in_progress") {
        return `Task ${taskId} is ${task.status}, cannot complete`;
    }
    if (task.owner !== owner) {
        return `Task ${taskId} is owned by ${task.owner}, not ${owner}`;
    }

    // 先记下"完成之前就已经就绪"的任务，用来算出这次真正解锁了谁
    const readyBefore = new Set(
        listTasks()
            .filter(
                (candidate) =>
                    candidate.status === "pending" &&
                    candidate.blockedBy.length > 0 &&
                    canStart(candidate.id),
            )
            .map((candidate) => candidate.id),
    );

    task.status = "completed";
    TASKS.save(task);

    const unblocked = listTasks()
        .filter(
            (candidate) =>
                candidate.status === "pending" &&
                candidate.blockedBy.length > 0 &&
                !readyBefore.has(candidate.id) &&
                canStart(candidate.id),
        )
        .map((candidate) => candidate.subject);

    console.log(`  [complete] ${task.subject}`);
    let message = `Completed ${task.id} (${task.subject})`;
    if (unblocked.length > 0) {
        message += `\nUnblocked: ${unblocked.join(", ")}`;
        console.log(`  [unblocked] ${unblocked.join(", ")}`);
    }
    return message;
}

// -- From s04: tool implementations --

function runBash({ command }: { command: string }): string {
    const r = spawnSync(command, {
        shell: true, cwd: WORKDIR, encoding: "utf8",
        timeout: 120_000, maxBuffer: 10 * 1024 * 1024,
    });
    if (r.error) {
        const code = (r.error as NodeJS.ErrnoException).code;
        if (code === "ETIMEDOUT") return "Error: Timeout (120s)";
        return `Error: ${r.error.message}`;
    }
    if (r.signal === "SIGTERM") return "Error: Timeout (120s)";
    const out = `${r.stdout ?? ""}${r.stderr ?? ""}`.trim();
    return out ? out.slice(0, 50_000) : "(no output)";
}

function runRead({ path: p, limit }: { path: string; limit?: number }): string {
    try {
        let lines = splitLines(fs.readFileSync(path.resolve(WORKDIR, p), "utf8"));
        if (limit && limit < lines.length) {
            lines = [...lines.slice(0, limit), `... (${lines.length - limit} more lines)`];
        }
        return lines.join("\n");
    } catch (error: any) {
        return `Error: ${error.message}`;
    }
}

function runWrite({ path: p, content }: { path: string; content: string }): string {
    try {
        const filePath = path.resolve(WORKDIR, p);
        fs.mkdirSync(path.dirname(filePath), { recursive: true });
        fs.writeFileSync(filePath, content, "utf8");
        return `Wrote ${content.length} bytes to ${p}`;
    } catch (error: any) {
        return `Error: ${error.message}`;
    }
}

function runEdit(
    { path: p, old_text, new_text }: { path: string; old_text: string; new_text: string },
): string {
    try {
        const filePath = path.resolve(WORKDIR, p);
        const text = fs.readFileSync(filePath, "utf8");
        if (!text.includes(old_text)) return `Error: text not found in ${p}`;
        fs.writeFileSync(filePath, text.replace(old_text, new_text), "utf8");
        return `Edited ${p}`;
    } catch (error: any) {
        return `Error: ${error.message}`;
    }
}

function runGlob({ pattern }: { pattern: string }): string {
    try {
        const raw = fg.sync(pattern, { cwd: WORKDIR, dot: false, onlyFiles: false });
        const matches = [
            ...new Set(
                raw.filter((m) => {
                    const abs = path.resolve(WORKDIR, m);
                    return abs === WORKDIR || abs.startsWith(WORKDIR + path.sep);
                }),
            ),
        ].sort();
        const shown = matches.slice(0, 200);
        if (matches.length > 200) {
            shown.push("... (more matches omitted; narrow the pattern)");
        }
        return shown.length > 0 ? shown.join("\n") : "(no matches)";
    } catch (error: any) {
        return `Error: ${error.message}`;
    }
}

function runCreateTask(
    { subject, description = "" }: { subject: string; description?: string },
): string {
    const task = createTask(subject, description);
    console.log(`  [create] ${task.subject}`);
    return `Created ${task.id}: ${task.subject}`;
}

function runUpdateTask(
    { task_id, addBlockedBy }: { task_id: string; addBlockedBy: string[] },
): string {
    const task = updateTask(task_id, addBlockedBy);
    const dependencies = task.blockedBy.join(", ") || "(none)";
    console.log(`  [update] ${task.subject} blockedBy: ${dependencies}`);
    return `Updated ${task.id} blockedBy: ${dependencies}`;
}

function runListTasks(): string {
    const tasks = listTasks();
    if (tasks.length === 0) return "No tasks. Use create_task to add some.";

    const MARKERS: Record<string, string> = {
        pending: "[ ]",
        in_progress: "[>]",
        completed: "[x]",
    };

    return tasks
        .map((task) => {
            const marker = MARKERS[task.status] ?? "[?]";
            const dependencies =
                task.blockedBy.length > 0 ? ` (blockedBy: ${task.blockedBy.join(", ")})` : "";
            const owner = task.owner ? ` [${task.owner}]` : "";
            return `${marker} ${task.id}: ${task.subject} [${task.status}]${owner}${dependencies}`;
        })
        .join("\n");
}

function runGetTask({ task_id }: { task_id: string }): string {
    return getTask(task_id);
}

function runClaimTask({ task_id }: { task_id: string }): string {
    return claimTask(task_id, "agent");
}

function runCompleteTask({ task_id }: { task_id: string }): string {
    return completeTask(task_id, "agent");
}

type ToolHandler = (args: any) => string | Promise<string>;

const TOOLS = [
    {
        name: "bash", description: "Run a shell command.",
        input_schema: { type: "object" as const, properties: { command: { type: "string" } }, required: ["command"] }
    },
    {
        name: "read_file", description: "Read file contents.",
        input_schema: { type: "object" as const, properties: { path: { type: "string" }, limit: { type: "integer" } }, required: ["path"] }
    },
    {
        name: "write_file", description: "Write content to a file.",
        input_schema: { type: "object" as const, properties: { path: { type: "string" }, content: { type: "string" } }, required: ["path", "content"] }
    },
    {
        name: "edit_file", description: "Replace exact text in a file once.",
        input_schema: { type: "object" as const, properties: { path: { type: "string" }, old_text: { type: "string" }, new_text: { type: "string" } }, required: ["path", "old_text", "new_text"] }
    },
    {
        name: "glob", description: "Find files matching a glob pattern; ** matches recursively.",
        input_schema: { type: "object" as const, properties: { pattern: { type: "string" } }, required: ["pattern"] }
    },
    {
        name: "create_task", description: "Create a task and return its runtime-generated ID.",
        input_schema: { type: "object" as const, properties: { subject: { type: "string" }, description: { type: "string" } }, required: ["subject"], additionalProperties: false }
    },
    {
        name: "update_task", description: "Add dependencies using IDs returned by create_task.",
        input_schema: { type: "object" as const, properties: { task_id: { type: "string", pattern: "^task_[0-9a-f]{8}$" }, addBlockedBy: { type: "array", items: { type: "string", pattern: "^task_[0-9a-f]{8}$" }, minItems: 1 } }, required: ["task_id", "addBlockedBy"], additionalProperties: false }
    },
    {
        name: "list_tasks", description: "List tasks with status, owner, and dependencies.",
        input_schema: { type: "object" as const, properties: {} }
    },
    {
        name: "get_task", description: "Get a task by ID.",
        input_schema: { type: "object" as const, properties: { task_id: { type: "string" } }, required: ["task_id"] }
    },
    {
        name: "claim_task", description: "Claim a pending task whose dependencies are complete.",
        input_schema: { type: "object" as const, properties: { task_id: { type: "string" } }, required: ["task_id"] }
    },
    {
        name: "complete_task", description: "Complete the task claimed by this agent.",
        input_schema: { type: "object" as const, properties: { task_id: { type: "string" } }, required: ["task_id"] }
    },
];

const TOOL_HANDLERS: Record<string, ToolHandler> = {
    bash: runBash,
    read_file: runRead,
    write_file: runWrite,
    edit_file: runEdit,
    glob: runGlob,
    create_task: runCreateTask,
    update_task: runUpdateTask,
    list_tasks: runListTasks,
    get_task: runGetTask,
    claim_task: runClaimTask,
    complete_task: runCompleteTask,
};

// -- From s04: hooks and permission checks --

type Msg = { role: "user" | "assistant"; content: any };
type HookResult = string | null;
type Hook = (...args: any[]) => HookResult | Promise<HookResult>;

const HOOKS: Record<string, Hook[]> = {
    UserPromptSubmit: [],
    PreToolUse: [],
    PostToolUse: [],
    Stop: [],
};

function registerHook(event: string, callback: Hook): void {
    HOOKS[event].push(callback);
}

async function triggerHooks(event: string, ...args: any[]): Promise<HookResult> {
    for (const callback of HOOKS[event]) {
        const result = await callback(...args);
        if (result !== null && result !== undefined) return result;
    }
    return null;
}

const DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="];
const DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"];

async function permissionHook(block: any): Promise<HookResult> {
    if (block.name === "bash") {
        const command = block.input.command ?? "";
        for (const pattern of DENY_LIST) {
            if (command.includes(pattern)) {
                console.log(`\n\x1b[31m[blocked] '${pattern}'\x1b[0m`);
                return "Permission denied by deny list";
            }
        }
        if (DESTRUCTIVE.some((keyword) => command.includes(keyword))) {
            console.log("\n\x1b[33m[permission] Potentially destructive command\x1b[0m");
            console.log(`   Tool: ${block.name}(${JSON.stringify(block.input)})`);
            const choice = (await rl.question("   Allow? [y/N] ")).trim().toLowerCase();
            if (!["y", "yes"].includes(choice)) return "Permission denied by user";
        }
    }

    if (["read_file", "write_file", "edit_file"].includes(block.name)) {
        const abs = path.resolve(WORKDIR, block.input.path ?? "");
        if (!(abs === WORKDIR || abs.startsWith(WORKDIR + path.sep))) {
            console.log("\n\x1b[33m[permission] Access outside workspace\x1b[0m");
            console.log(`   Tool: ${block.name}(${JSON.stringify(block.input)})`);
            const choice = (await rl.question("   Allow? [y/N] ")).trim().toLowerCase();
            if (!["y", "yes"].includes(choice)) return "Permission denied by user";
        }
    }
    return null;
}

function logHook(block: any): HookResult {
    const preview = JSON.stringify(Object.values(block.input).slice(0, 2)).slice(0, 60);
    console.log(`\x1b[90m[HOOK] ${block.name}(${preview})\x1b[0m`);
    return null;
}

function largeOutputHook(block: any, output: any): HookResult {
    if (String(output).length > 100_000) {
        console.log(
            `\x1b[33m[HOOK] Large output from ${block.name}: ` +
            `${String(output).length} chars\x1b[0m`,
        );
    }
    return null;
}

function contextHook(_query: string): HookResult {
    console.log(`\x1b[90m[HOOK] UserPromptSubmit: working in ${WORKDIR}\x1b[0m`);
    return null;
}

function summaryHook(messages: Msg[]): HookResult {
    let toolCount = 0;
    for (const message of messages) {
        if (!Array.isArray(message.content)) continue;
        for (const block of message.content) {
            if (block && typeof block === "object" && block.type === "tool_result") {
                toolCount += 1;
            }
        }
    }
    console.log(`\x1b[90m[HOOK] Stop: session used ${toolCount} tool calls\x1b[0m`);
    return null;
}

registerHook("UserPromptSubmit", contextHook);
registerHook("PreToolUse", permissionHook);
registerHook("PreToolUse", logHook);
registerHook("PostToolUse", largeOutputHook);
registerHook("Stop", summaryHook);

async function executeTool(block: any): Promise<string> {
    const blocked = await triggerHooks("PreToolUse", block);
    if (blocked) return String(blocked);

    const handler = TOOL_HANDLERS[block.name];
    let output: string;
    try {
        output = handler ? await handler(block.input) : `Unknown: ${block.name}`;
    } catch (error: any) {
        output = `Error: ${error.message}`;
    }

    await triggerHooks("PostToolUse", block, output);
    return String(output);
}

// -- The loop --

async function agentLoop(messages: Msg[]): Promise<void> {
    while (true) {
        const response = await client.messages.create({
            model: MODEL,
            system: SYSTEM,
            messages: messages as any,
            tools: TOOLS as any,
            max_tokens: 8000,
        });
        messages.push({ role: "assistant", content: response.content });

        const toolCalls = response.content.filter(
            (block: any) => block.type === "tool_use",
        ) as any[];
        if (toolCalls.length === 0) {
            const force = await triggerHooks("Stop", messages);
            if (force) {
                messages.push({ role: "user", content: force });
                continue;
            }
            return;
        }

        const results: any[] = [];
        for (const block of toolCalls) {
            const output = await executeTool(block);
            results.push({ type: "tool_result", tool_use_id: block.id, content: output });
        }
        messages.push({ role: "user", content: results });
    }
}

console.log("s10: Task System - dependencies and task state");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("\x1b[36ms10 >> \x1b[0m");
    } catch {
        break;
    }
    if (["q", "exit", ""].includes(query.trim().toLowerCase())) break;

    await triggerHooks("UserPromptSubmit", query);
    history.push({ role: "user", content: query });
    await agentLoop(history);

    const last = history[history.length - 1].content;
    if (Array.isArray(last)) {
        for (const block of last) {
            if (block?.type === "text") console.log(block.text);
        }
    }
    console.log();
}

rl.close();
