export const VERSION_ORDER = [
  "s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09", "s10", "s11", "s12",
  "s13", "s14", "s15", "s16", "s17"
] as const;

export const LEARNING_PATH = VERSION_ORDER;

export type VersionId = typeof LEARNING_PATH[number];

export const VERSION_META: Record<string, {
  title: string;
  subtitle: string;
  coreAddition: string;
  keyInsight: string;
  layer: "tools" | "planning" | "memory" | "concurrency" | "collaboration" | "security";
  prevVersion: string | null;
}> = {
  s01: { title: "The Agent Loop", subtitle: "Bash is All You Need", coreAddition: "Single-tool agent loop", keyInsight: "The minimal agent kernel is a while loop + one tool", layer: "tools", prevVersion: null },
  s02: { title: "Tools", subtitle: "One Handler Per Tool", coreAddition: "Tool dispatch map", keyInsight: "The loop stays the same; new tools register into the dispatch map", layer: "tools", prevVersion: "s01" },
  s03: { title: "TodoWrite", subtitle: "Plan Before You Act", coreAddition: "TodoManager + nag reminder", keyInsight: "An agent without a plan drifts; list the steps first, then execute", layer: "planning", prevVersion: "s02" },
  s04: { title: "Subagents", subtitle: "Clean Context Per Subtask", coreAddition: "Subagent spawn with isolated messages[]", keyInsight: "Subagents use independent messages[], keeping the main conversation clean", layer: "planning", prevVersion: "s03" },
  s05: { title: "Skills", subtitle: "Load on Demand", coreAddition: "SkillLoader + two-layer injection", keyInsight: "Inject knowledge via tool_result when needed, not upfront in the system prompt", layer: "planning", prevVersion: "s04" },
  s06: { title: "Compact", subtitle: "Three-Layer Compression", coreAddition: "micro-compact + auto-compact + archival", keyInsight: "Context will fill up; three-layer compression strategy enables infinite sessions", layer: "memory", prevVersion: "s05" },
  s07: { title: "Tasks", subtitle: "Task Graph + Dependencies", coreAddition: "TaskManager with file-based state + dependency graph", keyInsight: "A file-based task graph with ordering, parallelism, and dependencies -- the coordination backbone for multi-agent work", layer: "planning", prevVersion: "s06" },
  s08: { title: "Background Tasks", subtitle: "Background Threads + Notifications", coreAddition: "BackgroundManager + notification queue", keyInsight: "Run slow operations in the background; the agent keeps thinking ahead", layer: "concurrency", prevVersion: "s07" },
  s09: { title: "Agent Teams", subtitle: "Teammates + Mailboxes", coreAddition: "TeammateManager + file-based mailbox", keyInsight: "When one agent can't finish, delegate to persistent teammates via async mailboxes", layer: "collaboration", prevVersion: "s08" },
  s10: { title: "Team Protocols", subtitle: "Shared Communication Rules", coreAddition: "request_id correlation for two protocols", keyInsight: "One request-response pattern drives all team negotiation", layer: "collaboration", prevVersion: "s09" },
  s11: { title: "Autonomous Agents", subtitle: "Scan Board, Claim Tasks", coreAddition: "Task board polling + timeout-based self-governance", keyInsight: "Teammates scan the board and claim tasks themselves; no need for the lead to assign each one", layer: "collaboration", prevVersion: "s10" },
  s12: { title: "Worktree + Task Isolation", subtitle: "Isolate by Directory", coreAddition: "Composable worktree lifecycle + event stream over a shared task board", keyInsight: "Each works in its own directory; tasks manage goals, worktrees manage directories, bound by ID", layer: "collaboration", prevVersion: "s11" },
  s13: { title: "Permission Guard", subtitle: "Not Every Command Should Run Automatically", coreAddition: "PermissionGuard with 5 permission modes (allow/ask/deny/auto_edit/edit)", keyInsight: "Permission is not yes/no -- it's a spectrum with five stops", layer: "security", prevVersion: "s02" },
  s14: { title: "Security Classifier", subtitle: "Let the Model Judge Its Own Commands", coreAddition: "Two-layer classifier: regex quick-scan + LLM intent classification", keyInsight: "Regex sees patterns; the LLM sees intent", layer: "security", prevVersion: "s13" },
  s15: { title: "Hooks System", subtitle: "Intercept Between Model and Tool", coreAddition: "HookManager with 8 event types and 3 execution modes", keyInsight: "Hooks don't change what tools do -- they change when, how, and whether they execute", layer: "security", prevVersion: "s13" },
  s16: { title: "MCP Client", subtitle: "Tools Don't Have to Be Built-in", coreAddition: "MCPClient + MCPManager for external tool servers via JSON-RPC", keyInsight: "MCP upgrades tool dispatch from a dict to a network protocol", layer: "security", prevVersion: "s02" },
  s17: { title: "Secure Extension Harness", subtitle: "Five Layers of Defense, One Loop", coreAddition: "Unified execution pipeline: Hook -> Classify -> Permission -> Execute -> PostHook", keyInsight: "Production harnesses aren't about more features -- they're about clear responsibilities at every layer", layer: "security", prevVersion: "s16" },
};

export const LAYERS = [
  { id: "tools" as const, label: "Tools & Execution", color: "#3B82F6", versions: ["s01", "s02"] },
  { id: "planning" as const, label: "Planning & Coordination", color: "#10B981", versions: ["s03", "s04", "s05", "s07"] },
  { id: "memory" as const, label: "Memory Management", color: "#8B5CF6", versions: ["s06"] },
  { id: "concurrency" as const, label: "Concurrency", color: "#F59E0B", versions: ["s08"] },
  { id: "collaboration" as const, label: "Collaboration", color: "#EF4444", versions: ["s09", "s10", "s11", "s12"] },
  { id: "security" as const, label: "Security & Extensibility", color: "#06B6D4", versions: ["s13", "s14", "s15", "s16", "s17"] },
] as const;
