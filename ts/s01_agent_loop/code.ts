/**
 * s01_agent_loop.ts - The agent loop
 *
 * TypeScript 1:1 port of s01_agent_loop/code.py
 *
 * The entire secret of an AI coding agent in one pattern:
 *
 *     while (true) {
 *         response = LLM(messages, tools)
 *         if (response contains no tool_use) break
 *         execute tools
 *         append results
 *     }
 *
 *     +----------+      +-------+      +---------+
 *     |   User   | ---> |  LLM  | ---> |  Tool   |
 *     |  prompt  |      |       |      | execute |
 *     +----------+      +---+---+      +----+----+
 *                           ^               |
 *                           |   tool_result |
 *                           +---------------+
 *                           (loop continues)
 *
 * Usage:
 *     cd ts && npm install
 *     npm run s01
 */

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline/promises";

import Anthropic from "@anthropic-ai/sdk";
import dotenv from "dotenv";

// py: load_dotenv(override=True)
// TS 里没有"从调用者文件向上找 .env"的默认行为，所以显式指向仓库根目录。
const HERE = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(HERE, "../../.env"), override: true, quiet: true });

// py: os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
if (process.env.ANTHROPIC_BASE_URL) {
    delete process.env.ANTHROPIC_AUTH_TOKEN;
}

const client = new Anthropic({ baseURL: process.env.ANTHROPIC_BASE_URL });

// py: MODEL = os.environ["MODEL_ID"]  —— 缺失就立刻崩，不给默认值
const MODEL: string = process.env.MODEL_ID ?? "";
if (!MODEL) throw new Error("MODEL_ID is required (see .env)");

const WORKDIR = process.cwd();

const SYSTEM = `You are a coding agent at ${WORKDIR}. Use bash to solve tasks. Act, don't explain.`;

// -- Tool definition: just bash --
const TOOLS = [
    {
        name: "bash",
        description: "Run a shell command.",
        input_schema: {
            type: "object" as const,
            properties: { command: { type: "string" } },
            required: ["command"],
        },
    },
];

// -- Tool execution --
function runBash(command: string): string {
    const dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"];
    if (dangerous.some((d) => command.includes(d))) {
        return "Error: Dangerous command blocked";
    }

    // py: subprocess.run(shell=True, capture_output=True, text=True, timeout=120)
    // spawnSync 不会因非零退出码抛异常，最接近 Python 的行为。
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

// py 里 messages 是 list[dict]，这里用一个最小类型，保持和无类型的 Python 版同构
type Msg = { role: "user" | "assistant"; content: any };

// -- The core pattern: a while loop that calls tools until the model stops --
async function agentLoop(messages: Msg[]): Promise<void> {
    while (true) {
        const response = await client.messages.create({
            model: MODEL,
            system: SYSTEM,
            messages: messages as any,
            tools: TOOLS as any,
            max_tokens: 8000,
        });

        // Append assistant turn
        messages.push({ role: "assistant", content: response.content });

        // If the model didn't call a tool, we're done
        const toolCalls = response.content.filter(
            (block: any) => block.type === "tool_use",
        ) as any[];
        if (toolCalls.length === 0) return;

        // Execute each tool call, collect results
        const results: any[] = [];
        for (const block of toolCalls) {
            console.log(`\x1b[33m$ ${block.input.command}\x1b[0m`);
            const output = runBash(block.input.command);
            console.log(output.slice(0, 200));
            results.push({
                type: "tool_result",
                tool_use_id: block.id,
                content: output,
            });
        }

        // Feed tool results back, loop continues
        messages.push({ role: "user", content: results });
    }
}

// -- Entry point --
console.log("s01: agent loop");
console.log("Enter a question, press Enter to send. Type q to quit.\n");

const rl = createInterface({ input: process.stdin, output: process.stdout });
const history: Msg[] = [];

while (true) {
    let query: string;
    try {
        query = await rl.question("\x1b[36ms01 >> \x1b[0m");
    } catch {
        break; // Ctrl-C / Ctrl-D
    }
    if (["q", "exit", ""].includes(query.trim().toLowerCase())) break;

    history.push({ role: "user", content: query });
    await agentLoop(history);

    // Print the model's final text response
    const last = history[history.length - 1].content;
    if (Array.isArray(last)) {
        for (const block of last) {
            if (block?.type === "text") console.log(block.text);
        }
    }
    console.log();
}

rl.close();
