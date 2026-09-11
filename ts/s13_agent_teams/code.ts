/**
 * s13: Agent Teams - persistent teammates with shared tasks and mailboxes.
 *
 * TypeScript 1:1 port of s13_agent_teams/code.py
 *
 *     +------+  spawn(task_id)  +----------+  result  +------+
 *     | Lead | ---------------> |   WORK   | -------> | IDLE |
 *     +--+---+                  +----+-----+          +--+---+
 *        ^                           |                   |
 *        | team events               | tools             | wait
 *        |                           v                   v
 *     +--+-----------+          +----------+        +----------+
 *     | MessageBus   |          | Task cwd | <----- | Mailbox  |
 *     +--------------+          +----------+  claim +----------+
 *
 *     .tasks/       shared task records and dependencies
 *     .mailboxes/   messages, results, and protocol responses
 *     .worktrees/   optional task-bound working directories
 *
 * TS-vs-Python 差异（本章四处，都是并发模型造成的）:
 *
 *   1. fcntl.flock -> O_EXCL 锁文件
 *      Node 没有 flock。改成 open(lockPath, "wx") 自旋抢占 + 超时。
 *      只用于跨进程；同进程内不需要（见第 2 条）。
 *
 *   2. threading.RLock（task_lock / team_lock）-> 删掉
 *      py 需要它，因为线程会在任意字节码边界切换。
 *      JS 单线程：一段**不含 await 的同步代码**执行期间没有任何东西能插进来。
 *      本章所有临界区（claimTask / completeTask / 协议状态机）都是纯同步的，
 *      所以天然原子。这不是省略，是这两个并发模型的实质差别。
 *
 *   3. threading.Thread -> 并发 async 函数
 *      每个 teammate 是一个不被 await 的 async 函数，有自己的 messages 和
 *      自己的 await client.messages.create。事件循环负责交错。
 *
 *   4. select.select([sys.stdin], timeout) -> AbortController + rl.question
 *      Lead 的 REPL 要同时等"用户输入"和"teammate 事件"。
 *      py 用 select 轮询 stdin；TS 用可中断的 rl.question(q, { signal })，
 *      邮箱有信时 abort 掉输入等待。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s13
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

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
const isInside = (target: string, root: string) =>
  target === root || target.startsWith(root + path.sep);

// -- Task System --

const TASKS_DIR = path.join(WORKDIR, ".tasks");
const TASKS_ROOT = path.resolve(TASKS_DIR);
const TASK_ID_PATTERN = /^task_[0-9a-f]{8}$/;
const TASK_LOCK_PATH = path.join(TASKS_DIR, ".lock");

// owner -> {task_id, cwd}. 一个 teammate 同时只有一份 assignment，
// 所有文件工具都通过这张表解析自己的 cwd。
const teammateAssignments: Record<string, { task_id: string; cwd: string }> = {};
const assignmentVersions: Record<string, number> = {};

let taskLockDepth = 0;

/**
 * py: fcntl.flock(LOCK_EX) —— 跨线程 + 跨进程串行化
 * ts: 只需跨进程（同进程内同步代码天然原子），用 O_EXCL 锁文件自旋
 */
// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\n|\r/);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

function withTaskStoreLock<T>(fn: () => T): T {
  if (taskLockDepth > 0) {
    // py 用 threading.local 的 depth 实现可重入，这里同理
    taskLockDepth += 1;
    try {
      return fn();
    } finally {
      taskLockDepth -= 1;
    }
  }

  fs.mkdirSync(TASKS_DIR, { recursive: true });
  const deadline = Date.now() + 10_000;
  let fd: number | undefined;
  while (fd === undefined) {
    try {
      fd = fs.openSync(TASK_LOCK_PATH, "wx");
    } catch (error: any) {
      if (error?.code !== "EEXIST") throw error;
      if (Date.now() > deadline) {
        // 别人的锁烂在那儿了，抢过来
        try {
          fs.unlinkSync(TASK_LOCK_PATH);
        } catch {
          /* ignore */
        }
      }
    }
  }

  taskLockDepth = 1;
  try {
    return fn();
  } finally {
    taskLockDepth = 0;
    try {
      fs.closeSync(fd);
      fs.unlinkSync(TASK_LOCK_PATH);
    } catch {
      /* ignore */
    }
  }
}

/** Invalidate old approvals without clearing an explicit plan requirement. */
function advanceAssignmentVersion(owner: string): void {
  assignmentVersions[owner] = (assignmentVersions[owner] ?? 0) + 1;
  if (owner in planGates && planGates[owner] !== "not_required") {
    planGates[owner] = "required";
  }
  delete planRequestIds[owner];
}

type Task = {
  id: string;
  subject: string;
  description: string;
  status: string; // pending | in_progress | completed
  owner: string | null;
  blockedBy: string[];
  worktree: string | null;
};

const TASK_FIELDS = [
  "id", "subject", "description", "status", "owner", "blockedBy", "worktree",
];

// py: Task(**data) 自带字段校验，TS 手写
function taskFromData(data: any): Task {
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new Error("Task file is not an object");
  }
  for (const key of Object.keys(data)) {
    if (!TASK_FIELDS.includes(key)) {
      throw new Error(`Task file has unexpected field: ${key}`);
    }
  }
  for (const field of TASK_FIELDS.slice(0, 6)) {
    if (!(field in data)) throw new Error(`Task file is missing field: ${field}`);
  }
  if (!Array.isArray(data.blockedBy)) throw new Error("blockedBy must be a list");
  return {
    id: String(data.id),
    subject: String(data.subject),
    description: String(data.description),
    status: String(data.status),
    owner: data.owner == null ? null : String(data.owner),
    blockedBy: data.blockedBy.map((x: any) => String(x)),
    worktree: data.worktree == null ? null : String(data.worktree),
  };
}

function taskPath(taskId: string): string {
  if (typeof taskId !== "string" || !TASK_ID_PATTERN.test(taskId)) {
    throw new Error(`Invalid task ID: '${taskId}'`);
  }
  const target = path.resolve(TASKS_DIR, `${taskId}.json`);
  if (!isInside(TASKS_ROOT, path.resolve(WORKDIR)) || !isInside(target, TASKS_ROOT)) {
    throw new Error(`Invalid task ID: '${taskId}'`);
  }
  return target;
}

function createTask(subject: string, description = ""): Task {
  subject = subject.trim();
  if (!subject) throw new Error("Task subject cannot be empty");
  return withTaskStoreLock(() => {
    for (let attempt = 0; attempt < 100; attempt++) {
      const task: Task = {
        id: `task_${randomBytes(4).toString("hex")}`,
        subject,
        description,
        status: "pending",
        owner: null,
        blockedBy: [],
        worktree: null,
      };
      try {
        fs.writeFileSync(taskPath(task.id), JSON.stringify(task, null, 2), {
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
  });
}

/** Return whether taskId transitively depends on targetId. */
function taskDependsOn(taskId: string, targetId: string): boolean {
  const pending = [taskId];
  const visited = new Set<string>();
  while (pending.length > 0) {
    const current = pending.pop()!;
    if (current === targetId) return true;
    if (visited.has(current)) continue;
    visited.add(current);
    pending.push(...loadTask(current).blockedBy);
  }
  return false;
}

/** Add dependency edges after createTask has returned real task IDs. */
function updateTask(taskId: string, addBlockedBy: string[]): Task {
  if (!Array.isArray(addBlockedBy)) {
    throw new Error("addBlockedBy must be a list of task IDs");
  }
  return withTaskStoreLock(() => {
    const task = loadTask(taskId);
    if (task.status !== "pending" || task.owner !== null) {
      throw new Error(
        `Task ${taskId} dependencies can only be updated while pending and unowned`,
      );
    }
    const dependencies = [...new Set(addBlockedBy)];
    for (const dependency of dependencies) {
      if (dependency === taskId) throw new Error("Task cannot depend on itself");
      const depPath = taskPath(dependency);
      if (!fs.existsSync(depPath) || !fs.statSync(depPath).isFile()) {
        throw new Error(`Dependency not found: ${dependency}`);
      }
      if (!task.blockedBy.includes(dependency) && taskDependsOn(dependency, taskId)) {
        throw new Error(`Dependency cycle detected: ${taskId} -> ${dependency}`);
      }
    }
    for (const dependency of dependencies) {
      if (!task.blockedBy.includes(dependency)) task.blockedBy.push(dependency);
    }
    saveTask(task);
    return task;
  });
}

let saveCounter = 0;

function saveTask(task: Task): void {
  withTaskStoreLock(() => {
    const target = taskPath(task.id);
    saveCounter += 1;
    // py: .{name}.{pid}.{tid}.tmp —— TS 没有线程 id，用进程内计数器
    const temporary = path.join(
      path.dirname(target),
      `.${path.basename(target)}.${process.pid}.${saveCounter}.tmp`,
    );
    try {
      fs.writeFileSync(temporary, JSON.stringify(task, null, 2), "utf8");
      fs.renameSync(temporary, target); // py: os.replace —— 原子替换
    } finally {
      try {
        fs.unlinkSync(temporary);
      } catch {
        /* missing_ok=True */
      }
    }
  });
}

function loadTask(taskId: string): Task {
  const data = JSON.parse(fs.readFileSync(taskPath(taskId), "utf8"));
  const task = taskFromData(data);
  if (task.id !== taskId) throw new Error(`Task file ID does not match ${taskId}`);
  if (!["pending", "in_progress", "completed"].includes(task.status)) {
    throw new Error(`Invalid task status: ${task.status}`);
  }
  return task;
}

function listTasks(): Task[] {
  if (!fs.existsSync(TASKS_DIR)) return [];
  if (!isInside(TASKS_ROOT, path.resolve(WORKDIR))) {
    throw new Error("Tasks directory escapes workspace");
  }
  return fg
    .sync("task_*.json", { cwd: TASKS_ROOT, onlyFiles: true })
    .sort()
    .map((filename) => loadTask(path.basename(filename, ".json")));
}

/** Return full task details as JSON. */
function getTask(taskId: string): string {
  return JSON.stringify(loadTask(taskId), null, 2);
}

/**
 * Check if all blockedBy dependencies are completed.
 * Missing dependencies are treated as blocked.
 */
function canStart(taskId: string): boolean {
  const task = loadTask(taskId);
  for (const depId of task.blockedBy) {
    let depPath: string;
    try {
      depPath = taskPath(depId);
    } catch {
      return false;
    }
    if (!fs.existsSync(depPath)) return false;
    if (loadTask(depId).status !== "completed") return false;
  }
  return true;
}

function ownerInProgress(owner: string): Task | null {
  return (
    listTasks().find((t) => t.status === "in_progress" && t.owner === owner) ?? null
  );
}

function incompleteDependencies(task: Task): string[] {
  const incomplete: string[] = [];
  for (const depId of task.blockedBy) {
    let depPath: string;
    try {
      depPath = taskPath(depId);
    } catch {
      incomplete.push(depId);
      continue;
    }
    if (!fs.existsSync(depPath) || loadTask(depId).status !== "completed") {
      incomplete.push(depId);
    }
  }
  return incomplete;
}

/** Atomically claim one task and bind the owner's filesystem cwd. */
function claimTask(taskId: string, owner = "agent"): string {
  const message = withTaskStoreLock(() => {
    const task = loadTask(taskId);
    if (task.status !== "pending") return `Task ${taskId} is ${task.status}, cannot claim`;
    if (task.owner) return `Task ${taskId} is already owned by ${task.owner}`;

    const assignment = teammateAssignments[owner];
    if (assignment) {
      return (
        `Owner ${owner} must finish the current work turn for ` +
        `${assignment.task_id} before claiming another task`
      );
    }
    const current = ownerInProgress(owner);
    if (current) {
      return `Owner ${owner} must complete ${current.id} before claiming another task`;
    }
    if (!canStart(taskId)) {
      const deps = incompleteDependencies(task);
      return `Blocked by: [${deps.map((d) => `'${d}'`).join(", ")}]`;
    }
    const [cwd, error] = taskWorktreeCwd(task);
    if (error) return `Cannot claim ${taskId}: ${error}`;

    task.owner = owner;
    task.status = "in_progress";
    saveTask(task);
    teammateAssignments[owner] = { task_id: task.id, cwd };
    advanceAssignmentVersion(owner);
    return ` claimed:${task.id}:${task.subject}`;
  });

  if (message.startsWith(" claimed:")) {
    const rest = message.slice(" claimed:".length);
    const sep = rest.indexOf(":");
    const id = rest.slice(0, sep);
    const subject = rest.slice(sep + 1);
    console.log(`  [claim] ${subject} -> in_progress (owner: ${owner})`);
    return `Claimed ${id} (${subject})`;
  }
  return message;
}

/** Complete an assignment only when the caller owns it. */
function completeTask(taskId: string, owner = "agent"): string {
  let subject = "";
  let unblocked: string[] = [];

  const message = withTaskStoreLock(() => {
    const task = loadTask(taskId);
    if (task.status !== "in_progress") {
      return `Task ${taskId} is ${task.status}, cannot complete`;
    }
    if (task.owner !== owner) {
      return `Task ${taskId} is owned by ${task.owner}, not ${owner}; cannot complete`;
    }
    const gate = planGates[owner] ?? "not_required";
    if (["required", "pending", "rejected"].includes(gate)) {
      return `Task ${taskId} cannot complete while plan status is ${gate}`;
    }
    const assignment = teammateAssignments[owner];
    if (!assignment || assignment.task_id !== task.id) {
      const [cwd, error] = taskWorktreeCwd(task);
      if (error) return `Task ${taskId} cannot complete: ${error}`;
      teammateAssignments[owner] = { task_id: task.id, cwd };
    }
    task.status = "completed";
    saveTask(task);
    subject = task.subject;
    unblocked = listTasks()
      .filter((t) => t.status === "pending" && t.blockedBy.length > 0 && canStart(t.id))
      .map((t) => t.subject);
    return "";
  });

  if (message) return message;

  console.log(`  [complete] ${subject}`);
  let result = `Completed ${taskId} (${subject})`;
  if (unblocked.length > 0) {
    result += `\nUnblocked: ${unblocked.join(", ")}`;
    console.log(`  [unblocked] ${unblocked.join(", ")}`);
  }
  return result;
}

// -- Task-bound Worktrees --

const WORKTREES_DIR = path.join(WORKDIR, ".worktrees");
const WORKTREES_ROOT = path.resolve(WORKTREES_DIR);
const VALID_WORKTREE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

function validateWorktreeName(name: string): string | null {
  if (typeof name !== "string" || !VALID_WORKTREE_NAME.test(name)) {
    return (
      "worktree name must be 1-64 letters, digits, dots, " +
      "underscores, or dashes, and start with a letter or digit"
    );
  }
  if (name === "." || name === ".." || name.includes("..")) {
    return "worktree name cannot contain '..'";
  }
  return null;
}

function worktreePath(name: string): string {
  const target = path.resolve(WORKTREES_DIR, name);
  if (
    !isInside(WORKTREES_ROOT, path.resolve(WORKDIR)) ||
    !isInside(target, WORKTREES_ROOT) ||
    target === WORKTREES_ROOT
  ) {
    throw new Error(`Worktree path escapes directory: '${name}'`);
  }
  return target;
}

function worktreeBranch(name: string): string {
  return `wt/${name}`;
}

/** Run Git without shell interpolation and preserve machine output. */
function rawGit(args: string[], cwd?: string): [boolean, string] {
  const r = spawnSync("git", args, {
    cwd: cwd ?? WORKDIR,
    encoding: "utf8",
    timeout: 30_000,
    shell: false,
  });
  if (r.error) {
    const name = (r.error as any).code ?? r.error.constructor?.name ?? "Error";
    return [false, `${name}: ${r.error.message}`];
  }
  const output = `${r.stdout ?? ""}${r.stderr ?? ""}`.trim();
  return [r.status === 0, output || "(no output)"];
}

/** Run Git and bound only the text returned to the model. */
function runGit(args: string[], cwd?: string): [boolean, string] {
  const [ok, output] = rawGit(args, cwd);
  return [ok, output.slice(0, 5000)];
}

function registeredWorktrees(): [Record<string, Record<string, string>>, string | null] {
  const [ok, output] = rawGit(["worktree", "list", "--porcelain"]);
  if (!ok) return [{}, `cannot read Git worktree registry: ${output}`];

  const entries: Record<string, Record<string, string>> = {};
  let current: Record<string, string> = {};
  for (const line of [...output.split("\n"), ""]) {
    if (!line) {
      const rawPath = current["worktree"];
      if (rawPath) entries[path.resolve(rawPath)] = current;
      current = {};
      continue;
    }
    const spaceIndex = line.indexOf(" ");
    const key = spaceIndex === -1 ? line : line.slice(0, spaceIndex);
    const value = spaceIndex === -1 ? "" : line.slice(spaceIndex + 1);
    current[key] = value;
  }
  return [entries, null];
}

function registeredWorktree(name: string): [string | null, string | null] {
  let target: string;
  try {
    target = worktreePath(name);
  } catch (error: any) {
    return [null, error.message];
  }
  const [entries, error] = registeredWorktrees();
  if (error) return [null, error];
  if (!(target in entries)) return [null, `worktree '${name}' is not registered with Git`];
  if (!fs.existsSync(target) || !fs.statSync(target).isDirectory()) {
    return [null, `worktree '${name}' is missing at ${target}`];
  }
  const expectedBranch = `refs/heads/${worktreeBranch(name)}`;
  if (entries[target]["branch"] !== expectedBranch) {
    return [
      null,
      `worktree '${name}' is not registered on expected branch '${worktreeBranch(name)}'`,
    ];
  }
  return [target, null];
}

/** Resolve a task cwd, failing closed for broken worktree bindings. */
function taskWorktreeCwd(task: Task): [string, string | null] {
  if (!task.worktree) return [WORKDIR, null];
  const [target, error] = registeredWorktree(task.worktree);
  return [target ?? WORKDIR, error];
}

function assignmentCwd(owner: string): string {
  let assignment = teammateAssignments[owner];
  const inProgress = ownerInProgress(owner);

  if (inProgress && (!assignment || assignment.task_id !== inProgress.id)) {
    const [cwd, error] = taskWorktreeCwd(inProgress);
    if (error) throw new Error(error);
    assignment = { task_id: inProgress.id, cwd };
    teammateAssignments[owner] = assignment;
  } else if (!assignment) {
    return WORKDIR;
  }

  const task = loadTask(assignment.task_id);
  if (!["in_progress", "completed"].includes(task.status) || task.owner !== owner) {
    throw new Error(`Assignment for ${owner} is no longer active`);
  }
  const [cwd, error] = taskWorktreeCwd(task);
  if (error) throw new Error(error);
  if (path.resolve(cwd) !== path.resolve(assignment.cwd)) {
    throw new Error(`Assignment cwd changed for task ${task.id}`);
  }
  return cwd;
}

/** Release a completed cwd lease only at a model turn boundary. */
function releaseCompletedAssignment(owner: string): boolean {
  const assignment = teammateAssignments[owner];
  if (!assignment) return false;
  const task = loadTask(assignment.task_id);
  if (task.status !== "completed" || task.owner !== owner) return false;
  delete teammateAssignments[owner];
  advanceAssignmentVersion(owner);
  if (owner in planGates) planGates[owner] = "not_required";
  return true;
}

/** Return abandoned teammate work to the task board on thread exit. */
function releaseTeammateAssignment(owner: string): void {
  try {
    const task = ownerInProgress(owner);
    if (task) {
      task.status = "pending";
      task.owner = null;
      saveTask(task);
    }
  } finally {
    delete teammateAssignments[owner];
    advanceAssignmentVersion(owner);
    if (owner in planGates) planGates[owner] = "not_required";
  }
}

/** Create and bind a dedicated worktree after all inputs validate. */
function createWorktree(name: string, taskId: string): string {
  const nameError = validateWorktreeName(name);
  if (nameError) return `Error: ${nameError}`;

  let target: string;
  let taskFile: string;
  try {
    target = worktreePath(name);
    taskFile = taskPath(taskId);
  } catch (error: any) {
    return `Error: ${error.message}`;
  }
  const branch = worktreeBranch(name);

  const result = withTaskStoreLock(() => {
    if (!fs.existsSync(taskFile)) return `Error: Task ${taskId} not found`;
    const task = loadTask(taskId);
    if (task.status !== "pending" || task.owner !== null) {
      return `Error: Task ${taskId} must be pending and unowned`;
    }
    if (task.worktree) {
      return `Error: Task ${taskId} already uses worktree '${task.worktree}'`;
    }
    if (listTasks().some((t) => t.id !== taskId && t.worktree === name)) {
      return `Error: Worktree '${name}' is already bound to another task`;
    }
    if (fs.existsSync(target)) return `Error: Worktree path already exists: ${target}`;

    const [rootOk, root] = runGit(["rev-parse", "--show-toplevel"]);
    if (!rootOk || path.resolve(root) !== path.resolve(WORKDIR)) {
      return "Error: Working directory must be the root of a Git repository";
    }
    const [formatOk, branchCheck] = runGit(["check-ref-format", "--branch", branch]);
    if (!formatOk) return `Error: Invalid worktree branch '${branch}': ${branchCheck}`;

    const [exists] = runGit(["show-ref", "--verify", "--quiet", `refs/heads/${branch}`]);
    if (exists) return `Error: Branch '${branch}' already exists`;

    const [entries, registryError] = registeredWorktrees();
    if (registryError) return `Error: ${registryError}`;
    if (target in entries) return `Error: Worktree path is already registered: ${target}`;

    fs.mkdirSync(WORKTREES_DIR, { recursive: true });
    const [addOk, addResult] = runGit(["worktree", "add", "-b", branch, target, "HEAD"]);
    if (!addOk) {
      const [entries2, registryError2] = registeredWorktrees();
      const [branchExists] = runGit([
        "show-ref", "--verify", "--quiet", `refs/heads/${branch}`,
      ]);
      const artifacts: string[] = [];
      if (fs.existsSync(target)) artifacts.push(`checkout path '${target}'`);
      if (registryError2 === null && target in entries2) {
        artifacts.push("registered Git worktree");
      }
      if (branchExists) artifacts.push(`branch '${branch}'`);
      if (artifacts.length > 0) {
        return (
          "Partial operation: git worktree add reported an error " +
          `after leaving ${artifacts.join(", ")}. Task ${taskId} ` +
          "remains unbound and no Git data was deleted. Run " +
          `\`git worktree list\`, inspect '${target}' and '${branch}', ` +
          "then keep or remove those artifacts manually after " +
          `preserving any work. Git error: ${addResult}`
        );
      }
      return `Git error: ${addResult}`;
    }

    try {
      task.worktree = name;
      saveTask(task);
    } catch (error: any) {
      return (
        `Partial success: Worktree '${name}' was created at ` +
        `${target} on branch '${branch}', but task binding failed: ` +
        `${error.message}. Git data was retained for manual recovery.`
      );
    }
    return "";
  });

  if (result) return result;
  console.log(`  \x1b[33m[worktree] created: ${name} at ${target}\x1b[0m`);
  return `Worktree '${name}' created at ${target} for task ${taskId}`;
}

/** Remove a registered checkout while always retaining its branch. */
function removeWorktree(name: string, discardChanges = false): string {
  const nameError = validateWorktreeName(name);
  if (nameError) return `Error: ${nameError}`;

  const result = withTaskStoreLock(() => {
    const [target, error] = registeredWorktree(name);
    if (error || target === null) return `Error: ${error}`;

    const bound = listTasks().filter((task) => task.worktree === name);
    if (bound.length === 0) return `Error: Worktree '${name}' is not bound to a task`;
    const active = bound.filter((task) => task.status !== "completed");
    if (active.length > 0) {
      return (
        `Error: Worktree '${name}' is bound to active task ` +
        `${active[0].id}; complete it before removal`
      );
    }
    const leased = Object.entries(teammateAssignments)
      .filter(([, assignment]) => path.resolve(assignment.cwd) === path.resolve(target))
      .map(([owner]) => owner)
      .sort();
    if (leased.length > 0) {
      return (
        `Error: Worktree '${name}' is still in use by ` +
        `${leased.join(", ")}; wait for the turn to end`
      );
    }

    const [statusOk, status] = runGit(["status", "--porcelain", "--ignored"], target);
    if (!statusOk) return `Error: Cannot verify worktree '${name}' status: ${status}`;
    if (status !== "(no output)" && !discardChanges) {
      const changed = status.split("\n").filter((line) => line.trim()).length;
      return (
        `Error: Worktree '${name}' has ${changed} uncommitted ` +
        "change(s); preserve or discard them manually"
      );
    }

    const args = ["worktree", "remove"];
    if (discardChanges) args.push("--force");
    args.push(target);
    const [removeOk, removeResult] = runGit(args);
    if (!removeOk) return `Git error: ${removeResult}`;

    try {
      for (const task of bound) {
        task.worktree = null;
        saveTask(task);
      }
    } catch (error: any) {
      return (
        `Partial success: Worktree '${name}' was removed and ` +
        `branch '${worktreeBranch(name)}' retained, but task ` +
        `unbinding failed: ${error.message}. Manual recovery is required.`
      );
    }
    return "";
  });

  if (result) return result;
  console.log(`  [worktree] removed: ${name}; branch retained`);
  return `Worktree '${name}' removed; branch '${worktreeBranch(name)}' retained`;
}

// -- System Prompt --

const PROMPT_SECTIONS: Record<string, string> = {
  identity: "You are a coding agent. Act, don't explain.",
  tools:
    "Available tools: bash, read_file, write_file, edit_file, glob, " +
    "create_task, update_task, list_tasks, get_task, claim_task, " +
    "complete_task, " +
    "spawn_teammate, list_teammates, send_message, request_shutdown, " +
    "request_plan, review_plan, create_worktree.",
  tasks:
    "Create all task nodes first. Only after create_task returns " +
    "runtime-generated IDs, use update_task with those exact IDs to add " +
    "dependencies. Only the Lead changes task dependencies.",
  teams:
    "When parallel work would help, first propose a small team with clear " +
    "responsibilities and wait for the user's confirmation. Do not call " +
    "spawn_teammate before the user confirms. After confirmation, delegate " +
    "independent work by creating a Task for each parallel change. Pass " +
    "task_id to spawn_teammate when assigning ready work, then " +
    "create a task-bound worktree only when a separate working directory " +
    "would prevent conflicting edits. A teammate must complete its current " +
    "Task before claiming another. A worktree changes tool default cwd " +
    "only; it is not a sandbox. Worktree removal stays with the host or " +
    "user. After spawning a teammate, end the current turn instead of " +
    "polling its status; the runtime will deliver team events and wake the " +
    "Lead. React to those events, and shut teammates down when " +
    "coordination is complete.",
  workspace: `Working directory: ${WORKDIR}`,
};

const SYSTEM = Object.values(PROMPT_SECTIONS).join("\n\n");

// -- Base Tools --

function safePath(p: string, cwd?: string | null): string {
  const base = path.resolve(cwd ?? WORKDIR);
  const target = path.resolve(base, p);
  if (!isInside(target, base)) throw new Error(`Path escapes workspace: ${p}`);
  return target;
}

function runBash(command: string, cwd?: string | null): string {
  const r = spawnSync(command, {
    shell: true,
    cwd: cwd ?? WORKDIR,
    encoding: "utf8",
    timeout: 120_000,
    maxBuffer: 10 * 1024 * 1024,
  });
  if (r.error) {
    const code = (r.error as NodeJS.ErrnoException).code;
    if (code === "ETIMEDOUT") return "Error: Timeout (120s)";
    return `Error: ${code ?? "Error"}: ${r.error.message}`;
  }
  if (r.signal === "SIGTERM") return "Error: Timeout (120s)";
  let output = `${r.stdout ?? ""}${r.stderr ?? ""}`.trim();
  output = output ? output.slice(0, 50_000) : "(no output)";
  if (r.status) return `Error: command exited with status ${r.status}\n${output}`;
  return output;
}

function runRead(p: string, limit?: number | null, cwd?: string | null): string {
  try {
    let lines = splitLines(fs.readFileSync(safePath(p, cwd), "utf8"));
    if (limit && limit < lines.length) {
      lines = [...lines.slice(0, limit), `... (${lines.length - limit} more lines)`];
    }
    return lines.join("\n");
  } catch (error: any) {
    return `Error: ${error.message}`;
  }
}

function runWrite(p: string, content: string, cwd?: string | null): string {
  try {
    const target = safePath(p, cwd);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content, "utf8");
    return `Wrote ${content.length} bytes to ${p}`;
  } catch (error: any) {
    return `Error: ${error.message}`;
  }
}

function runEdit(
  p: string, oldText: string, newText: string, cwd?: string | null,
): string {
  try {
    const target = safePath(p, cwd);
    const content = fs.readFileSync(target, "utf8");
    const count = content.split(oldText).length - 1;
    if (count !== 1) return `Error: Expected 1 occurrence, found ${count}`;
    fs.writeFileSync(target, content.replace(oldText, newText), "utf8");
    return `Edited ${p}`;
  } catch (error: any) {
    return `Error: ${error.message}`;
  }
}

function runGlobTool(pattern: string, cwd?: string | null): string {
  try {
    const base = path.resolve(cwd ?? WORKDIR);
    const matches = fg
      .sync(pattern, { cwd: base, onlyFiles: false, dot: false })
      .filter((m) => isInside(path.resolve(base, m), base))
      .sort();
    const shown = matches.slice(0, 200);
    if (matches.length > 200) {
      shown.push("... (more matches omitted; narrow the pattern)");
    }
    return shown.join("\n") || "No files found";
  } catch (error: any) {
    return `Error: ${error.message}`;
  }
}

function agentCwd(): [string | null, string | null] {
  try {
    return [assignmentCwd("agent"), null];
  } catch (error: any) {
    return [null, `Error: Invalid task assignment: ${error.message}`];
  }
}

function runAgentBash({ command }: { command: string }): string {
  const [cwd, error] = agentCwd();
  return error || runBash(command, cwd);
}

function runAgentRead({ path: p, limit }: { path: string; limit?: number }): string {
  const [cwd, error] = agentCwd();
  return error || runRead(p, limit, cwd);
}

function runAgentWrite({ path: p, content }: { path: string; content: string }): string {
  const [cwd, error] = agentCwd();
  return error || runWrite(p, content, cwd);
}

function runAgentEdit(
  { path: p, old_text, new_text }: { path: string; old_text: string; new_text: string },
): string {
  const [cwd, error] = agentCwd();
  return error || runEdit(p, old_text, new_text, cwd);
}

function runAgentGlob({ pattern }: { pattern: string }): string {
  const [cwd, error] = agentCwd();
  return error || runGlobTool(pattern, cwd);
}

// -- Task Tools --

function runCreateTask(
  { subject, description = "" }: { subject: string; description?: string },
): string {
  const task = createTask(subject, description);
  console.log(`  \x1b[34m[create] ${task.subject}\x1b[0m`);
  return `Created ${task.id}: ${task.subject}`;
}

function runUpdateTask(
  { task_id, addBlockedBy }: { task_id: string; addBlockedBy: string[] },
): string {
  let task: Task;
  try {
    task = updateTask(task_id, addBlockedBy);
  } catch (error: any) {
    if (error?.code === "ENOENT") return `Error: Task ${task_id} not found`;
    return `Error: ${error.message}`;
  }
  const dependencies = task.blockedBy.join(", ") || "(none)";
  console.log(`  \x1b[34m[update] ${task.subject} blockedBy: ${dependencies}\x1b[0m`);
  return `Updated ${task.id} blockedBy: ${dependencies}`;
}

function runListTasks(): string {
  const tasks = listTasks();
  if (tasks.length === 0) return "No tasks. Use create_task to add some.";
  const ICONS: Record<string, string> = {
    pending: "[ ]", in_progress: "[~]", completed: "[x]",
  };
  return tasks
    .map((t) => {
      const icon = ICONS[t.status] ?? "[?]";
      const deps = t.blockedBy.length ? ` (blockedBy: ${t.blockedBy.join(", ")})` : "";
      const owner = t.owner ? ` [${t.owner}]` : "";
      const worktree = t.worktree ? ` (worktree: ${t.worktree})` : "";
      return `  ${icon} ${t.id}: ${t.subject} [${t.status}]${owner}${deps}${worktree}`;
    })
    .join("\n");
}

function runGetTask({ task_id }: { task_id: string }): string {
  try {
    return getTask(task_id);
  } catch (error: any) {
    if (error?.code === "ENOENT") return `Error: Task ${task_id} not found`;
    return `Error: ${error.message}`;
  }
}

function runClaimTask({ task_id }: { task_id: string }): string {
  try {
    return claimTask(task_id, "agent");
  } catch (error: any) {
    if (error?.code === "ENOENT") return `Error: Task ${task_id} not found`;
    return `Error: ${error.message}`;
  }
}

function runCompleteTask({ task_id }: { task_id: string }): string {
  try {
    return completeTask(task_id, "agent");
  } catch (error: any) {
    if (error?.code === "ENOENT") return `Error: Task ${task_id} not found`;
    return `Error: ${error.message}`;
  }
}

// -- MessageBus and Team Protocols --

const MAILBOX_DIR = path.join(WORKDIR, ".mailboxes");
const MAILBOX_ROOT = path.resolve(MAILBOX_DIR);
const VALID_AGENT_NAME = /^[A-Za-z0-9_-]{1,64}$/;
const RESERVED_TEAMMATE_NAMES = new Set(["lead", "agent"]);

function isValidAgentName(name: string): boolean {
  return VALID_AGENT_NAME.test(name);
}

type BusMessage = {
  from: string;
  to: string;
  content: string;
  type: string;
  ts: number;
  metadata: Record<string, any>;
};

/**
 * File mailboxes with destructive reads.
 * py 用 threading.Condition 做等待/唤醒；JS 单线程，改成轮询（见 waitForMessages）。
 */
class MessageBus {
  private mailboxPath(agent: string): string {
    if (!isValidAgentName(agent)) {
      throw new Error(`Invalid mailbox recipient: '${agent}'`);
    }
    const target = path.resolve(MAILBOX_DIR, `${agent}.jsonl`);
    if (!isInside(target, MAILBOX_ROOT)) {
      throw new Error(`Mailbox path escapes directory: '${agent}'`);
    }
    return target;
  }

  send(
    fromAgent: string, toAgent: string, content: string,
    msgType = "message", metadata: Record<string, any> | null = null,
  ): void {
    const msg: BusMessage = {
      from: fromAgent,
      to: toAgent,
      content,
      type: msgType,
      ts: Date.now() / 1000,
      metadata: metadata ?? {},
    };
    fs.mkdirSync(MAILBOX_DIR, { recursive: true });
    fs.appendFileSync(this.mailboxPath(toAgent), JSON.stringify(msg) + "\n", "utf8");
    console.log(`  [bus] ${fromAgent} -> ${toAgent}: (${msgType}) ${content.slice(0, 50)}`);
  }

  readInbox(agent: string): BusMessage[] {
    const inbox = this.mailboxPath(agent);
    if (!fs.existsSync(inbox)) return [];
    const msgs = fs
      .readFileSync(inbox, "utf8")
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => JSON.parse(line) as BusMessage);
    fs.unlinkSync(inbox);
    return msgs;
  }

  peek(agent: string): boolean {
    const inbox = this.mailboxPath(agent);
    return fs.existsSync(inbox) && fs.statSync(inbox).size > 0;
  }

  /** Block until the agent has messages or timeout expires. */
  async waitForMessages(agent: string, timeoutSeconds: number | null = null): Promise<BusMessage[]> {
    const deadline = timeoutSeconds === null ? null : Date.now() + timeoutSeconds * 1000;
    while (!this.peek(agent)) {
      if (deadline !== null && Date.now() >= deadline) return [];
      await sleep(50);
    }
    return this.readInbox(agent);
  }
}

const BUS = new MessageBus();

// working | waiting_approval | idle | stopping
const activeTeammates: Record<string, string> = {};
const planGates: Record<string, string> = {};
const planRequestIds: Record<string, string> = {};

type ProtocolState = {
  request_id: string;
  type: string;
  sender: string;
  target: string;
  status: string;
  payload: string;
  work_version: number | null;
  task_id: string | null;
  created_at: number;
};

const pendingRequests: Record<string, ProtocolState> = {};

function newRequestId(): string {
  while (true) {
    const requestId = `req_${String(Math.floor(Math.random() * 1_000_000)).padStart(6, "0")}`;
    if (!(requestId in pendingRequests)) return requestId;
  }
}

/** Match one protocol response to one pending request. */
function matchResponse(
  responseType: string, requestId: string, approve: boolean,
  fromAgent: string, toAgent: string,
): boolean {
  const state = pendingRequests[requestId];
  if (!state) {
    console.log(`  [protocol] unknown request_id: ${requestId}`);
    return false;
  }
  const expected = { shutdown: "shutdown_response", plan_approval: "plan_approval_response" }[
    state.type as "shutdown" | "plan_approval"
  ];
  if (responseType !== expected) {
    console.log(`  [protocol] expected ${expected}, got ${responseType}`);
    return false;
  }
  if (fromAgent !== state.target || toAgent !== state.sender) {
    console.log(`  [protocol] ${requestId} responder mismatch`);
    return false;
  }
  if (state.status !== "pending") {
    console.log(`  [protocol] ${requestId} already ${state.status}`);
    return false;
  }
  state.status = approve ? "approved" : "rejected";
  console.log(`  [protocol] ${requestId} -> ${state.status}`);
  return true;
}

/** Consume Lead events and update protocol state before model delivery. */
function consumeLeadInbox(): BusMessage[] {
  const msgs = BUS.readInbox("lead");
  for (const msg of msgs) {
    const metadata = msg.metadata ?? {};
    const requestId = metadata.request_id ?? "";
    if (requestId && (msg.type ?? "").endsWith("_response")) {
      matchResponse(msg.type, requestId, metadata.approve ?? false, msg.from ?? "", msg.to ?? "");
    }
  }
  return msgs;
}

function formatTeamEvents(msgs: BusMessage[]): string {
  const lines = msgs.map((msg) => {
    const requestId = (msg.metadata ?? {}).request_id;
    const suffix = requestId ? ` request_id=${requestId}` : "";
    return `[${msg.type}${suffix}] ${msg.from}: ${msg.content}`;
  });
  return "[Team events]\n" + lines.join("\n");
}

function lastAssistantText(content: any): string {
  for (const block of content) {
    if (block?.type === "text") return String(block.text ?? "").trim();
  }
  return "";
}

function currentWorkIdentity(owner: string): [number, string | null] {
  const assignment = teammateAssignments[owner];
  return [assignmentVersions[owner] ?? 0, assignment ? assignment.task_id : null];
}

function teammateSubmitPlan(fromName: string, plan: string): string {
  const assignment = teammateAssignments[fromName];
  const taskId = assignment ? assignment.task_id : null;
  const workVersion = assignmentVersions[fromName] ?? 0;

  if (planGates[fromName] === "pending") return "A plan is already waiting for review.";

  const requestId = newRequestId();
  pendingRequests[requestId] = {
    request_id: requestId,
    type: "plan_approval",
    sender: fromName,
    target: "lead",
    status: "pending",
    payload: plan,
    work_version: workVersion,
    task_id: taskId,
    created_at: Date.now() / 1000,
  };
  planGates[fromName] = "pending";
  planRequestIds[fromName] = requestId;
  activeTeammates[fromName] = "waiting_approval";

  BUS.send(fromName, "lead", plan, "plan_approval_request", { request_id: requestId });
  return `Plan submitted (${requestId}). Wait for Lead's decision.`;
}

async function runTeammateTool(
  name: string, block: any, handlers: Record<string, ToolHandler>,
): Promise<string> {
  const gate = planGates[name] ?? "not_required";
  if (["bash", "write_file", "edit_file"].includes(block.name)) {
    if (gate !== "approved") {
      if (gate !== "not_required") {
        return (
          `Blocked: plan status is ${gate}. Submit or revise the ` +
          "plan and wait for approval before changing the workspace."
        );
      }
    }
    const blocked = await checkPermission(block, false);
    if (blocked) return blocked;
  }
  const handler = handlers[block.name];
  if (!handler) return `Unknown tool: ${block.name}`;

  await triggerHooks("PreToolUse", [block], true);
  let output: string;
  try {
    output = String(await handler(block.input));
  } catch (error: any) {
    output = `Error: ${error?.constructor?.name ?? "Error"}: ${error.message}`;
  }
  await triggerHooks("PostToolUse", [block, output]);
  return output;
}

/** Apply only the Lead response for this teammate's current plan. */
function applyPlanResponse(name: string, msg: BusMessage): [boolean, string] {
  const metadata = msg.metadata ?? {};
  const requestId = metadata.request_id ?? "";
  const [workVersion, taskId] = currentWorkIdentity(name);

  const state = pendingRequests[requestId];
  const expectedId = planRequestIds[name];
  const valid =
    msg.from === "lead" &&
    msg.to === name &&
    requestId === expectedId &&
    state !== undefined &&
    state.type === "plan_approval" &&
    state.sender === name &&
    state.target === "lead" &&
    state.work_version === workVersion &&
    state.task_id === taskId &&
    ["approved", "rejected"].includes(state.status) &&
    (metadata.approve ?? false) === (state.status === "approved");

  if (!valid) return [false, "[Ignored plan response: request mismatch]"];

  planGates[name] = state.status;
  activeTeammates[name] = "working";
  delete planRequestIds[name];
  return [true, `[Plan ${state.status}] ${msg.content}`];
}

/** Accept only a pending shutdown request sent by Lead to this teammate. */
function applyShutdownRequest(name: string, msg: BusMessage): [boolean, string] {
  const requestId = (msg.metadata ?? {}).request_id ?? "";
  const state = pendingRequests[requestId];
  const valid =
    msg.from === "lead" &&
    msg.to === name &&
    state !== undefined &&
    state.type === "shutdown" &&
    state.sender === "lead" &&
    state.target === name &&
    state.status === "pending" &&
    activeTeammates[name] !== "stopping";

  if (!valid) return [false, "[Ignored shutdown request: request mismatch]"];
  activeTeammates[name] = "stopping";
  return [true, requestId];
}

function teammateSendMessage(fromName: string, to: string, content: string): string {
  if (to !== "lead" && !(to in activeTeammates)) return `Agent '${to}' is not active`;
  BUS.send(fromName, to, content);
  return `Sent to ${to}`;
}

// -- Idle Task Discovery --

const IDLE_SCAN_INTERVAL = 2.0;

/** Return ready tasks whose optional worktree binding is usable. */
function scanUnclaimedTasks(): Task[] {
  const ready: Task[] = [];
  for (const task of listTasks()) {
    if (task.status !== "pending" || task.owner !== null || !canStart(task.id)) continue;
    const [, error] = taskWorktreeCwd(task);
    if (!error) ready.push(task);
  }
  return ready;
}

/** Claim the first still-available task, never a second assignment. */
function claimNextTask(name: string): Task | null {
  if (teammateAssignments[name] || ownerInProgress(name)) return null;
  for (const task of scanUnclaimedTasks()) {
    const result = claimTask(task.id, name);
    if (result.startsWith("Claimed ")) return loadTask(task.id);
  }
  return null;
}

// -- Teammate Runtime --

/** One persistent teammate with separate messages and WORK/IDLE phases. */
class TeammateRuntime {
  name: string;
  system: string;
  messages: Msg[];
  handlers: Record<string, ToolHandler>;

  constructor(
    name: string, role: string, prompt: string,
    taskId: string | null, requirePlan: boolean,
  ) {
    this.name = name;
    this.system =
      `You are '${name}', a ${role}. Use tools to complete the assigned ` +
      "Task, then call complete_task and report a concise result. " +
      "If the first user message contains [Assigned task], that Task is " +
      "already claimed; do not call claim_task for it again. " +
      "When asked for a plan, call submit_plan and wait for approval " +
      "before bash or file changes. File and shell tools use the Task's " +
      "working directory; that directory is not a sandbox. The runtime " +
      "delivers your final text to Lead. Use send_message only for " +
      "intermediate coordination, and address the coordinator as 'lead'.";

    let content = prompt;
    if (taskId) {
      const task = loadTask(taskId);
      const cwd = assignmentCwd(name);
      content +=
        `\n\n[Assigned task ${task.id}] ${task.subject}\n` +
        `${task.description}\nWork directory: ${cwd}`;
    }
    if (requirePlan) {
      content +=
        "\n\n[Plan required] Submit a plan and wait for Lead approval " +
        "before changing files or using bash.";
    }
    this.messages = [{ role: "user", content }];

    this.handlers = {
      bash: ({ command }: any) => this.bash(command),
      read_file: ({ path: p, limit }: any) => this.read(p, limit),
      write_file: ({ path: p, content: c }: any) => this.write(p, c),
      edit_file: ({ path: p, old_text, new_text }: any) => this.edit(p, old_text, new_text),
      glob: ({ pattern }: any) => this.glob(pattern),
      send_message: ({ to, content: c }: any) => teammateSendMessage(name, to, c),
      submit_plan: ({ plan }: any) => teammateSubmitPlan(name, plan),
      list_tasks: () => runListTasks(),
      claim_task: ({ task_id }: any) => this.claim(task_id),
      complete_task: ({ task_id }: any) => this.complete(task_id),
    };
  }

  currentCwd(): [string | null, string | null] {
    if (!(this.name in teammateAssignments)) {
      return [null, "Error: Claim a Task before using workspace tools."];
    }
    try {
      return [assignmentCwd(this.name), null];
    } catch (error: any) {
      return [null, `Error: Invalid task assignment: ${error.message}`];
    }
  }

  bash(command: string): string {
    const [cwd, error] = this.currentCwd();
    return error || runBash(command, cwd);
  }

  read(p: string, limit?: number): string {
    const [cwd, error] = this.currentCwd();
    return error || runRead(p, limit, cwd);
  }

  write(p: string, content: string): string {
    const [cwd, error] = this.currentCwd();
    return error || runWrite(p, content, cwd);
  }

  edit(p: string, oldText: string, newText: string): string {
    const [cwd, error] = this.currentCwd();
    return error || runEdit(p, oldText, newText, cwd);
  }

  glob(pattern: string): string {
    const [cwd, error] = this.currentCwd();
    return error || runGlobTool(pattern, cwd);
  }

  claim(taskId: string): string {
    try {
      return claimTask(taskId, this.name);
    } catch (error: any) {
      if (error?.code === "ENOENT") return `Error: Task ${taskId} not found`;
      return `Error: ${error.message}`;
    }
  }

  complete(taskId: string): string {
    try {
      return completeTask(taskId, this.name);
    } catch (error: any) {
      if (error?.code === "ENOENT") return `Error: Task ${taskId} not found`;
      return `Error: ${error.message}`;
    }
  }

  /** Append work messages and return true for a valid shutdown. */
  handleInbox(inbox: BusMessage[]): boolean {
    const workMessages: string[] = [];
    for (const msg of inbox) {
      const msgType = msg.type ?? "message";
      if (msgType === "shutdown_request") {
        const [accepted, notice] = applyShutdownRequest(this.name, msg);
        if (!accepted) {
          workMessages.push(notice);
          continue;
        }
        BUS.send(this.name, "lead", "Shutdown acknowledged.", "shutdown_response", {
          request_id: notice, approve: true,
        });
        return true;
      }
      if (msgType === "plan_approval_response") {
        const [, notice] = applyPlanResponse(this.name, msg);
        workMessages.push(notice);
        continue;
      }
      if (msgType === "plan_request") {
        workMessages.push(`[Plan required] ${msg.content}`);
        continue;
      }
      workMessages.push(`[Message from ${msg.from}] ${msg.content}`);
    }
    if (workMessages.length > 0) {
      this.messages.push({ role: "user", content: workMessages.join("\n") });
    }
    return false;
  }

  /** Run one model turn. Return continue, idle, or stop. */
  async work(): Promise<string> {
    if (this.handleInbox(BUS.readInbox(this.name))) return "stop";
    activeTeammates[this.name] = "working";

    let response;
    try {
      response = await client.messages.create({
        model: MODEL,
        system: this.system,
        messages: this.messages as any,
        tools: TEAMMATE_TOOLS as any,
        max_tokens: 8000,
      });
    } catch (error: any) {
      BUS.send(
        this.name, "lead",
        `${error?.constructor?.name ?? "Error"}: ${error.message}`, "error",
      );
      return "stop";
    }

    this.messages.push({ role: "assistant", content: response.content });
    const toolCalls = response.content.filter((b: any) => b.type === "tool_use") as any[];

    if (toolCalls.length > 0) {
      const results: any[] = [];
      for (const block of toolCalls) {
        const output = await runTeammateTool(this.name, block, this.handlers);
        results.push({ type: "tool_result", tool_use_id: block.id, content: output });
      }
      this.messages.push({ role: "user", content: results });
      return "continue";
    }

    const summary = lastAssistantText(response.content);
    const gate = planGates[this.name] ?? "not_required";
    if (gate !== "pending" && summary) {
      BUS.send(this.name, "lead", summary, "result");
    }
    if (gate === "pending") {
      activeTeammates[this.name] = "waiting_approval";
    } else {
      releaseCompletedAssignment(this.name);
      activeTeammates[this.name] = "idle";
      BUS.send(this.name, "lead", "Waiting for more work.", "idle_notification");
    }
    return "idle";
  }

  /** Wait for a message or atomically claim the next ready Task. */
  async waitForWork(): Promise<boolean> {
    while (true) {
      const inbox = await BUS.waitForMessages(this.name, IDLE_SCAN_INTERVAL);
      if (inbox.length > 0) {
        const before = this.messages.length;
        if (this.handleInbox(inbox)) return false;
        if (this.messages.length > before) return true;
        continue;
      }

      const task = claimNextTask(this.name);
      if (!task) continue;
      const cwd = assignmentCwd(this.name);
      this.messages.push({
        role: "user",
        content:
          `[Auto-claimed task ${task.id}] ${task.subject}\n` +
          `${task.description}\nWork directory: ${cwd}`,
      });
      console.log(`  [idle] ${this.name} claimed ${task.id}: ${task.subject}`);
      return true;
    }
  }

  async run(): Promise<void> {
    try {
      let state = "continue";
      while (state !== "stop") {
        if (state === "idle" && !(await this.waitForWork())) break;
        state = await this.work();
      }
    } catch (error: any) {
      try {
        BUS.send(
          this.name, "lead",
          `${error?.constructor?.name ?? "Error"}: ${error.message}`, "error",
        );
      } catch {
        /* ignore */
      }
    } finally {
      try {
        releaseTeammateAssignment(this.name);
      } catch (error: any) {
        try {
          BUS.send(
            this.name, "lead",
            `Assignment cleanup failed: ${error?.constructor?.name ?? "Error"}: ${error.message}`,
            "error",
          );
        } catch {
          /* ignore */
        }
      }
      delete activeTeammates[this.name];
      delete planGates[this.name];
      delete planRequestIds[this.name];
      delete teammateRuntimes[this.name];
      console.log(`  [teammate] ${this.name} finished`);
    }
  }
}

// py: teammate_threads: dict[str, threading.Thread]
// ts: 没有线程对象可存，存 runtime 实例本身
const teammateRuntimes: Record<string, TeammateRuntime> = {};

/** Claim an initial Task, then start one persistent teammate. */
function spawnTeammate(
  name: string, role: string, prompt: string,
  taskId: string | null = null, requirePlan = false,
): string {
  if (!isValidAgentName(name)) {
    return "Invalid teammate name: use 1-64 letters, digits, underscores, or dashes";
  }
  if (RESERVED_TEAMMATE_NAMES.has(name.toLowerCase())) {
    return `Invalid teammate name: '${name}' is reserved by the runtime`;
  }
  if (Object.keys(activeTeammates).some((e) => e.toLowerCase() === name.toLowerCase())) {
    return `Teammate '${name}' already exists`;
  }

  activeTeammates[name] = "working";
  planGates[name] = requirePlan ? "required" : "not_required";
  assignmentVersions[name] = 0;

  if (taskId) {
    let claimed: string;
    try {
      claimed = claimTask(taskId, name);
    } catch (error: any) {
      claimed = `Error: ${error.message}`;
    }
    if (!claimed.startsWith("Claimed ")) {
      delete activeTeammates[name];
      delete planGates[name];
      delete assignmentVersions[name];
      return `Cannot spawn teammate '${name}': ${claimed}`;
    }
  }

  const runtime = new TeammateRuntime(name, role, prompt, taskId, requirePlan);
  teammateRuntimes[name] = runtime;
  // py: thread.start()  ->  ts: 不 await，交给事件循环
  void runtime.run();

  console.log(`  [teammate] ${name} spawned as ${role}`);
  const assigned = taskId ? ` for ${taskId}` : " without an initial Task";
  return (
    `Teammate '${name}' spawned as ${role}${assigned}. ` +
    "End this turn; the runtime will deliver its events."
  );
}

// -- Lead Team Tools --

function runSpawnTeammate(
  { name, role, prompt, task_id = null, require_plan = false }: any,
): string {
  return spawnTeammate(name, role, prompt, task_id, require_plan);
}

function runListTeammates(): string {
  const names = Object.keys(activeTeammates).sort();
  if (names.length === 0) return "No active teammates.";
  return names.map((name) => `${name}: ${activeTeammates[name]}`).join("\n");
}

function runSendMessage({ to, content }: { to: string; content: string }): string {
  if (!(to in activeTeammates)) return `Teammate '${to}' is not active`;
  BUS.send("lead", to, content);
  return `Sent to ${to}`;
}

function runRequestShutdown({ teammate }: { teammate: string }): string {
  if (!(teammate in activeTeammates)) return `Teammate '${teammate}' is not active`;
  const requestId = newRequestId();
  pendingRequests[requestId] = {
    request_id: requestId,
    type: "shutdown",
    sender: "lead",
    target: teammate,
    status: "pending",
    payload: "",
    work_version: null,
    task_id: null,
    created_at: Date.now() / 1000,
  };
  BUS.send("lead", teammate, "Finish the current step and shut down.", "shutdown_request", {
    request_id: requestId,
  });
  return `Shutdown requested from ${teammate} (${requestId})`;
}

function runRequestPlan({ teammate, task }: { teammate: string; task: string }): string {
  if (!(teammate in activeTeammates)) return `Teammate '${teammate}' is not active`;
  planGates[teammate] = "required";
  BUS.send("lead", teammate, task, "plan_request");
  return `Plan requested from ${teammate}`;
}

function runReviewPlan(
  { request_id, approve, feedback = "" }: { request_id: string; approve: boolean; feedback?: string },
): string {
  const state = pendingRequests[request_id];
  if (!state) return `Request ${request_id} not found`;

  const [workVersion, taskId] = currentWorkIdentity(state.sender);
  if (state.type !== "plan_approval") return `Request ${request_id} is not a plan`;
  if (state.status !== "pending") return `Request ${request_id} already ${state.status}`;
  if (state.work_version !== workVersion || state.task_id !== taskId) {
    return `Request ${request_id} belongs to an earlier assignment`;
  }
  if (planRequestIds[state.sender] !== request_id) {
    return `Request ${request_id} is not the current plan`;
  }
  state.status = approve ? "approved" : "rejected";

  const content = feedback || (approve ? "Plan approved." : "Revise the plan and submit it again.");
  BUS.send("lead", state.sender, content, "plan_approval_response", {
    request_id, approve,
  });
  return `Plan ${state.status} (${request_id})`;
}

function runCreateWorktree({ name, task_id }: { name: string; task_id: string }): string {
  return createWorktree(name, task_id);
}

// -- Tool Definitions --

const BASE_TOOLS = [
  { name: "bash", description: "Run a shell command.",
    input_schema: { type: "object" as const, properties: { command: { type: "string" } }, required: ["command"] } },
  { name: "read_file", description: "Read file contents.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, limit: { type: "integer" } }, required: ["path"] } },
  { name: "write_file", description: "Write content to a file.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, content: { type: "string" } }, required: ["path", "content"] } },
  { name: "edit_file", description: "Replace exact text once.",
    input_schema: { type: "object" as const, properties: { path: { type: "string" }, old_text: { type: "string" }, new_text: { type: "string" } }, required: ["path", "old_text", "new_text"] } },
  { name: "glob", description: "Find files by glob pattern; ** matches recursively.",
    input_schema: { type: "object" as const, properties: { pattern: { type: "string" } }, required: ["pattern"] } },
];

const TASK_TOOLS = [
  { name: "create_task", description: "Create a task and return its runtime-generated ID.",
    input_schema: { type: "object" as const, properties: { subject: { type: "string" }, description: { type: "string" } }, required: ["subject"], additionalProperties: false } },
  { name: "update_task", description: "Add dependencies using IDs returned by create_task.",
    input_schema: { type: "object" as const, properties: { task_id: { type: "string", pattern: "^task_[0-9a-f]{8}$" }, addBlockedBy: { type: "array", items: { type: "string", pattern: "^task_[0-9a-f]{8}$" }, minItems: 1 } }, required: ["task_id", "addBlockedBy"], additionalProperties: false } },
  { name: "list_tasks", description: "List shared tasks.",
    input_schema: { type: "object" as const, properties: {} } },
  { name: "get_task", description: "Get one task by ID.",
    input_schema: { type: "object" as const, properties: { task_id: { type: "string" } }, required: ["task_id"] } },
  { name: "claim_task", description: "Claim a ready task.",
    input_schema: { type: "object" as const, properties: { task_id: { type: "string" } }, required: ["task_id"] } },
  { name: "complete_task", description: "Complete an owned task.",
    input_schema: { type: "object" as const, properties: { task_id: { type: "string" } }, required: ["task_id"] } },
];

const TEAMMATE_TOOLS = [
  ...BASE_TOOLS,
  { name: "send_message", description: "Send an intermediate message to 'lead' or an active teammate.",
    input_schema: { type: "object" as const, properties: { to: { type: "string" }, content: { type: "string" } }, required: ["to", "content"] } },
  { name: "submit_plan", description: "Submit a work plan for Lead approval.",
    input_schema: { type: "object" as const, properties: { plan: { type: "string" } }, required: ["plan"] } },
  TASK_TOOLS.find((t) => t.name === "list_tasks")!,
  TASK_TOOLS.find((t) => t.name === "claim_task")!,
  TASK_TOOLS.find((t) => t.name === "complete_task")!,
];

const TEAM_TOOLS = [
  { name: "spawn_teammate", description: "Spawn a persistent teammate.",
    input_schema: { type: "object" as const, properties: { name: { type: "string", pattern: "^[A-Za-z0-9_-]{1,64}$" }, role: { type: "string" }, prompt: { type: "string" }, task_id: { type: "string", pattern: "^task_[0-9a-f]{8}$" }, require_plan: { type: "boolean" } }, required: ["name", "role", "prompt"] } },
  { name: "list_teammates", description: "List active teammates.",
    input_schema: { type: "object" as const, properties: {} } },
  { name: "send_message", description: "Message a teammate.",
    input_schema: { type: "object" as const, properties: { to: { type: "string" }, content: { type: "string" } }, required: ["to", "content"] } },
  { name: "request_shutdown", description: "Ask a teammate to shut down.",
    input_schema: { type: "object" as const, properties: { teammate: { type: "string" } }, required: ["teammate"] } },
  { name: "request_plan", description: "Require a teammate plan before workspace changes.",
    input_schema: { type: "object" as const, properties: { teammate: { type: "string" }, task: { type: "string" } }, required: ["teammate", "task"] } },
  { name: "review_plan", description: "Approve or reject a plan.",
    input_schema: { type: "object" as const, properties: { request_id: { type: "string" }, approve: { type: "boolean" }, feedback: { type: "string" } }, required: ["request_id", "approve"] } },
  { name: "create_worktree", description: "Create and bind a task worktree.",
    input_schema: { type: "object" as const, properties: { name: { type: "string", pattern: "^(?!.*\\.\\.)[A-Za-z0-9][A-Za-z0-9._-]{0,63}$", maxLength: 64 }, task_id: { type: "string" } }, required: ["name", "task_id"], additionalProperties: false } },
];

const TOOLS = [...BASE_TOOLS, ...TASK_TOOLS, ...TEAM_TOOLS];

type Msg = { role: "user" | "assistant"; content: any };
type ToolHandler = (args: any) => string | Promise<string>;

const TOOL_HANDLERS: Record<string, ToolHandler> = {
  bash: runAgentBash,
  read_file: runAgentRead,
  write_file: runAgentWrite,
  edit_file: runAgentEdit,
  glob: runAgentGlob,
  create_task: runCreateTask,
  update_task: runUpdateTask,
  list_tasks: runListTasks,
  get_task: runGetTask,
  claim_task: runClaimTask,
  complete_task: runCompleteTask,
  spawn_teammate: runSpawnTeammate,
  list_teammates: runListTeammates,
  send_message: runSendMessage,
  request_shutdown: runRequestShutdown,
  request_plan: runRequestPlan,
  review_plan: runReviewPlan,
  create_worktree: runCreateWorktree,
};

// -- Hooks and Permission Checks --

type HookResult = string | null;
type Hook = (...args: any[]) => HookResult | Promise<HookResult>;

const HOOKS: Record<string, Hook[]> = {
  UserPromptSubmit: [], PreToolUse: [], PostToolUse: [], Stop: [],
};
const DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="];
const DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"];

function registerHook(event: string, callback: Hook): void {
  HOOKS[event].push(callback);
}

// py 用关键字参数 skip_permission；TS 放在第三个位置参数上
async function triggerHooks(
  event: string, args: any[] = [], skipPermission = false,
): Promise<HookResult> {
  for (const callback of HOOKS[event]) {
    if (skipPermission && callback === permissionHook) continue;
    const result = await callback(...args);
    if (result !== null && result !== undefined) return result;
  }
  return null;
}

async function checkPermission(block: any, promptUser = true): Promise<string | null> {
  if (block.name === "bash") {
    const command = block.input.command ?? "";
    for (const pattern of DENY_LIST) {
      if (command.includes(pattern)) return `Permission denied by deny list: ${pattern}`;
    }
    if (DESTRUCTIVE.some((keyword) => command.includes(keyword))) {
      if (!promptUser) return "Permission required: ask Lead to run this command.";
      console.log(`\n[permission] ${block.name}(${JSON.stringify(block.input)})`);
      const choice = (await rl.question("Allow? [y/N] ")).trim().toLowerCase();
      if (!["y", "yes"].includes(choice)) return "Permission denied by user";
    }
  }

  if (["read_file", "write_file", "edit_file"].includes(block.name)) {
    const rawPath = block.input.path ?? "";
    if (!isInside(path.resolve(WORKDIR, rawPath), path.resolve(WORKDIR))) {
      if (!promptUser) return "Permission required: path is outside the workspace.";
      console.log(`\n[permission] ${block.name}(${JSON.stringify(block.input)})`);
      const choice = (await rl.question("Allow? [y/N] ")).trim().toLowerCase();
      if (!["y", "yes"].includes(choice)) return "Permission denied by user";
    }
  }
  return null;
}

async function permissionHook(block: any): Promise<HookResult> {
  return checkPermission(block, true);
}

function logHook(block: any): HookResult {
  const preview = JSON.stringify(Object.values(block.input).slice(0, 2)).slice(0, 60);
  console.log(`[hook] ${block.name}(${preview})`);
  return null;
}

function largeOutputHook(block: any, output: any): HookResult {
  if (String(output).length > 100_000) {
    console.log(`[hook] Large output from ${block.name}: ${String(output).length} chars`);
  }
  return null;
}

function contextHook(_query: string): HookResult {
  console.log(`[hook] UserPromptSubmit: working in ${WORKDIR}`);
  return null;
}

function summaryHook(messages: Msg[]): HookResult {
  let toolCount = 0;
  for (const message of messages) {
    if (!Array.isArray(message.content)) continue;
    for (const block of message.content) {
      if (block && typeof block === "object" && block.type === "tool_result") toolCount += 1;
    }
  }
  console.log(`[hook] Stop: session used ${toolCount} tool calls`);
  return null;
}

registerHook("UserPromptSubmit", contextHook);
registerHook("PreToolUse", permissionHook);
registerHook("PreToolUse", logHook);
registerHook("PostToolUse", largeOutputHook);
registerHook("Stop", summaryHook);

async function executeTool(block: any): Promise<string> {
  const blocked = await triggerHooks("PreToolUse", [block]);
  if (blocked) return String(blocked);
  const handler = TOOL_HANDLERS[block.name];
  if (!handler) return `Unknown tool: ${block.name}`;
  let output: string;
  try {
    output = String(await handler(block.input));
  } catch (error: any) {
    output = `Error: ${error?.constructor?.name ?? "Error"}: ${error.message}`;
  }
  await triggerHooks("PostToolUse", [block, output]);
  return output;
}

// -- The Lead loop --

const rl = createInterface({ input: process.stdin, output: process.stdout });

async function agentLoop(messages: Msg[]): Promise<void> {
  while (true) {
    let response;
    try {
      response = await client.messages.create({
        model: MODEL,
        system: SYSTEM,
        messages: messages as any,
        tools: TOOLS as any,
        max_tokens: 8000,
      });
    } catch (error: any) {
      messages.push({
        role: "assistant",
        content: [{
          type: "text",
          text: `[Error] ${error?.constructor?.name ?? "Error"}: ${error.message}`,
        }],
      });
      releaseCompletedAssignment("agent");
      await triggerHooks("Stop", [messages]);
      return;
    }

    messages.push({ role: "assistant", content: response.content });
    const toolCalls = response.content.filter((b: any) => b.type === "tool_use") as any[];
    if (toolCalls.length === 0) {
      releaseCompletedAssignment("agent");
      await triggerHooks("Stop", [messages]);
      return;
    }

    const results: any[] = [];
    for (const block of toolCalls) {
      console.log(`> ${block.name}`);
      const output = await executeTool(block);
      console.log(output.slice(0, 300));
      results.push({ type: "tool_result", tool_use_id: block.id, content: output });
    }
    messages.push({ role: "user", content: results });
  }
}

function printLastAssistantMessage(history: Msg[]): void {
  if (history.length === 0) return;
  const content = history[history.length - 1].content;
  if (!Array.isArray(content)) return;
  for (const block of content) {
    if (block?.type === "text") console.log(block.text ?? "");
  }
}

/**
 * py 用 select.select([sys.stdin], [], [], 0.25) 同时等 stdin 和邮箱。
 * TS 用可中断的 rl.question：邮箱有信时 abort 掉输入等待。
 */
async function waitForCliEvent(): Promise<[string, string | null]> {
  if (BUS.peek("lead")) return ["wake", null];

  const controller = new AbortController();
  let woken = false;

  const poller = (async () => {
    while (!controller.signal.aborted) {
      if (BUS.peek("lead")) {
        woken = true;
        controller.abort();
        return;
      }
      await sleep(250);
    }
  })();

  try {
    const line = await rl.question("s13 >> ", { signal: controller.signal });
    controller.abort();
    await poller;
    return ["user", line];
  } catch {
    await poller;
    if (woken) {
      console.log();
      return ["wake", null];
    }
    return ["quit", null];
  }
}

console.log("s13: agent teams");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];
let hadTeammates = false;

while (true) {
  const [kind, payload] = await waitForCliEvent();
  if (kind === "quit") break;

  if (kind === "user") {
    if (payload === null || ["q", "exit", ""].includes(payload.trim().toLowerCase())) break;
    await triggerHooks("UserPromptSubmit", [payload]);
    history.push({ role: "user", content: payload });
  } else {
    const inbox = consumeLeadInbox();
    if (inbox.length === 0) continue;
    history.push({ role: "user", content: formatTeamEvents(inbox) });
    console.log(`[wake: ${inbox.length} team event(s) -> new turn]`);
  }

  await agentLoop(history);
  printLastAssistantMessage(history);

  if (Object.keys(activeTeammates).length > 0) {
    hadTeammates = true;
  } else if (hadTeammates && !BUS.peek("lead")) {
    console.log("[all teammates shut down]");
    hadTeammates = false;
  }
  console.log();
}

rl.close();
process.exit(0);
