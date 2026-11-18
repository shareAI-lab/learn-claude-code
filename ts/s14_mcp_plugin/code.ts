/**
 * s14: MCP Tools - discover external tools and add them to the agent loop.
 *
 * TypeScript 1:1 port of s14_mcp_plugin/code.py
 *
 *     connectMcp("docs")
 *               |
 *               v
 *     +------------------+     tools/list     +------------------+
 *     | Agent Harness    | <----------------- | MCP server       |
 *     |                  |                    | docs             |
 *     | built-in tools   |     tools/call     |                  |
 *     | + MCP tools      | -----------------> | search           |
 *     +--------+---------+                    | get_version      |
 *              |                              +------------------+
 *              v
 *     +-----------------------------------------------+
 *     | bash | read | write | edit | glob | connect  |
 *     | mcp__docs__search | mcp__docs__get_version   |
 *     +-----------------------------------------------+
 *
 * 注意：这一章的 MCP 服务器是**进程内 mock**，不是真的 JSON-RPC over stdio。
 * 教的是"工具池怎么被外部来源动态填充"，不是 MCP 协议本身。
 *
 * TS-vs-Python 差异（本章新增两处）:
 *
 *   1. 闭包捕获循环变量：py 需要技巧，JS 不需要
 *      py:  handlers[prefixed] = (lambda *, client=server, tool=raw_name,
 *                                 **kwargs: client.call_tool(tool, kwargs))
 *           ^ 必须用默认参数把 server / raw_name 绑死，否则所有闭包都会看到
 *             循环结束后的最后一个值（Python 的 late binding）
 *      ts:  const 在 for-of 每轮是**新的绑定**，直接写箭头函数就对
 *
 *   2. 元组键 -> 字符串键
 *      py:  MCP_HOST_POLICY = {("docs", "search"): "allow", ...}
 *      ts:  JS 对象/Map 不做元组值比较，键拼成 "docs/search"
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s14
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

const BASE_SYSTEM =
    `You are a coding agent at ${WORKDIR}. Use built-in and connected MCP ` +
    "tools to solve tasks. Call connect_mcp before using a server.";

const isInside = (target: string, root: string) =>
    target === root || target.startsWith(root + path.sep);

// -- From s04: base tools --

type ToolHandler = (args: any) => string | Promise<string>;

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
        return `Error: ${code ?? "Error"}: ${r.error.message}`;
    }
    if (r.signal === "SIGTERM") return "Error: Timeout (120s)";
    let output = `${r.stdout ?? ""}${r.stderr ?? ""}`.trim();
    output = output ? output.slice(0, 50_000) : "(no output)";
    if (r.status) return `Error: command exited with status ${r.status}\n${output}`;
    return output;
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
        const target = path.resolve(WORKDIR, p);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, content, "utf8");
        return `Wrote ${content.length} bytes to ${p}`;
    } catch (error: any) {
        return `Error: ${error.message}`;
    }
}

function runEdit(
    { path: p, old_text, new_text }: { path: string; old_text: string; new_text: string },
): string {
    try {
        const target = path.resolve(WORKDIR, p);
        const content = fs.readFileSync(target, "utf8");
        const count = content.split(old_text).length - 1;
        if (count !== 1) return `Error: Expected 1 occurrence, found ${count}`;
        fs.writeFileSync(target, content.replace(old_text, new_text), "utf8");
        return `Edited ${p}`;
    } catch (error: any) {
        return `Error: ${error.message}`;
    }
}

function runGlobTool({ pattern }: { pattern: string }): string {
    try {
        const matches = [
            ...new Set(
                fg
                    .sync(pattern, { cwd: WORKDIR, dot: false, onlyFiles: false })
                    .filter((m) => isInside(path.resolve(WORKDIR, m), path.resolve(WORKDIR))),
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

const BASE_TOOLS = [
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
        name: "edit_file", description: "Replace exact text once.",
        input_schema: { type: "object" as const, properties: { path: { type: "string" }, old_text: { type: "string" }, new_text: { type: "string" } }, required: ["path", "old_text", "new_text"] }
    },
    {
        name: "glob", description: "Find files by glob pattern; ** matches recursively.",
        input_schema: { type: "object" as const, properties: { pattern: { type: "string" } }, required: ["pattern"] }
    },
];

const BASE_HANDLERS: Record<string, ToolHandler> = {
    bash: runBash,
    read_file: runRead,
    write_file: runWrite,
    edit_file: runEdit,
    glob: runGlobTool,
};

// -- New in s14: MCP discovery and dispatch --

type McpToolDef = {
    name: string;
    description?: string;
    inputSchema?: any;
    annotations?: Record<string, any>;
};

/** Small in-process stand-in for MCP tools/list and tools/call. */
class MCPClient {
    name: string;
    tools: McpToolDef[] = [];
    private handlers: Record<string, ToolHandler> = {};

    constructor(name: string) {
        this.name = name;
    }

    register(toolDefs: McpToolDef[], handlers: Record<string, ToolHandler>): void {
        const names = toolDefs.map((tool) => tool.name);
        if (names.some((name) => typeof name !== "string" || !name)) {
            throw new Error("Every MCP tool needs a non-empty name");
        }
        if (new Set(names).size !== names.length) {
            throw new Error(`Duplicate MCP tool name on server '${this.name}'`);
        }
        const missing = names.filter((name) => !(name in handlers));
        if (missing.length > 0) {
            throw new Error(`Missing MCP handlers: ${missing.join(", ")}`);
        }
        this.tools = [...toolDefs];
        this.handlers = { ...handlers };
    }

    callTool(toolName: string, args: any): string {
        const handler = this.handlers[toolName];
        if (!handler) return `MCP error: unknown tool '${toolName}'`;
        try {
            return String(handler(args));
        } catch (error: any) {
            return `MCP error: ${error?.constructor?.name ?? "Error"}: ${error.message}`;
        }
    }
}

const mcpClients: Record<string, MCPClient> = {};
let mcpToolPolicies: Record<string, string> = {};
const DISALLOWED_CHARS = /[^a-zA-Z0-9_-]/g;

// Authorization comes from host configuration, never server descriptions.
// py 用元组键 ("docs", "search")；JS 拼成字符串键
const MCP_HOST_POLICY: Record<string, string> = {
    "docs/search": "allow",
    "docs/get_version": "allow",
    "deploy/status": "allow",
    "deploy/trigger": "confirm",
};

/** Replace characters outside the model tool-name alphabet. */
function normalizeMcpName(name: string): string {
    const normalized = name.replace(DISALLOWED_CHARS, "_");
    if (!normalized) throw new Error("MCP names cannot normalize to an empty string");
    return normalized;
}

function mockServerDocs(): MCPClient {
    const server = new MCPClient("docs");
    server.register(
        [
            {
                name: "search",
                description: "Search the documentation.",
                inputSchema: {
                    type: "object",
                    properties: { query: { type: "string" } },
                    required: ["query"],
                },
                annotations: { readOnlyHint: true },
            },
            {
                name: "get_version",
                description: "Get the documentation API version.",
                inputSchema: { type: "object", properties: {} },
                annotations: { readOnlyHint: true },
            },
        ],
        {
            search: ({ query }: any) => `[docs] Found 3 results for '${query}'`,
            get_version: () => "[docs] API v2.1.0",
        },
    );
    return server;
}

function mockServerDeploy(): MCPClient {
    const server = new MCPClient("deploy");
    server.register(
        [
            {
                name: "trigger",
                description: "Trigger a deployment.",
                inputSchema: {
                    type: "object",
                    properties: { service: { type: "string" } },
                    required: ["service"],
                },
                annotations: { destructiveHint: true },
            },
            {
                name: "status",
                description: "Check deployment status.",
                inputSchema: {
                    type: "object",
                    properties: { service: { type: "string" } },
                    required: ["service"],
                },
                annotations: { readOnlyHint: true },
            },
        ],
        {
            trigger: ({ service }: any) => `[deploy] Triggered: ${service}`,
            status: ({ service }: any) => `[deploy] ${service}: running (v1.4.2)`,
        },
    );
    return server;
}

const MOCK_SERVERS: Record<string, () => MCPClient> = {
    docs: mockServerDocs,
    deploy: mockServerDeploy,
};

function connectMcp(name: string): string {
    if (name in mcpClients) return `MCP server '${name}' already connected`;
    const factory = MOCK_SERVERS[name];
    if (!factory) {
        return `Unknown server '${name}'. Available: ${Object.keys(MOCK_SERVERS).join(", ")}`;
    }
    const server = factory();
    mcpClients[name] = server;
    const names = server.tools.map((tool) => tool.name).join(", ");
    console.log(`  [mcp] connected: ${name} -> ${names}`);
    return (
        `Connected to MCP server '${name}'. ` +
        `Discovered ${server.tools.length} tools: ${names}`
    );
}

function runConnectMcp({ name }: { name: string }): string {
    return connectMcp(name);
}

const CONNECT_TOOL = {
    name: "connect_mcp",
    description: "Connect to an MCP server and discover its tools.",
    input_schema: {
        type: "object" as const,
        properties: { name: { type: "string", enum: ["docs", "deploy"] } },
        required: ["name"],
    },
};

const BUILTIN_TOOLS = [...BASE_TOOLS, CONNECT_TOOL];
const BUILTIN_HANDLERS: Record<string, ToolHandler> = {
    ...BASE_HANDLERS,
    connect_mcp: runConnectMcp,
};

/** Combine built-in tools with every connected server tool. */
function assembleToolPool(): [any[], Record<string, ToolHandler>] {
    const tools: any[] = [...BUILTIN_TOOLS];
    const handlers: Record<string, ToolHandler> = { ...BUILTIN_HANDLERS };
    const policies: Record<string, string> = {};
    const origins: Record<string, string> = {};
    for (const tool of tools) origins[tool.name] = `built-in tool '${tool.name}'`;

    for (const [serverName, server] of Object.entries(mcpClients)) {
        const safeServer = normalizeMcpName(serverName);
        for (const toolDef of server.tools) {
            const rawName = toolDef.name;
            const safeTool = normalizeMcpName(rawName);
            const prefixed = `mcp__${safeServer}__${safeTool}`;
            if (prefixed.length > 64) {
                throw new Error(`MCP tool name is longer than 64 characters: ${prefixed}`);
            }
            const origin = `MCP tool '${serverName}'/'${rawName}'`;
            if (prefixed in origins) {
                throw new Error(
                    "MCP tool name collision after normalization: " +
                    `'${prefixed}' maps both ${origins[prefixed]} and ${origin}`,
                );
            }
            const schema = toolDef.inputSchema ?? {};
            if (
                typeof schema !== "object" || schema === null || Array.isArray(schema) ||
                (schema.type ?? "object") !== "object"
            ) {
                throw new Error(`Invalid input schema for ${origin}`);
            }
            origins[prefixed] = origin;
            tools.push({
                name: prefixed,
                description: toolDef.description ?? "",
                input_schema: schema,
            });
            // py 必须用默认参数把 server/rawName 绑死（late binding）；
            // JS 的 for-of + const 每轮是新绑定，直接闭包就对。
            handlers[prefixed] = (args: any) => server.callTool(rawName, args);
            policies[prefixed] = MCP_HOST_POLICY[`${serverName}/${rawName}`] ?? "confirm";
        }
    }

    mcpToolPolicies = policies;
    return [tools, handlers];
}

function assembleSystemPrompt(): string {
    const names = Object.keys(mcpClients);
    if (names.length === 0) return BASE_SYSTEM;
    return BASE_SYSTEM + "\n\nConnected MCP servers: " + names.join(", ");
}

// -- From s04: hooks and permission checks --

type Msg = { role: "user" | "assistant"; content: any };
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

async function triggerHooks(event: string, ...args: any[]): Promise<HookResult> {
    for (const callback of HOOKS[event]) {
        const result = await callback(...args);
        if (result !== null && result !== undefined) return result;
    }
    return null;
}

async function permissionHook(block: any): Promise<HookResult> {
    if (block.name === "bash") {
        const command = block.input.command ?? "";
        for (const pattern of DENY_LIST) {
            if (command.includes(pattern)) return `Permission denied by deny list: ${pattern}`;
        }
        if (DESTRUCTIVE.some((keyword) => command.includes(keyword))) {
            console.log(`\n[permission] ${block.name}(${JSON.stringify(block.input)})`);
            const choice = (await rl.question("Allow? [y/N] ")).trim().toLowerCase();
            if (!["y", "yes"].includes(choice)) return "Permission denied by user";
        }
    }

    if (["read_file", "write_file", "edit_file"].includes(block.name)) {
        const rawPath = block.input.path ?? "";
        if (!isInside(path.resolve(WORKDIR, rawPath), path.resolve(WORKDIR))) {
            console.log(`\n[permission] ${block.name}(${JSON.stringify(block.input)})`);
            const choice = (await rl.question("Allow? [y/N] ")).trim().toLowerCase();
            if (!["y", "yes"].includes(choice)) return "Permission denied by user";
        }
    }

    if (block.name.startsWith("mcp__")) {
        const policy = mcpToolPolicies[block.name] ?? "confirm";
        if (policy !== "allow") {
            console.log(
                `\n[permission] External tool ${block.name}(${JSON.stringify(block.input)})`,
            );
            const choice = (await rl.question("Allow? [y/N] ")).trim().toLowerCase();
            if (!["y", "yes"].includes(choice)) return "Permission denied by user";
        }
    }
    return null;
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

async function executeTool(
    block: any, handlers: Record<string, ToolHandler>,
): Promise<string> {
    const blocked = await triggerHooks("PreToolUse", block);
    if (blocked) return String(blocked);
    const handler = handlers[block.name];
    if (!handler) return `Unknown tool: ${block.name}`;
    let output: string;
    try {
        output = String(await handler(block.input));
    } catch (error: any) {
        output = `Error: ${error?.constructor?.name ?? "Error"}: ${error.message}`;
    }
    await triggerHooks("PostToolUse", block, output);
    return output;
}

// -- Agent loop with a dynamic tool pool --

const rl = createInterface({ input: process.stdin, output: process.stdout });

async function agentLoop(messages: Msg[]): Promise<void> {
    while (true) {
        let response;
        let handlers: Record<string, ToolHandler>;
        try {
            // 每轮重新组装工具池 —— 这一章的关键：连上新服务器后，
            // 下一轮请求就自动带上它的工具，循环本身不用改。
            const [tools, assembled] = assembleToolPool();
            handlers = assembled;
            response = await client.messages.create({
                model: MODEL,
                system: assembleSystemPrompt(),
                messages: messages as any,
                tools: tools as any,
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
            await triggerHooks("Stop", messages);
            return;
        }

        messages.push({ role: "assistant", content: response.content });
        const toolCalls = response.content.filter((b: any) => b.type === "tool_use") as any[];
        if (toolCalls.length === 0) {
            await triggerHooks("Stop", messages);
            return;
        }

        const results: any[] = [];
        for (const block of toolCalls) {
            console.log(`> ${block.name}`);
            const output = await executeTool(block, handlers);
            console.log(output.slice(0, 300));
            results.push({ type: "tool_result", tool_use_id: block.id, content: output });
        }
        messages.push({ role: "user", content: results });
    }
}

console.log("s14: MCP tools");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("s14 >> ");
    } catch {
        break;
    }
    if (["q", "exit", ""].includes(query.trim().toLowerCase())) break;

    await triggerHooks("UserPromptSubmit", query);
    history.push({ role: "user", content: query });
    await agentLoop(history);

    const content = history[history.length - 1].content;
    if (Array.isArray(content)) {
        for (const block of content) {
            if (block?.type === "text") console.log(block.text ?? "");
        }
    }
    console.log();
}

rl.close();
