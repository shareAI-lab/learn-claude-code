/**
 * s05_todo_write.ts - TodoWrite
 *
 * TypeScript 1:1 port of s05_todo_write/code.py
 *
 * The model tracks its progress through a TodoManager. After three rounds
 * without an update, the harness adds a reminder alongside the tool results.
 *
 *     +----------+      +-------+      +--------------+
 *     |   User   | ---> |  LLM  | ---> | Tools        |
 *     |  prompt  |      |       |      | + todo_write |
 *     +----------+      +---^---+      +------+-------+
 *                           |                 | update
 *                           |          +------v----------+
 *                           |          | TodoManager     |
 *                           |          | [ ] pending     |
 *                           |          | [>] in progress |
 *                           |          | [x] completed   |
 *                           |          +------+----------+
 *                           | tool_result     |
 *                           +-----------------+
 *
 *               roundsSinceTodo >= 3 -> add <reminder>
 *
 * TS-vs-Python 差异:
 *   py 版在解析 todos 时有两级兜底：先 json.loads，失败再 ast.literal_eval
 *   （后者能吃下 Python 单引号字面量 "[{'content': ...}]"）。
 *   TS 只有 JSON.parse，没有等价的安全字面量解析器，所以只保留一级兜底。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s05
 */

import { spawnSync } from "node:child_process";
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

// s05 change: SYSTEM prompt adds planning guidance
const SYSTEM =
    `You are a coding agent at ${WORKDIR}. ` +
    "Before starting any multi-step task, use todo_write to plan your steps. " +
    "Update status as you go.";

const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- Tool implementations from s02-s04 --

// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\n|\r/);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

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
    } catch (e: any) {
        return `Error: ${e.message}`;
    }
}

function runWrite({ path: p, content }: { path: string; content: string }): string {
    try {
        const filePath = path.resolve(WORKDIR, p);
        fs.mkdirSync(path.dirname(filePath), { recursive: true });
        fs.writeFileSync(filePath, content, "utf8");
        return `Wrote ${content.length} bytes to ${p}`;
    } catch (e: any) {
        return `Error: ${e.message}`;
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
    } catch (e: any) {
        return `Error: ${e.message}`;
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
    } catch (e: any) {
        return `Error: ${e.message}`;
    }
}

// -- New in s05: structured state the model updates --

type TodoStatus = "pending" | "in_progress" | "completed";
type TodoItem = { content: string; status: TodoStatus };

class TodoManager {
    items: TodoItem[] = [];

    update(todos: unknown): string {
        // 模型有时把数组序列化成字符串发过来，先兜一层
        if (typeof todos === "string") {
            try {
                todos = JSON.parse(todos);
            } catch {
                throw new Error("todos must be a list or JSON array string");
            }
        }

        if (!Array.isArray(todos)) throw new Error("todos must be a list");
        if (todos.length > 20) throw new Error("Max 20 todos allowed");

        const validated: TodoItem[] = [];
        let inProgressCount = 0;

        todos.forEach((todo: any, index: number) => {
            if (typeof todo !== "object" || todo === null || Array.isArray(todo)) {
                throw new Error(`todos[${index}] must be an object`);
            }

            const content = String(todo.content ?? "").trim();
            const status = String(todo.status ?? "pending").toLowerCase();

            if (!content) throw new Error(`todos[${index}] requires content`);
            if (!["pending", "in_progress", "completed"].includes(status)) {
                throw new Error(`todos[${index}] has invalid status '${status}'`);
            }
            if (status === "in_progress") inProgressCount += 1;

            validated.push({ content, status: status as TodoStatus });
        });

        if (inProgressCount > 1) {
            throw new Error("Only one todo can be in_progress at a time");
        }

        this.items = validated;
        return this.render();
    }

    render(): string {
        if (this.items.length === 0) return "No todos.";

        const MARKERS: Record<TodoStatus, string> = {
            pending: "[ ]",
            in_progress: "[>]",
            completed: "[x]",
        };

        const lines = this.items.map((todo) => `${MARKERS[todo.status]} ${todo.content}`);
        const done = this.items.filter((todo) => todo.status === "completed").length;
        lines.push(`\n(${done}/${this.items.length} completed)`);
        return lines.join("\n");
    }
}

const TODO = new TodoManager();

function runTodoWrite({ todos }: { todos: unknown }): string {
    let output: string;
    try {
        output = TODO.update(todos);
    } catch (e: any) {
        return `Error: ${e.message}`;
    }
    console.log(`\n\x1b[33m## Current Tasks\x1b[0m\n${output}`);
    return output;
}

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
    // s05: new tool
    {
        name: "todo_write",
        description: "Create and manage a task list for your current coding session.",
        input_schema: {
            type: "object" as const,
            properties: {
                todos: {
                    type: "array",
                    maxItems: 20,
                    items: {
                        type: "object",
                        properties: {
                            content: { type: "string", minLength: 1 },
                            status: { type: "string", enum: ["pending", "in_progress", "completed"] },
                        },
                        required: ["content", "status"],
                    },
                },
            },
            required: ["todos"],
        }
    },
];

type ToolHandler = (args: any) => string;

const TOOL_HANDLERS: Record<string, ToolHandler> = {
    bash: runBash,
    read_file: runRead,
    write_file: runWrite,
    edit_file: runEdit,
    glob: runGlob,
    todo_write: runTodoWrite,
};

// -- Hook system from s04 --

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

/** PreToolUse: s03 permission logic, registered as an s04 hook. */
async function permissionHook(block: any): Promise<HookResult> {
    if (block.name === "bash") {
        const command = block.input.command ?? "";
        for (const pattern of DENY_LIST) {
            if (command.includes(pattern)) {
                console.log(`\n\x1b[31m[blocked] '${pattern}'\x1b[0m`);
                return "Permission denied by deny list";
            }
        }
        for (const keyword of DESTRUCTIVE) {
            if (command.includes(keyword)) {
                console.log(`\n\x1b[33m[permission] Potentially destructive command\x1b[0m`);
                console.log(`   Tool: ${block.name}(${JSON.stringify(block.input)})`);
                const choice = (await rl.question("   Allow? [y/N] ")).trim().toLowerCase();
                if (!["y", "yes"].includes(choice)) return "Permission denied by user";
            }
        }
    }
    if (["read_file", "write_file", "edit_file"].includes(block.name)) {
        const abs = path.resolve(WORKDIR, block.input.path ?? "");
        if (!(abs === WORKDIR || abs.startsWith(WORKDIR + path.sep))) {
            console.log(`\n\x1b[33m[permission] Access outside workspace\x1b[0m`);
            console.log(`   Tool: ${block.name}(${JSON.stringify(block.input)})`);
            const choice = (await rl.question("   Allow? [y/N] ")).trim().toLowerCase();
            if (!["y", "yes"].includes(choice)) return "Permission denied by user";
        }
    }
    return null;
}

/** PreToolUse: log every tool call. */
function logHook(block: any): HookResult {
    const argsPreview = JSON.stringify(Object.values(block.input).slice(0, 2)).slice(0, 60);
    console.log(`\x1b[90m[HOOK] ${block.name}(${argsPreview})\x1b[0m`);
    return null;
}

/** PostToolUse: warn on large output. */
function largeOutputHook(block: any, output: any): HookResult {
    if (String(output).length > 100_000) {
        console.log(
            `\x1b[33m[HOOK] Large output from ${block.name}: ${String(output).length} chars\x1b[0m`,
        );
    }
    return null;
}

/** UserPromptSubmit: log working directory. */
function contextInjectHook(_query: string): HookResult {
    console.log(`\x1b[90m[HOOK] UserPromptSubmit: working in ${WORKDIR}\x1b[0m`);
    return null;
}

/** Stop: print tool call count. */
function summaryHook(messages: Msg[]): HookResult {
    let toolCount = 0;
    for (const m of messages) {
        if (!Array.isArray(m.content)) continue;
        for (const b of m.content) {
            if (b && typeof b === "object" && b.type === "tool_result") toolCount += 1;
        }
    }
    console.log(`\x1b[90m[HOOK] Stop: session used ${toolCount} tool calls\x1b[0m`);
    return null;
}

registerHook("UserPromptSubmit", contextInjectHook);
registerHook("PreToolUse", permissionHook);
registerHook("PreToolUse", logHook);
registerHook("PostToolUse", largeOutputHook);
registerHook("Stop", summaryHook);

// -- The loop with the reminder counter --

type Msg = { role: "user" | "assistant"; content: any };

async function agentLoop(messages: Msg[]): Promise<void> {
    let roundsSinceTodo = 0;

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
        let usedTodo = false;

        for (const block of toolCalls) {
            const blocked = await triggerHooks("PreToolUse", block);
            if (blocked) {
                results.push({
                    type: "tool_result",
                    tool_use_id: block.id,
                    content: String(blocked),
                });
                continue;
            }

            const handler = TOOL_HANDLERS[block.name];
            let output: string;
            try {
                output = handler ? handler(block.input) : `Unknown: ${block.name}`;
            } catch (e: any) {
                output = `Error: ${e.message}`;
            }

            await triggerHooks("PostToolUse", block, output);

            if (block.name === "todo_write") usedTodo = true;

            results.push({
                type: "tool_result",
                tool_use_id: block.id,
                content: String(output),
            });
        }

        roundsSinceTodo = usedTodo ? 0 : roundsSinceTodo + 1;
        if (roundsSinceTodo >= 3) {
            // 关键技巧：把一个 text 块混进 tool_result 列表里搭车发出去，
            // 这样不用单独插一条 user 消息（那会破坏 role 交替）。
            results.push({ type: "text", text: "<reminder>Update your todos.</reminder>" });
            roundsSinceTodo = 0;
        }

        messages.push({ role: "user", content: results });
    }
}

console.log("s05: TodoWrite - plan before execution");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("\x1b[36ms05 >> \x1b[0m");
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
