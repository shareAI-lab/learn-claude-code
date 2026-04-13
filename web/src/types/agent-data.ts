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
  layer: "core" | "hardening" | "runtime" | "platform";
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
  version: string | null;
  slug: string;
  locale: "en" | "zh" | "ja" | "vi";
  title: string;
  kind: "chapter" | "bridge";
  filename: string;
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
