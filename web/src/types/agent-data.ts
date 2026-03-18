export interface AgentVersion {
  id: string;
  filename: string;
  title: string;
  subtitle: string;
  loc: number;
  tools: string[];
  newTools: string[];
  coreAddition: string;
  keyInsight: string;
  classes: { name: string; startLine: number; endLine: number }[];
  functions: { name: string; signature: string; startLine: number }[];
  layer: "tools" | "planning" | "memory" | "concurrency" | "collaboration";
  source: string;
}

export interface VersionDiff {
  from: string;
  to: string;
  newClasses: string[];
  newFunctions: string[];
  newTools: string[];
  locDelta: number;
}

export interface DocContent {
  version: string;
  locale: "en" | "zh" | "ja";
  title: string;
  content: string; // raw markdown
}

export interface VersionIndex {
  versions: AgentVersion[];
  diffs: VersionDiff[];
}

export type SimStepType =
  | "user_message"
  | "assistant_text"
  | "tool_call"
  | "tool_result"
  | "system_event";

export interface SimStep {
  type: SimStepType;
  content: string;
  annotation: string;
  toolName?: string;
  toolInput?: string;
}

export interface Scenario {
  version: string;
  title: string;
  description: string;
  steps: SimStep[];
}

export interface FlowNode {
  id: string;
  label: string;
  type: "start" | "process" | "decision" | "subprocess" | "end";
  x: number;
  y: number;
}

export interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

export interface TraceToolExecution {
  name: string;
  input: Record<string, unknown>;
  output: string;
}

export interface TraceContentBlock {
  type: string;
  text?: string;
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  raw?: string;
}

export interface TraceUsage {
  input_tokens: number;
  output_tokens: number;
}

export interface TraceRequest {
  model: string;
  system: string;
  messages: unknown[];
  tools: unknown[];
  max_tokens: number;
}

export interface TraceResponse {
  id: string;
  type: string;
  role: string;
  model: string;
  stop_reason: string;
  content: TraceContentBlock[];
  usage: TraceUsage;
}

export interface TraceCycle {
  cycle: number;
  elapsed_ms: number;
  request: TraceRequest;
  response: TraceResponse;
  tool_executions: TraceToolExecution[];
}

export interface ApiTrace {
  version: string;
  prompt: string;
  model: string;
  total_cycles: number;
  total_input_tokens: number;
  total_output_tokens: number;
  cycles: TraceCycle[];
}
