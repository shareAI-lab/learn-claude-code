export const VERSION_ORDER = [
  "s01",
  "s02",
  "s03",
  "s04",
  "s05",
  "s06",
  "s07",
  "s08",
  "s09",
  "s10",
  "s11",
  "s12",
  "s13",
  "s14",
  "s15",
  "s16",
  "s17",
  "s18",
  "s19",
] as const;

export const LEARNING_PATH = VERSION_ORDER;

export type VersionId = typeof LEARNING_PATH[number];
export type LearningLayer = "core" | "hardening" | "runtime" | "platform";

export const VERSION_META: Record<string, {
  title: string;
  subtitle: string;
  coreAddition: string;
  keyInsight: string;
  layer: LearningLayer;
  prevVersion: string | null;
}> = {
  s01: {
    title: "The Agent Loop",
    subtitle: "Minimal Closed Loop",
    coreAddition: "LoopState + tool_result feedback",
    keyInsight: "An agent is just a loop: send messages, execute tools, feed results back, repeat.",
    layer: "core",
    prevVersion: null,
  },
  s02: {
    title: "Tool Use",
    subtitle: "Route Intent into Action",
    coreAddition: "Tool specs + dispatch map",
    keyInsight: "Adding a tool means adding one handler. The loop never changes.",
    layer: "core",
    prevVersion: "s01",
  },
  s03: {
    title: "TodoWrite",
    subtitle: "Session Planning",
    coreAddition: "PlanningState + reminder loop",
    keyInsight: "A visible plan keeps the agent on track when tasks get complex.",
    layer: "core",
    prevVersion: "s02",
  },
  s04: {
    title: "Subagent",
    subtitle: "Fresh Context per Subtask",
    coreAddition: "Delegation with isolated message history",
    keyInsight: "A subagent is mainly a context boundary, not a process trick.",
    layer: "core",
    prevVersion: "s03",
  },
  s05: {
    title: "Skills",
    subtitle: "Discover Cheap, Load Deep",
    coreAddition: "Skill registry + on-demand injection",
    keyInsight: "Discover cheaply, load deeply -- only when needed.",
    layer: "core",
    prevVersion: "s04",
  },
  s06: {
    title: "Context Compact",
    subtitle: "Keep the Active Context Small",
    coreAddition: "Persist markers + micro compact + summary compact",
    keyInsight: "Compaction isn't deleting history -- it's relocating detail so the agent can keep working.",
    layer: "core",
    prevVersion: "s05",
  },
  s07: {
    title: "Permission System",
    subtitle: "Intent Must Pass Safety",
    coreAddition: "deny / mode / allow / ask pipeline",
    keyInsight: "Safety is a pipeline, not a boolean: deny, check mode, allow, then ask.",
    layer: "hardening",
    prevVersion: "s06",
  },
  s08: {
    title: "Hook System",
    subtitle: "Extend Without Rewriting the Loop",
    coreAddition: "Lifecycle events + side-effect hooks",
    keyInsight: "The loop owns control flow; hooks only observe, block, or annotate at named moments.",
    layer: "hardening",
    prevVersion: "s07",
  },
  s09: {
    title: "Memory System",
    subtitle: "Keep Only What Survives Sessions",
    coreAddition: "Typed memory records + reload path",
    keyInsight: "Memory gives direction; current observation gives truth.",
    layer: "hardening",
    prevVersion: "s08",
  },
  s10: {
    title: "System Prompt",
    subtitle: "Build Inputs as a Pipeline",
    coreAddition: "Prompt sections + dynamic assembly",
    keyInsight: "The model sees a constructed input pipeline, not one giant static string.",
    layer: "hardening",
    prevVersion: "s09",
  },
  s11: {
    title: "Error Recovery",
    subtitle: "Recover, Then Continue",
    coreAddition: "Continuation reasons + retry branches",
    keyInsight: "Most failures aren't true task failure -- they're signals to try a different path.",
    layer: "hardening",
    prevVersion: "s10",
  },
  s12: {
    title: "Task System",
    subtitle: "Durable Work Graph",
    coreAddition: "Task records + dependencies + unlock rules",
    keyInsight: "Todo lists help a session; durable task graphs coordinate work that outlives it.",
    layer: "runtime",
    prevVersion: "s11",
  },
  s13: {
    title: "Background Tasks",
    subtitle: "Separate Goal from Running Work",
    coreAddition: "RuntimeTaskState + async execution slots",
    keyInsight: "Background execution is a runtime lane, not a second main loop.",
    layer: "runtime",
    prevVersion: "s12",
  },
  s14: {
    title: "Cron Scheduler",
    subtitle: "Let Time Trigger Work",
    coreAddition: "Scheduled triggers over runtime tasks",
    keyInsight: "Scheduling is not a separate system -- it just feeds the same agent loop from a timer.",
    layer: "runtime",
    prevVersion: "s13",
  },
  s15: {
    title: "Agent Teams",
    subtitle: "Persistent Specialists",
    coreAddition: "Team roster + teammate lifecycle",
    keyInsight: "Teammates persist beyond one prompt, have identity, and coordinate through durable channels.",
    layer: "platform",
    prevVersion: "s14",
  },
  s16: {
    title: "Team Protocols",
    subtitle: "Shared Request-Response Rules",
    coreAddition: "Protocol envelopes + request correlation",
    keyInsight: "A protocol request is a structured message with an ID; the response must reference the same ID.",
    layer: "platform",
    prevVersion: "s15",
  },
  s17: {
    title: "Autonomous Agents",
    subtitle: "Self-Claim and Self-Resume",
    coreAddition: "Idle polling + role-aware self-claim + resume context",
    keyInsight: "Autonomy is a bounded mechanism -- idle, scan, claim, resume -- not magic.",
    layer: "platform",
    prevVersion: "s16",
  },
  s18: {
    title: "Worktree Isolation",
    subtitle: "Separate Directory, Separate Lane",
    coreAddition: "Task-worktree state + explicit enter/closeout lifecycle",
    keyInsight: "Tasks answer what; worktrees answer where. Keep them separate.",
    layer: "platform",
    prevVersion: "s17",
  },
  s19: {
    title: "MCP & Plugin",
    subtitle: "External Capability Bus",
    coreAddition: "Scoped servers + capability routing",
    keyInsight: "External capabilities join the same routing, permission, and result-append path as native tools.",
    layer: "platform",
    prevVersion: "s18",
  },
};

export const LAYERS = [
  {
    id: "core" as const,
    label: "Core Single-Agent",
    color: "#2563EB",
    versions: ["s01", "s02", "s03", "s04", "s05", "s06"],
  },
  {
    id: "hardening" as const,
    label: "Production Hardening",
    color: "#059669",
    versions: ["s07", "s08", "s09", "s10", "s11"],
  },
  {
    id: "runtime" as const,
    label: "Task Runtime",
    color: "#D97706",
    versions: ["s12", "s13", "s14"],
  },
  {
    id: "platform" as const,
    label: "Multi-Agent Platform",
    color: "#DC2626",
    versions: ["s15", "s16", "s17", "s18", "s19"],
  },
] as const;
