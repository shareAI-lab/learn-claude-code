/**
 * s04_hooks.ts - Hooks
 *
 * TypeScript 1:1 port of s04_hooks/code.py
 *
 * Hooks run callbacks at fixed points in the agent loop:
 *
 *     User prompt
 *          |
 *          v
 *     UserPromptSubmit
 *          |
 *          v
 *     +----------+      +-------+      +------------+      +-------+
 *     | messages | ---> |  LLM  | ---> | PreToolUse | ---> | Tool  |
 *     +----------+      +---+---+      | permission |      +---+---+
 *          ^                | stop     | log        |          |
 *          |                v          +------------+          v
 *          |            Stop hook                         PostToolUse
 *          |                                               |
 *          +---------------- tool_result ------------------+
 *
 * TS-vs-Python 差异:
 *     钩子里要向用户提问（异步），所以 hook 回调和 triggerHooks 都是 async，
 *     调用处 await。py 版是同步的。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s04
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

const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- From s02-s03: tool implementations --

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

const TOOLS = [
  { name: "bash", description: "Run a shell command.",
    input_schema: { type: "object" as const, properties: { command: { type: "string" } }, required: ["command"] } },
  { name: "read_file", description: "Read file contents.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, limit: { type: "integer" } }, required: ["path"] } },
  { name: "write_file", description: "Write content to a file.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, content: { type: "string" } }, required: ["path", "content"] } },
  { name: "edit_file", description: "Replace exact text in a file once.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, old_text: { type: "string" }, new_text: { type: "string" } }, required: ["path", "old_text", "new_text"] } },
  { name: "glob", description: "Find files matching a glob pattern; ** matches recursively.",
    input_schema: { type: "object" as const, properties: { pattern: { type: "string" } }, required: ["pattern"] } },
];

type ToolHandler = (args: any) => string;

const TOOL_HANDLERS: Record<string, ToolHandler> = {
  bash: runBash,
  read_file: runRead,
  write_file: runWrite,
  edit_file: runEdit,
  glob: runGlob,
};

// -- New in s04: hook system (s03 permission logic now uses hooks) --

// py: 返回 None 表示放行；TS 用 null。回调可以是同步或 async。
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
    if (result !== null && result !== undefined) {
      // A hook result blocks this tool call.
      return result;
    }
  }
  return null;
}

// s03 permission check logic, now wrapped as a hook
const DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="];
const DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"];

/** PreToolUse: s03 checkPermission() logic moved here. */
async function permissionHook(block: any): Promise<HookResult> {
  if (block.name === "bash") {
    const command = block.input.command ?? "";
    for (const pattern of DENY_LIST) {
      if (command.includes(pattern)) {
        console.log(`\n\x1b[31m[blocked] '${pattern}'\x1b[0m`);
        return "Permission denied by deny list";
      }
    }
    for (const kw of DESTRUCTIVE) {
      if (command.includes(kw)) {
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

/** UserPromptSubmit: log user input before it reaches the LLM. */
function contextInjectHook(_query: string): HookResult {
  console.log(`\x1b[90m[HOOK] UserPromptSubmit: working in ${WORKDIR}\x1b[0m`);
  return null;
}

/** Stop: print summary when loop is about to exit. */
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

// -- The loop: same structure as s03, but no hard-coded check --
// s03: if (!(await checkPermission(block))) ...
// s04: if (await triggerHooks("PreToolUse", block)) ...

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
    if (toolCalls.length === 0) {
      const force = await triggerHooks("Stop", messages);
      if (force) {
        // Stop 钩子可以驳回"收工"，把它的返回值当一条用户消息塞回去
        messages.push({ role: "user", content: force });
        continue;
      }
      return;
    }

    const results: any[] = [];
    for (const block of toolCalls) {
      // s04 change: hook replaces hard-coded checkPermission()
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
      const output = handler ? handler(block.input) : `Unknown: ${block.name}`;

      await triggerHooks("PostToolUse", block, output); // s04: post hook

      results.push({ type: "tool_result", tool_use_id: block.id, content: output });
    }

    messages.push({ role: "user", content: results });
  }
}

console.log("s04: Hooks - extension logic on hooks, loop stays clean");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
  let query: string;
  try {
    query = await rl.question("\x1b[36ms04 >> \x1b[0m");
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
