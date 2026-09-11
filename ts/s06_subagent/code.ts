/**
 * s06_subagent.ts - Subagents
 *
 * TypeScript 1:1 port of s06_subagent/code.py
 *
 * The task tool runs a second agent loop with a fresh message list. Both
 * loops share the working directory, but only the final text returns to
 * the parent conversation.
 *
 *     Parent agent                    Subagent
 *     +------------------+            +------------------+
 *     | messages=[...]   |            | messages=[prompt]|
 *     |                  |   task     |                  |
 *     | tool: task       | ---------> | own agent loop   |
 *     |                  |            | base tools only  |
 *     | tool_result      | <--------- | final text       |
 *     +------------------+            +------------------+
 *
 * The subagent has no task tool, so it cannot delegate again.
 *
 * 注意：s06 建立在 s04（钩子）之上，不含 s05 的 todo_write —— 和 Python 版一致。
 *
 * TS-vs-Python 差异（本章新增一处）:
 *     runSubagent 是个工具 handler，但它内部要 await client.messages.create。
 *     py 里全程同步，TS 里 handler 必须能返回 Promise：
 *         type ToolHandler = (args: any) => string | Promise<string>
 *     所以 executeTool 里改成 await handler(...)。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s06
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

const SYSTEM =
  `You are a coding agent at ${WORKDIR}. ` +
  "Use task for focused exploration or a self-contained subtask.";
const SUB_SYSTEM =
  `You are a coding agent at ${WORKDIR}. ` +
  "Complete the given task, then return a concise final answer.";

const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- Base tools --

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

// py: handler 可能是同步的普通工具，也可能是 async 的 runSubagent
type ToolHandler = (args: any) => string | Promise<string>;

const BASE_TOOLS = [
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

const BASE_HANDLERS: Record<string, ToolHandler> = {
  bash: runBash,
  read_file: runRead,
  write_file: runWrite,
  edit_file: runEdit,
  glob: runGlob,
};

// -- Hooks --

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

/** PreToolUse: block denied operations and ask about risky ones. */
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
        console.log("\n\x1b[33m[permission] Potentially destructive command\x1b[0m");
        console.log(`   Tool: ${block.name}(${JSON.stringify(block.input)})`);
        const choice = (await rl.question("   Allow? [y/N] ")).trim().toLowerCase();
        if (!["y", "yes"].includes(choice)) return "Permission denied by user";
      }
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

/** UserPromptSubmit: log the working directory. */
function contextInjectHook(_query: string): HookResult {
  console.log(`\x1b[90m[HOOK] UserPromptSubmit: working in ${WORKDIR}\x1b[0m`);
  return null;
}

/** Stop: print the number of tool results in this message list. */
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

registerHook("UserPromptSubmit", contextInjectHook);
registerHook("PreToolUse", permissionHook);
registerHook("PreToolUse", logHook);
registerHook("PostToolUse", largeOutputHook);
registerHook("Stop", summaryHook);

// s06: 工具执行被抽成一个函数，父 agent 和子 agent 共用同一套钩子+派发
async function executeTool(
  block: any,
  handlers: Record<string, ToolHandler>,
): Promise<string> {
  const blocked = await triggerHooks("PreToolUse", block);
  if (blocked) return String(blocked);

  const handler = handlers[block.name];
  let output: string;
  try {
    output = handler ? await handler(block.input) : `Unknown: ${block.name}`;
  } catch (e: any) {
    output = `Error: ${e.message}`;
  }

  await triggerHooks("PostToolUse", block, output);
  return String(output);
}

// -- New in s06: a nested agent loop with fresh messages --

// 拷贝而不是引用 —— 子 agent 的工具池里没有 task，所以它无法再往下委派
const SUB_TOOLS = [...BASE_TOOLS];
const SUB_HANDLERS: Record<string, ToolHandler> = { ...BASE_HANDLERS };

function extractText(content: any): string {
  if (!Array.isArray(content)) return String(content);
  return content
    .filter((block: any) => block?.type === "text")
    .map((block: any) => block.text ?? "")
    .join("\n");
}

async function runSubagent({ prompt }: { prompt: string }): Promise<string> {
  console.log("\n\x1b[35m[Subagent started]\x1b[0m");

  // 关键：全新的 messages，父对话的历史一个字都没带进来
  const messages: Msg[] = [{ role: "user", content: prompt }];

  for (let turn = 0; turn < 30; turn++) {
    const response = await client.messages.create({
      model: MODEL,
      system: SUB_SYSTEM,
      messages: messages as any,
      tools: SUB_TOOLS as any,
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
      console.log("\x1b[35m[Subagent done]\x1b[0m");
      // 只有最终文本回到父对话，中间几十轮工具调用全部丢弃
      return extractText(response.content) || "(no summary)";
    }

    const results: any[] = [];
    for (const block of toolCalls) {
      const output = await executeTool(block, SUB_HANDLERS);
      console.log(`  \x1b[90m[sub] ${block.name}: ${output.slice(0, 100)}\x1b[0m`);
      results.push({
        type: "tool_result",
        tool_use_id: block.id,
        content: output,
      });
    }
    messages.push({ role: "user", content: results });
  }

  console.log("\x1b[35m[Subagent stopped]\x1b[0m");
  return "Subagent stopped after 30 turns without a final answer.";
}

const TASK_TOOL = {
  name: "task",
  description: "Run a subagent with fresh conversation context and return its final text.",
  input_schema: {
    type: "object" as const,
    properties: { prompt: { type: "string", minLength: 1 } },
    required: ["prompt"],
  },
};

const TOOLS = [...BASE_TOOLS, TASK_TOOL];
const TOOL_HANDLERS: Record<string, ToolHandler> = {
  ...BASE_HANDLERS,
  task: runSubagent,
};

// -- Parent agent loop --

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
      const output = await executeTool(block, TOOL_HANDLERS);
      results.push({
        type: "tool_result",
        tool_use_id: block.id,
        content: output,
      });
    }
    messages.push({ role: "user", content: results });
  }
}

console.log("s06: Subagent - fresh messages, final text returns");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
  let query: string;
  try {
    query = await rl.question("\x1b[36ms06 >> \x1b[0m");
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
