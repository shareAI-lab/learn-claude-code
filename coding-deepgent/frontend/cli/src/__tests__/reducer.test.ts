import { describe, expect, it } from 'vitest';
import { initialUiState, reduceFrontendEvent } from '../bridge/reducer.js';

describe('frontend reducer', () => {
  it('builds a multi-turn message view', () => {
    let state = reduceFrontendEvent(initialUiState, {
      type: 'session_started',
      session_id: 'session-1',
      workdir: '/repo'
    });
    state = reduceFrontendEvent(state, { type: 'user_message', id: 'u1', text: 'hello' });
    state = reduceFrontendEvent(state, { type: 'assistant_delta', message_id: 'a1', text: 'he' });
    state = reduceFrontendEvent(state, { type: 'assistant_delta', message_id: 'a1', text: 'llo' });
    state = reduceFrontendEvent(state, { type: 'assistant_message', message_id: 'a1', text: 'hello' });
    state = reduceFrontendEvent(state, { type: 'run_finished', session_id: 'session-1', status: 'completed' });

    expect(state.sessionId).toBe('session-1');
    expect(state.messages.map(message => message.text)).toEqual(['hello', 'hello']);
    expect(state.isRunning).toBe(false);
  });

  it('tracks permission queue and decisions', () => {
    let state = reduceFrontendEvent(initialUiState, {
      type: 'permission_requested',
      request_id: 'req-1',
      tool: 'write_file',
      description: 'Write app.py',
      options: ['approve', 'reject']
    });
    expect(state.pendingPermissions).toHaveLength(1);

    state = reduceFrontendEvent(state, {
      type: 'permission_resolved',
      request_id: 'req-1',
      decision: 'reject',
      message: 'No'
    });

    expect(state.pendingPermissions).toHaveLength(0);
    expect(state.messages.at(-1)?.text).toBe('No');
  });

  it('stores todo snapshots', () => {
    const state = reduceFrontendEvent(initialUiState, {
      type: 'todo_snapshot',
      items: [{ content: 'Build UI', status: 'in_progress', activeForm: 'Building UI' }]
    });

    expect(state.todos).toEqual([
      { content: 'Build UI', status: 'in_progress', activeForm: 'Building UI' }
    ]);
  });

  it('stores runtime visibility snapshots', () => {
    let state = reduceFrontendEvent(initialUiState, {
      type: 'task_snapshot',
      items: [{ id: 'task-1', content: 'Inspect context', status: 'in_progress' }]
    });
    state = reduceFrontendEvent(state, {
      type: 'context_snapshot',
      projection_mode: 'collapse',
      history_messages: 8,
      model_messages: 5,
      visible_messages: 4,
      hidden_messages: 4,
      compact_count: 1,
      collapse_count: 1,
      session_memory_status: 'current',
      latest_event: 'collapse'
    });
    state = reduceFrontendEvent(state, {
      type: 'subagent_snapshot',
      total: 1,
      items: [
        {
          created_at: '2026-04-20T00:00:00Z',
          agent_type: 'general',
          role: 'assistant',
          content: 'Checked tests.',
          subagent_thread_id: 'child-1'
        }
      ]
    });

    expect(state.tasks).toEqual([
      { id: 'task-1', content: 'Inspect context', status: 'in_progress' }
    ]);
    expect(state.contextSnapshot?.projection_mode).toBe('collapse');
    expect(state.contextSnapshot?.session_memory_status).toBe('current');
    expect(state.subagentSnapshot?.total).toBe(1);
    expect(state.subagentSnapshot?.items[0]?.content).toBe('Checked tests.');

    state = reduceFrontendEvent(state, {
      type: 'background_subagent_snapshot',
      total: 1,
      items: [
        {
          run_id: 'bgrun-1',
          status: 'running',
          mode: 'background_subagent',
          agent_type: 'general',
          progress_summary: 'Background subagent is running.',
          pending_inputs: 1,
          total_invocations: 0
        }
      ]
    });

    expect(state.backgroundSubagentSnapshot?.total).toBe(1);
    expect(state.backgroundSubagentSnapshot?.items[0]?.run_id).toBe('bgrun-1');
  });

  it('handles interleaved streaming and tool events', () => {
    let state = reduceFrontendEvent(initialUiState, { type: 'user_message', id: 'u1', text: 'run' });
    state = reduceFrontendEvent(state, { type: 'assistant_delta', message_id: 'a1', text: 'working' });
    state = reduceFrontendEvent(state, { type: 'tool_started', tool_call_id: 'call-1', name: 'read_file', summary: 'Reading' });
    state = reduceFrontendEvent(state, { type: 'tool_finished', tool_call_id: 'call-1', name: 'read_file', status: 'success', preview: 'Done' });
    state = reduceFrontendEvent(state, { type: 'assistant_delta', message_id: 'a1', text: ' done' });
    state = reduceFrontendEvent(state, { type: 'assistant_message', message_id: 'a1', text: 'working done' });

    expect(state.messages.map(message => [message.kind, message.text])).toEqual([
      ['user', 'run'],
      ['assistant', 'working done'],
      ['tool', 'Done']
    ]);
  });

  it('handles local CLI commands', () => {
    let state = reduceFrontendEvent(initialUiState, { type: 'user_message', id: 'u1', text: 'hello' });
    state = reduceFrontendEvent(state, { type: 'ui_help' });
    expect(state.messages.at(-1)?.title).toBe('Help');

    state = reduceFrontendEvent(state, { type: 'ui_clear' });
    expect(state.messages).toEqual([]);
    expect(state.status).toBe('Cleared');

    state = reduceFrontendEvent(state, { type: 'ui_interrupted' });
    expect(state.status).toBe('Interrupted');
    expect(state.isRunning).toBe(false);
  });
});
