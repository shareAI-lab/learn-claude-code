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
  | { type: 'runtime_event'; kind: string; message: string; metadata?: Record<string, unknown> }
  | { type: 'recovery_brief'; text: string }
  | { type: 'run_finished'; session_id: string; status: 'completed' | 'exited' }
  | { type: 'run_failed'; session_id: string; error: string }
  | { type: 'protocol_error'; error: string };

export type FrontendInput =
  | { type: 'submit_prompt'; text: string }
  | { type: 'permission_decision'; request_id: string; decision: 'approve' | 'reject'; message?: string }
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

