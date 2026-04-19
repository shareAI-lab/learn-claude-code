import type {
  ContextSnapshotPayload,
  FrontendEvent,
  SubagentItemPayload,
  TaskItemPayload,
  TodoItemPayload
} from './protocol.js';

export type MessageKind = 'user' | 'assistant' | 'tool' | 'system' | 'error';

export type UiMessage = {
  id: string;
  kind: MessageKind;
  title?: string;
  text: string;
  streaming?: boolean;
};

export type PendingPermission = {
  requestId: string;
  tool: string;
  description: string;
  options: Array<'approve' | 'reject'>;
};

export type UiState = {
  sessionId?: string;
  workdir?: string;
  messages: UiMessage[];
  todos: TodoItemPayload[];
  tasks: TaskItemPayload[];
  contextSnapshot?: ContextSnapshotPayload;
  subagentSnapshot?: { total: number; items: SubagentItemPayload[] };
  pendingPermissions: PendingPermission[];
  recoveryBrief?: string;
  isRunning: boolean;
  status: string;
  lastError?: string;
};

export type UiAction =
  | FrontendEvent
  | { type: 'ui_clear' }
  | { type: 'ui_help' }
  | { type: 'ui_interrupted' };

export const initialUiState: UiState = {
  messages: [],
  todos: [],
  tasks: [],
  pendingPermissions: [],
  isRunning: false,
  status: 'Ready'
};

export function reduceFrontendEvent(state: UiState, event: UiAction): UiState {
  switch (event.type) {
    case 'session_started':
      return {
        ...state,
        sessionId: event.session_id,
        workdir: event.workdir,
        status: 'Session started'
      };
    case 'user_message':
      return {
        ...state,
        isRunning: true,
        status: 'Running',
        messages: [
          ...state.messages,
          { id: event.id, kind: 'user', title: 'You', text: event.text }
        ]
      };
    case 'assistant_delta':
      return upsertAssistantDelta(state, event.message_id, event.text);
    case 'assistant_message':
      return upsertMessage(state, {
        id: event.message_id,
        kind: 'assistant',
        title: 'Assistant',
        text: event.text,
        streaming: false
      });
    case 'tool_started':
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: event.tool_call_id,
            kind: 'tool',
            title: `Tool: ${event.name}`,
            text: event.summary || 'started',
            streaming: true
          }
        ]
      };
    case 'tool_finished':
      return upsertMessage(state, {
        id: event.tool_call_id,
        kind: 'tool',
        title: `Tool: ${event.name}`,
        text: event.preview || 'completed',
        streaming: false
      });
    case 'tool_failed':
      return upsertMessage(state, {
        id: event.tool_call_id,
        kind: 'error',
        title: `Tool failed: ${event.name}`,
        text: event.error,
        streaming: false
      });
    case 'permission_requested':
      return {
        ...state,
        pendingPermissions: [
          ...state.pendingPermissions,
          {
            requestId: event.request_id,
            tool: event.tool,
            description: event.description,
            options: event.options
          }
        ],
        status: `Approval needed for ${event.tool}`
      };
    case 'permission_resolved':
      return {
        ...state,
        pendingPermissions: state.pendingPermissions.filter(
          permission => permission.requestId !== event.request_id
        ),
        messages: [
          ...state.messages,
          {
            id: `permission-${event.request_id}`,
            kind: 'system',
            title: 'Permission',
            text: event.message || `Decision: ${event.decision}`
          }
        ]
      };
    case 'todo_snapshot':
      return { ...state, todos: event.items };
    case 'task_snapshot':
      return { ...state, tasks: event.items };
    case 'context_snapshot':
      return {
        ...state,
        contextSnapshot: {
          projection_mode: event.projection_mode,
          history_messages: event.history_messages,
          model_messages: event.model_messages,
          visible_messages: event.visible_messages,
          hidden_messages: event.hidden_messages,
          compact_count: event.compact_count,
          collapse_count: event.collapse_count,
          session_memory_status: event.session_memory_status,
          ...(event.latest_event ? { latest_event: event.latest_event } : {})
        }
      };
    case 'subagent_snapshot':
      return {
        ...state,
        subagentSnapshot: { total: event.total, items: event.items }
      };
    case 'runtime_event':
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: `runtime-${state.messages.length}`,
            kind: event.kind.includes('error') ? 'error' : 'system',
            title: event.kind,
            text: event.message
          }
        ]
      };
    case 'recovery_brief':
      return { ...state, recoveryBrief: event.text };
    case 'run_finished':
      return {
        ...state,
        isRunning: false,
        status: event.status === 'exited' ? 'Exited' : 'Ready'
      };
    case 'run_failed':
      return {
        ...state,
        isRunning: false,
        lastError: event.error,
        status: 'Failed',
        messages: [
          ...state.messages,
          { id: `error-${state.messages.length}`, kind: 'error', title: 'Run failed', text: event.error }
        ]
      };
    case 'protocol_error':
      return {
        ...state,
        lastError: event.error,
        messages: [
          ...state.messages,
          { id: `protocol-${state.messages.length}`, kind: 'error', title: 'Protocol error', text: event.error }
        ]
      };
    case 'ui_clear':
      return {
        ...state,
        messages: [],
        status: 'Cleared'
      };
    case 'ui_help':
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: `help-${state.messages.length}`,
            kind: 'system',
            title: 'Help',
            text: 'Commands: /help show this message, /clear clear visible messages, /exit quit.'
          }
        ],
        status: 'Help shown'
      };
    case 'ui_interrupted':
      return {
        ...state,
        isRunning: false,
        status: 'Interrupted',
        messages: [
          ...state.messages,
          {
            id: `interrupt-${state.messages.length}`,
            kind: 'system',
            title: 'Interrupted',
            text: 'Frontend requested interruption.'
          }
        ]
      };
  }
}

function upsertAssistantDelta(state: UiState, id: string, delta: string): UiState {
  const existing = state.messages.find(message => message.id === id);
  if (!existing) {
    return {
      ...state,
      messages: [
        ...state.messages,
        { id, kind: 'assistant', title: 'Assistant', text: delta, streaming: true }
      ]
    };
  }
  return upsertMessage(state, { ...existing, text: existing.text + delta, streaming: true });
}

function upsertMessage(state: UiState, message: UiMessage): UiState {
  const index = state.messages.findIndex(candidate => candidate.id === message.id);
  if (index === -1) {
    return { ...state, messages: [...state.messages, message] };
  }
  return {
    ...state,
    messages: state.messages.map((candidate, candidateIndex) =>
      candidateIndex === index ? message : candidate
    )
  };
}
