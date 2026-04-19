export type TodoStatus = 'pending' | 'in_progress' | 'completed';

export type TodoItemPayload = {
  content: string;
  status: TodoStatus;
  activeForm?: string;
};

export type TaskItemPayload = {
  id: string;
  content: string;
  status: string;
  owner?: string;
};

export type ContextSnapshotPayload = {
  projection_mode: 'raw' | 'compact' | 'collapse';
  history_messages: number;
  model_messages: number;
  visible_messages: number;
  hidden_messages: number;
  compact_count: number;
  collapse_count: number;
  session_memory_status: 'missing' | 'current' | 'stale';
  latest_event?: string;
};

export type SubagentItemPayload = {
  created_at: string;
  agent_type: string;
  role: string;
  content: string;
  subagent_thread_id: string;
};

export type BackgroundSubagentItemPayload = {
  run_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  mode: 'background_subagent' | 'background_fork';
  agent_type: string;
  progress_summary: string;
  pending_inputs: number;
  total_invocations: number;
};

export type FrontendEvent =
  | { type: 'session_started'; session_id: string; workdir: string }
  | { type: 'user_message'; id: string; text: string }
  | { type: 'assistant_delta'; message_id: string; text: string }
  | { type: 'assistant_message'; message_id: string; text: string }
  | { type: 'tool_started'; tool_call_id: string; name: string; summary?: string }
  | { type: 'tool_finished'; tool_call_id: string; name: string; status: 'success'; preview?: string }
  | { type: 'tool_failed'; tool_call_id: string; name: string; error: string }
  | { type: 'permission_requested'; request_id: string; tool: string; description: string; options: Array<'approve' | 'reject'> }
  | { type: 'permission_resolved'; request_id: string; decision: 'approve' | 'reject'; message?: string }
  | { type: 'todo_snapshot'; items: TodoItemPayload[] }
  | { type: 'task_snapshot'; items: TaskItemPayload[] }
  | ({ type: 'context_snapshot' } & ContextSnapshotPayload)
  | { type: 'subagent_snapshot'; total: number; items: SubagentItemPayload[] }
  | { type: 'background_subagent_snapshot'; total: number; items: BackgroundSubagentItemPayload[] }
  | { type: 'runtime_event'; kind: string; message: string; metadata?: Record<string, unknown> }
  | { type: 'recovery_brief'; text: string }
  | { type: 'run_finished'; session_id: string; status: 'completed' | 'exited' }
  | { type: 'run_failed'; session_id: string; error: string }
  | { type: 'protocol_error'; error: string };

export type FrontendInput =
  | { type: 'submit_prompt'; text: string }
  | { type: 'permission_decision'; request_id: string; decision: 'approve' | 'reject'; message?: string }
  | { type: 'refresh_snapshots' }
  | { type: 'run_background_subagent'; task: string; agent_type?: string; plan_id?: string; max_turns?: number }
  | { type: 'subagent_send_input'; run_id: string; message: string }
  | { type: 'subagent_stop'; run_id: string }
  | { type: 'interrupt' }
  | { type: 'exit' };

const EVENT_TYPES = new Set([
  'session_started',
  'user_message',
  'assistant_delta',
  'assistant_message',
  'tool_started',
  'tool_finished',
  'tool_failed',
  'permission_requested',
  'permission_resolved',
  'todo_snapshot',
  'task_snapshot',
  'context_snapshot',
  'subagent_snapshot',
  'background_subagent_snapshot',
  'runtime_event',
  'recovery_brief',
  'run_finished',
  'run_failed',
  'protocol_error'
]);

export function parseFrontendEvent(line: string): FrontendEvent {
  const raw: unknown = JSON.parse(line);
  if (!isObject(raw)) {
    throw new Error('frontend event must be an object');
  }
  const type = raw.type;
  if (typeof type !== 'string' || !EVENT_TYPES.has(type)) {
    throw new Error(`unknown frontend event type: ${String(type)}`);
  }
  return raw as FrontendEvent;
}

export function encodeFrontendInput(input: FrontendInput): string {
  return `${JSON.stringify(input)}\n`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
