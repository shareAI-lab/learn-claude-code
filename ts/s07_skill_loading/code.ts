/**
 * s07_skill_loading.ts - Skill Loading
 *
 * TypeScript 1:1 port of s07_skill_loading/code.py
 *
 * The system prompt contains a catalog of skill names and descriptions.
 * The model loads the full SKILL.md only when it calls load_skill.
 *
 *     skills/                    Startup
 *     +------------------+       +------------------+
 *     | code-review/     | ----> | SkillLoader      |
 *     |   SKILL.md       |       | name + summary   |
 *     | pdf/             |       +--------+---------+
 *     |   SKILL.md       |                |
 *     +------------------+                v
 *                                  system prompt catalog
 *
 *     LLM -- load_skill(name) --> full SKILL.md
 *      ^                              |
 *      +--------- tool_result --------+
 *
 * 注意：SKILLS_DIR = WORKDIR/skills，也就是**按运行时的当前目录**去找技能。
 * 所以必须在仓库根目录运行，否则 catalog 是空的。`npm run s07` 已经帮你 cd 过去了。
 *
 * TS-vs-Python 差异（本章新增两处）:
 *   1. pyyaml -> yaml 包（yaml.safe_load -> YAML.parse）
 *   2. py 里 `"load_skill": SKILL_LOADER.load` 传的是**绑定方法**，this 自动带着；
 *      TS 里直接传 SKILL_LOADER.load 会丢 this，必须包一层箭头函数。
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s07
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline/promises";

import Anthropic from "@anthropic-ai/sdk";
import dotenv from "dotenv";
import fg from "fast-glob";
import YAML from "yaml";

const HERE = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(HERE, "../../.env"), override: true, quiet: true });

if (process.env.ANTHROPIC_BASE_URL) {
    delete process.env.ANTHROPIC_AUTH_TOKEN;
}

const WORKDIR = process.cwd();
const SKILLS_DIR = path.join(WORKDIR, "skills");
const client = new Anthropic({ baseURL: process.env.ANTHROPIC_BASE_URL });
const MODEL: string = process.env.MODEL_ID ?? "";
if (!MODEL) throw new Error("MODEL_ID is required (see .env)");

const rl = createInterface({ input: process.stdin, output: process.stdout });

// -- Skill catalog --

type Skill = { name: string; description: string; content: string };

class SkillLoader {
    skillsDir: string;
    skills: Record<string, Skill> = {};

    constructor(skillsDir: string) {
        this.skillsDir = skillsDir;
        this.scan();
    }

    // py: @staticmethod parse_frontmatter -> tuple[dict, str]
    // TS 没有多返回值，返回一个对象
    static parseFrontmatter(text: string): { metadata: any; body: string } {
        const lines = text.split(/\r?\n/);
        if (lines.length === 0 || lines[0] !== "---") {
            return { metadata: {}, body: text };
        }

        // 找收尾的那一行 ---（从第 2 行开始找）
        let closingIndex = -1;
        for (let i = 1; i < lines.length; i++) {
            if (lines[i] === "---") {
                closingIndex = i;
                break;
            }
        }
        if (closingIndex === -1) return { metadata: {}, body: text };

        const frontmatter = lines.slice(1, closingIndex).join("\n");
        const body = lines.slice(closingIndex + 1).join("\n").trim();

        let metadata: any = {};
        try {
            metadata = YAML.parse(frontmatter) ?? {};
        } catch {
            metadata = {};
        }
        if (typeof metadata !== "object" || metadata === null || Array.isArray(metadata)) {
            metadata = {};
        }
        return { metadata, body };
    }

    scan(): void {
        this.skills = {};
        if (!fs.existsSync(this.skillsDir)) return;

        // py 的 Path.resolve() 跟随符号链接，path.resolve() 不跟随
        const skillsRoot = fs.realpathSync(this.skillsDir);
        const manifests = fg
            .sync("*/SKILL.md", { cwd: skillsRoot, onlyFiles: true })
            .sort();

        for (const rel of manifests) {
            const manifest = path.resolve(skillsRoot, rel);
            // 和 py 一样再确认一次没跑出 skills/ 之外（符号链接）
            const real = fs.realpathSync(manifest);
            if (!(real === skillsRoot || real.startsWith(skillsRoot + path.sep))) continue;

            const content = fs.readFileSync(manifest, "utf8");
            const { metadata, body } = SkillLoader.parseFrontmatter(content);

            const rawName = metadata.name;
            let name = typeof rawName === "string" ? rawName.trim() : "";
            name = name || path.basename(path.dirname(manifest));

            const rawDescription = metadata.description;
            let description =
                typeof rawDescription === "string" ? rawDescription.trim() : "";
            description = description || body.split("\n", 1)[0];
            // py: " ".join(str(description).lstrip("# ").split())
            description = String(description)
                .replace(/^[#\s]+/, "")
                .split(/\s+/)
                .filter(Boolean)
                .join(" ");

            this.skills[name] = { name, description, content };
        }
    }

    catalog(): string {
        const values = Object.values(this.skills);
        if (values.length === 0) return "(no skills found)";
        return values.map((skill) => `- ${skill.name}: ${skill.description}`).join("\n");
    }

    load(name: string): string {
        const skill = this.skills[name];
        if (skill) return skill.content;
        const available = Object.keys(this.skills).join(", ") || "none";
        return `Error: Unknown skill '${name}'. Available: ${available}`;
    }
}

const SKILL_LOADER = new SkillLoader(SKILLS_DIR);

// py: str.splitlines() —— 末尾换行**不会**多产生一个空元素，JS 的 split 会。
// 不修的话行数和 "N more lines" 都会差 1。
function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\n|\r/);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

function buildSystemPrompt(): string {
    return (
        `You are a coding agent at ${WORKDIR}. Use tools to solve tasks. ` +
        "Act, don't explain.\n\n" +
        `Skills available:\n${SKILL_LOADER.catalog()}\n\n` +
        "Use load_skill to read the full instructions when a skill applies."
    );
}

const SYSTEM = buildSystemPrompt();

// -- Tools --

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
    // s07: new tool
    {
        name: "load_skill", description: "Load the full SKILL.md content by skill name.",
        input_schema: { type: "object" as const, properties: { name: { type: "string" } }, required: ["name"] }
    },
];

const TOOL_HANDLERS: Record<string, ToolHandler> = {
    bash: runBash,
    read_file: runRead,
    write_file: runWrite,
    edit_file: runEdit,
    glob: runGlob,
    // py 里可以直接写 SKILL_LOADER.load（绑定方法自带 this）；
    // TS 里裸传方法引用会丢 this，必须包一层。
    load_skill: ({ name }: { name: string }) => SKILL_LOADER.load(name),
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

async function executeTool(block: any): Promise<string> {
    const blocked = await triggerHooks("PreToolUse", block);
    if (blocked) return String(blocked);

    const handler = TOOL_HANDLERS[block.name];
    let output: string;
    try {
        output = handler ? await handler(block.input) : `Unknown: ${block.name}`;
    } catch (e: any) {
        output = `Error: ${e.message}`;
    }

    await triggerHooks("PostToolUse", block, output);
    return String(output);
}

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
            results.push({
                type: "tool_result",
                tool_use_id: block.id,
                content: output,
            });
        }
        messages.push({ role: "user", content: results });
    }
}

console.log("s07: Skill Loading - catalog first, full content on demand");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("\x1b[36ms07 >> \x1b[0m");
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
