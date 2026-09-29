/**
 * s11_background_tasks.ts - Background Tasks
 *
 * TypeScript 1:1 port of s11_background_tasks/code.py
 *
 *     Main flow                                Background
 *     +------------------------------+         +----------------------+
 *     | bash(run_in_background=True) | ------> | run command          |
 *     | return bg_id                 |         | queue result         |
 *     | continue agent loop          | <------ +----------------------+
 *     | next turn: collect           |
 *     +------------------------------+
 *
 * TS-vs-Python 差异（本章是第一个真正的结构性差异）:
 *
 *   1. 线程 → 事件循环
 *      py: threading.Thread(target=..., daemon=True).start()
 *      ts: 调一个 async 函数但**不 await** —— 它在事件循环里自己跑完
 *
 *   2. 锁整个消失
 *      py 需要 threading.Lock 保护 tasks / results / _ready，因为两个线程真的会同时跑。
 *      JS 是单线程的：任何一段同步代码执行期间，别的回调插不进来。
 *      所以 _lock 在 TS 版里没有对应物 —— 不是偷懒，是不需要。
 *
 *   3. 前台 bash 必须改成异步（这一步不做，整章就是坏的）
 *      s01–s10 用的是 spawnSync，它会**阻塞整个进程**，事件循环停转，
 *      后台子进程的 close 回调永远没机会执行。
 *      所以本章把 runBashProcess 换成 spawn + Promise，前台 await、后台不 await。
 *      py 那边前后台共用同一个阻塞函数，因为线程是真并行的。
 *
 *   4. 进程组清理
 *      py: os.killpg(pid, sig)，两个信号之间 sleep 50ms
 *      ts: process.kill(-pid, sig)（负数 = 进程组），需要 spawn 时 detached: true。
 *          Node 的退出钩子必须同步，所以省掉了那 50ms 间隔。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s11
 */

import { spawn, type ChildProcess } from "node:child_process";
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
  `You are a coding agent at ${WORKDIR}. Use tools to solve tasks. ` +
  "Set run_in_background to true only for independent Bash commands.";

const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- From s04: tool implementations --

// py: _shell_processes + _shell_process_lock
// JS 单线程，不需要锁
const shellProcesses = new Set<ChildProcess>();

/** Stop processes that remain in the command's original process group. */
// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\n|\r/);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

function stopProcessGroup(child: ChildProcess): void {
  if (child.pid === undefined) return;
  // py 在 SIGTERM 和 SIGKILL 之间 sleep(0.05)；
  // Node 的 exit 钩子必须同步，所以这里连着发。
  for (const sig of ["SIGTERM", "SIGKILL"] as const) {
    try {
      process.kill(-child.pid, sig); // 负 pid = 整个进程组
    } catch {
      return;
    }
  }
}

function stopAllShellProcesses(): void {
  for (const child of [...shellProcesses]) stopProcessGroup(child);
}

// py: atexit.register + signal.signal(SIGTERM, ...)
process.on("exit", stopAllShellProcesses);
process.on("SIGTERM", () => {
  stopAllShellProcesses();
  process.exit(128 + 15);
});

/**
 * py 这里是阻塞的 Popen.communicate(timeout=120)，靠线程实现并发。
 * TS 改成 Promise：前台 await 它，后台不 await —— 并发交给事件循环。
 */
function runBashProcess(command: string): Promise<[string, number | null]> {
  return new Promise((resolve) => {
    let child: ChildProcess;
    try {
      child = spawn(command, {
        shell: true,
        cwd: WORKDIR,
        detached: true, // py: start_new_session=True —— 自成进程组，才能整组 kill
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch (error: any) {
      resolve([`Error: ${error?.constructor?.name ?? "Error"}: ${error.message}`, null]);
      return;
    }

    shellProcesses.add(child);

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let settled = false;

    child.stdout?.setEncoding("utf8");
    child.stderr?.setEncoding("utf8");
    child.stdout?.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr?.on("data", (chunk: string) => {
      stderr += chunk;
    });

    const timer = setTimeout(() => {
      timedOut = true;
      stopProcessGroup(child);
    }, 120_000);

    const finish = (value: [string, number | null]) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      stopProcessGroup(child);
      shellProcesses.delete(child);
      resolve(value);
    };

    child.on("error", (error: any) => {
      finish([`Error: ${error?.constructor?.name ?? "Error"}: ${error.message}`, null]);
    });

    child.on("close", (code) => {
      if (timedOut) {
        finish(["Error: Timeout (120s)", null]);
        return;
      }
      const output = `${stdout}${stderr}`.trim();
      finish([output ? output.slice(0, 50_000) : "(no output)", code]);
    });
  });
}

function formatBashResult(output: string, exitCode: number | null): string {
  if (exitCode === 0 || exitCode === null) return output;
  return `Error: command exited with status ${exitCode}\n${output}`;
}

async function runBash(
  { command }: { command: string; run_in_background?: boolean },
): Promise<string> {
  const [output, exitCode] = await runBashProcess(command);
  return formatBashResult(output, exitCode);
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

type ToolHandler = (args: any) => string | Promise<string>;

const TOOLS = [
  { name: "bash", description: "Run a shell command.",
    input_schema: { type: "object" as const,
      properties: { command: { type: "string" }, run_in_background: { type: "boolean" } },
      required: ["command"] } },
  { name: "read_file", description: "Read file contents.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, limit: { type: "integer" } }, required: ["path"] } },
  { name: "write_file", description: "Write content to a file.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, content: { type: "string" } }, required: ["path", "content"] } },
  { name: "edit_file", description: "Replace exact text in a file once.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, old_text: { type: "string" }, new_text: { type: "string" } }, required: ["path", "old_text", "new_text"] } },
  { name: "glob", description: "Find files matching a glob pattern; ** matches recursively.",
    input_schema: { type: "object" as const, properties: { pattern: { type: "string" } }, required: ["pattern"] } },
];

const TOOL_HANDLERS: Record<string, ToolHandler> = {
  bash: runBash,
  read_file: runRead,
  write_file: runWrite,
  edit_file: runEdit,
  glob: runGlob,
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

function contextInjectHook(_query: string): HookResult {
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

registerHook("UserPromptSubmit", contextInjectHook);
registerHook("PreToolUse", permissionHook);
registerHook("PreToolUse", logHook);
registerHook("PostToolUse", largeOutputHook);
registerHook("Stop", summaryHook);

async function callTool(block: any): Promise<string> {
  const handler = TOOL_HANDLERS[block.name];
  let output: string;
  try {
    output = handler ? await handler(block.input) : `Unknown: ${block.name}`;
  } catch (error: any) {
    output = `Error: ${error.message}`;
  }
  return String(output);
}

// -- New in s11: background execution --

type BackgroundTask = { tool_use_id: string; command: string; status: string };

class BackgroundManager {
  tasks: Record<string, BackgroundTask> = {};
  results: Record<string, string> = {};
  private ready: string[] = [];
  private counter = 0;
  // py 这里有 threading.Lock；JS 单线程，不需要

  start(block: any): string {
    if (block.name !== "bash") {
      throw new Error("Only Bash commands can run in the background");
    }
    const command = block.input.command;
    if (typeof command !== "string" || !command.trim()) {
      throw new Error("Bash command cannot be empty");
    }

    this.counter += 1;
    const taskId = `bg_${String(this.counter).padStart(4, "0")}`;
    this.tasks[taskId] = {
      tool_use_id: block.id,
      command,
      status: "running",
    };

    // py: threading.Thread(...).start()
    // ts: 调 async 函数但不 await —— 它在事件循环里自己跑完
    void this.run(taskId, command);

    console.log(`  [background] started ${taskId}: ${command.slice(0, 60)}`);
    return taskId;
  }

  private async run(taskId: string, command: string): Promise<void> {
    let result: string;
    let status: string;
    try {
      const [output, exitCode] = await runBashProcess(command);
      result = formatBashResult(output, exitCode);
      status = exitCode === 0 ? "completed" : "failed";
    } catch (error: any) {
      result = `Error: ${error?.constructor?.name ?? "Error"}: ${error.message}`;
      status = "failed";
    }

    const task = this.tasks[taskId];
    if (task === undefined) return;
    task.status = status;
    this.results[taskId] = result;
    this.ready.push(taskId);
  }

  collect(): string[] {
    const ready: [string, BackgroundTask, string][] = [];
    for (const taskId of this.ready) {
      const task = this.tasks[taskId];
      const result = this.results[taskId] ?? "";
      delete this.tasks[taskId];
      delete this.results[taskId];
      if (task !== undefined) ready.push([taskId, task, result]);
    }
    this.ready = [];

    const notifications: string[] = [];
    for (const [taskId, task, result] of ready) {
      notifications.push(
        `<task_notification>\n` +
          `  <task_id>${taskId}</task_id>\n` +
          `  <status>${task.status}</status>\n` +
          `  <command>${task.command}</command>\n` +
          `  <summary>${result.slice(0, 500)}</summary>\n` +
          `</task_notification>`,
      );
      console.log(`  [background] collected ${taskId}: ${task.status}`);
    }
    return notifications;
  }
}

const BACKGROUND = new BackgroundManager();
const backgroundTasks = BACKGROUND.tasks;
const backgroundResults = BACKGROUND.results;
void backgroundTasks;
void backgroundResults;

function shouldRunBackground(toolName: string, toolInput: any): boolean {
  return toolName === "bash" && toolInput?.run_in_background === true;
}

function startBackgroundTask(block: any): string {
  return BACKGROUND.start(block);
}

function collectBackgroundResults(): string[] {
  return BACKGROUND.collect();
}

function injectBackgroundResults(messages: Msg[]): number {
  const notifications = collectBackgroundResults();
  if (notifications.length === 0) return 0;

  const blocks = notifications.map((item) => ({ type: "text", text: item }));
  const last = messages[messages.length - 1];

  if (last && last.role === "user") {
    const content = last.content ?? "";
    if (Array.isArray(content)) {
      content.push(...blocks);
    } else {
      last.content = [{ type: "text", text: String(content) }, ...blocks];
    }
  } else {
    messages.push({ role: "user", content: blocks });
  }
  return notifications.length;
}

async function executeTool(block: any): Promise<string> {
  const blocked = await triggerHooks("PreToolUse", block);
  if (blocked !== null && blocked !== undefined) return String(blocked);

  let output: string;
  if (shouldRunBackground(block.name, block.input)) {
    try {
      const taskId = startBackgroundTask(block);
      output =
        `[Background task ${taskId} started] ` +
        "The result will be collected on a later turn.";
    } catch (error: any) {
      output = `Error: ${error.message}`;
    }
  } else {
    output = await callTool(block);
  }

  await triggerHooks("PostToolUse", block, output);
  return output;
}

// -- The loop --

async function agentLoop(messages: Msg[]): Promise<void> {
  while (true) {
    injectBackgroundResults(messages);

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

console.log("s11: Background Tasks - explicit background Bash execution");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
  let query: string;
  try {
    query = await rl.question("\x1b[36ms11 >> \x1b[0m");
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
