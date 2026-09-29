/**
 * s02_tool_use.ts - Tools
 *
 * TypeScript 1:1 port of s02_tool_use/code.py
 *
 * The agent loop from s01 does not change. This lesson adds four tools
 * and a dispatch map:
 *
 *     +----------+      +-------+      +--------------------------+
 *     |   User   | ---> |  LLM  | ---> | Tool Dispatch            |
 *     |  prompt  |      |       |      | bash       -> runBash    |
 *     +----------+      +---+---+      | read_file  -> runRead    |
 *                           ^          | write_file -> runWrite   |
 *                           |          | edit_file  -> runEdit    |
 *                           +----------+ glob       -> runGlob    |
 *                           tool_result+--------------------------+
 *
 *   + runRead / runWrite / runEdit / runGlob
 *   + TOOL_HANDLERS instead of a hard-coded runBash call
 *   + safePath to keep file tools inside the workspace
 *
 * Key insight: the loop stays the same; only tool registration and dispatch grow.
 *
 * TS-vs-Python 差异（唯一一处结构性差异）:
 *     py: output = TOOL_HANDLERS[block.name](**block.input)   # 字典解包成关键字参数
 *     ts: output = TOOL_HANDLERS[block.name](block.input)     # TS 没有 **，改成传一个参数对象
 *   所以每个 handler 的签名是 (args: {...}) => string，用解构取字段。
 *   schema 的属性名依然必须和解构出的字段名逐字一致。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s02
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

const SYSTEM = `You are a coding agent at ${WORKDIR}. Use tools to solve tasks. Act, don't explain.`;

// -- From s01 (unchanged) --

// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\n|\r/);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

function runBash({ command }: { command: string }): string {
    const dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"];
    if (dangerous.some((d) => command.includes(d))) {
        return "Error: Dangerous command blocked";
    }
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

// -- New in s02: four tools --

// py: (WORKDIR / p).resolve() + is_relative_to(WORKDIR)
function safePath(p: string): string {
    const resolved = path.resolve(WORKDIR, p);
    if (resolved !== WORKDIR && !resolved.startsWith(WORKDIR + path.sep)) {
        throw new Error(`Path escapes workspace: ${p}`);
    }
    return resolved;
}

function runRead({ path: p, limit }: { path: string; limit?: number }): string {
    try {
        let lines = splitLines(fs.readFileSync(safePath(p), "utf8"));
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
        const filePath = safePath(p);
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
        const filePath = safePath(p);
        const text = fs.readFileSync(filePath, "utf8");
        if (!text.includes(old_text)) return `Error: text not found in ${p}`;
        // py: text.replace(old, new, 1) —— JS 的 String.replace 传字符串时天然只替换第一处
        fs.writeFileSync(filePath, text.replace(old_text, new_text), "utf8");
        return `Edited ${p}`;
    } catch (e: any) {
        return `Error: ${e.message}`;
    }
}

function runGlob({ pattern }: { pattern: string }): string {
    try {
        // py 的 glob 需要 recursive=True 才让 ** 生效；fast-glob 默认就支持 **
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

// -- New in s02: tool definitions (one tool in s01, five in s02) --

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

// -- New in s02: dispatch map (replaces s01's hard-coded runBash call) --

type ToolHandler = (args: any) => string;

const TOOL_HANDLERS: Record<string, ToolHandler> = {
    bash: runBash,
    read_file: runRead,
    write_file: runWrite,
    edit_file: runEdit,
    glob: runGlob,
};

// -- The agent loop keeps the same shape as s01; only dispatch changes --
// s01: output = runBash(block.input.command)
// s02: output = TOOL_HANDLERS[block.name](block.input)

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
            console.log(`\x1b[33m> ${block.name}\x1b[0m`);
            const handler = TOOL_HANDLERS[block.name];
            const output = handler ? handler(block.input) : `Unknown: ${block.name}`;
            console.log(String(output).slice(0, 200));
            results.push({ type: "tool_result", tool_use_id: block.id, content: output });
        }

        messages.push({ role: "user", content: results });
    }
}

console.log("s02: Tool Use - four tools added to s01");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const rl = createInterface({ input: process.stdin, output: process.stdout });
const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("\x1b[36ms02 >> \x1b[0m");
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
