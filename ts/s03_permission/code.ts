/**
 * s03_permission.ts - Permission System
 *
 * TypeScript 1:1 port of s03_permission/code.py
 *
 * Three gates inserted before tool execution:
 *
 *     Gate 1: Hard deny list (rm -rf /, sudo, ...)
 *     Gate 2: Rule matching (write outside workspace? destructive cmd?)
 *     Gate 3: User approval (pause and wait for confirmation)
 *
 *     +----------+      +-------+      +--------------+      +---------------+
 *     |   User   | ---> |  LLM  | ---> | Permission   | ---> | Tool Dispatch |
 *     |  prompt  |      |       |      | 1. deny list |      | execute       |
 *     +----------+      +---+---+      | 2. rules     |      +-------+-------+
 *                           ^          | 3. approval  |              |
 *                           |          +------+-------+              |
 *                           |                 | deny                 |
 *                           |                 v                      v
 *                           |          +-------------------------------+
 *                           +----------+ tool_result: denied or output |
 *                                      +-------------------------------+
 *
 * Only one line added to the agent loop:
 *
 *     if (!(await checkPermission(block))) continue
 *
 * TS-vs-Python 差异:
 *     py 的 input() 是同步阻塞的，所以 check_permission 是普通函数。
 *     TS 的 readline 是异步的，所以 askUser / checkPermission 都是 async，
 *     调用处要 await。这是把"人在环路里"搬到 Node 上的必然代价。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s03
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

const SYSTEM = `You are a coding agent at ${WORKDIR}. All destructive operations require user approval.`;

// Gate 3 要在工具执行中途向用户提问，所以 readline 提到模块顶层，供全文件共用
const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- From s02: tool implementations --
// 注意：和 py 版一样，s03 的文件工具不再走 safePath 硬拦，
// 越界访问改由 Gate 2 + Gate 3 交给用户决定。

// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\n|\r/);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

function runBash({ command }: { command: string }): string {
    const r = spawnSync(command, {
        shell: true,
        cwd: WORKDIR,
        encoding: "utf8",
        timeout: 120_000,
        maxBuffer: 10 * 1024 * 1024,
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

// -- From s02 (unchanged): tool definitions and dispatch --

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
];

type ToolHandler = (args: any) => string;

const TOOL_HANDLERS: Record<string, ToolHandler> = {
    bash: runBash,
    read_file: runRead,
    write_file: runWrite,
    edit_file: runEdit,
    glob: runGlob,
};

// -- New in s03: three-gate permission pipeline --

// Gate 1: Hard deny list - always forbidden
const DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda"];

// py: -> str | None，这里对应 string | null
function checkDenyList(command: string): string | null {
    for (const pattern of DENY_LIST) {
        if (command.includes(pattern)) {
            return `Blocked: '${pattern}' is on the deny list`;
        }
    }
    return null;
}

// Gate 2: Rule matching - context-dependent checks
// py 用 lambda 存进字典；TS 用箭头函数，完全同构
const PERMISSION_RULES: {
    tools: string[];
    check: (args: any) => boolean;
    message: string;
}[] = [
        {
            tools: ["read_file", "write_file", "edit_file"],
            check: (args) => {
                const abs = path.resolve(WORKDIR, args.path ?? "");
                return !(abs === WORKDIR || abs.startsWith(WORKDIR + path.sep));
            },
            message: "Writing outside workspace",
        },
        {
            tools: ["bash"],
            check: (args) =>
                ["rm ", "> /etc/", "chmod 777"].some((kw) => (args.command ?? "").includes(kw)),
            message: "Potentially destructive command",
        },
    ];

function checkRules(toolName: string, args: any): string | null {
    for (const rule of PERMISSION_RULES) {
        if (rule.tools.includes(toolName) && rule.check(args)) {
            return rule.message;
        }
    }
    return null;
}

// Gate 3: User approval - wait for confirmation after rule match
async function askUser(toolName: string, args: any, reason: string): Promise<string> {
    console.log(`\n\x1b[33m[permission] ${reason}\x1b[0m`);
    console.log(`   Tool: ${toolName}(${JSON.stringify(args)})`);
    const choice = (await rl.question("   Allow? [y/N] ")).trim().toLowerCase();
    return ["y", "yes"].includes(choice) ? "allow" : "deny";
}

// Pipeline: all three gates chained
async function checkPermission(block: any): Promise<boolean> {
    if (block.name === "bash") {
        const reason = checkDenyList(block.input.command ?? "");
        if (reason) {
            console.log(`\n\x1b[31m[blocked] ${reason}\x1b[0m`);
            return false;
        }
    }
    const reason = checkRules(block.name, block.input);
    if (reason) {
        const decision = await askUser(block.name, block.input, reason);
        if (decision === "deny") return false;
    }
    return true;
}

// -- Agent loop: same as s02, with checkPermission() inserted --

type Msg = { role: "user" | "assistant"; content: any };

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
        if (toolCalls.length === 0) return;

        const results: any[] = [];
        for (const block of toolCalls) {
            console.log(`\x1b[36m> ${block.name}\x1b[0m`);

            // s03 change: run through permission pipeline before executing
            if (!(await checkPermission(block))) {
                results.push({
                    type: "tool_result",
                    tool_use_id: block.id,
                    content: "Permission denied.",
                });
                continue;
            }

            const handler = TOOL_HANDLERS[block.name];
            const output = handler ? handler(block.input) : `Unknown: ${block.name}`;
            console.log(String(output).slice(0, 200));
            results.push({ type: "tool_result", tool_use_id: block.id, content: output });
        }

        messages.push({ role: "user", content: results });
    }
}

console.log("s03: Permission");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("\x1b[36ms03 >> \x1b[0m");
    } catch {
        break;
    }
    if (["q", "exit", ""].includes(query.trim().toLowerCase())) break;

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
