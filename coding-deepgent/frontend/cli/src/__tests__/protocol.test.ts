import { describe, expect, it } from 'vitest';
import { encodeFrontendInput, parseFrontendEvent } from '../bridge/protocol.js';

describe('frontend protocol', () => {
  it('parses known frontend events', () => {
    const event = parseFrontendEvent('{"type":"assistant_message","message_id":"a1","text":"hello"}');

    expect(event.type).toBe('assistant_message');
    if (event.type === 'assistant_message') {
      expect(event.text).toBe('hello');
    }
  });

  it('parses runtime visibility snapshot events', () => {
    const event = parseFrontendEvent(
      '{"type":"context_snapshot","projection_mode":"compact","history_messages":8,"model_messages":5,"visible_messages":4,"hidden_messages":4,"compact_count":1,"collapse_count":0,"session_memory_status":"stale","latest_event":"compact"}'
    );

    expect(event.type).toBe('context_snapshot');
    if (event.type === 'context_snapshot') {
      expect(event.projection_mode).toBe('compact');
      expect(event.session_memory_status).toBe('stale');
    }
  });

  it('encodes control inputs for background subagents', () => {
    expect(
      encodeFrontendInput({
        type: 'run_background_subagent',
        task: 'inspect repo',
        agent_type: 'general'
      })
    ).toBe('{"type":"run_background_subagent","task":"inspect repo","agent_type":"general"}\n');
  });

  it('rejects unknown frontend events', () => {
    expect(() => parseFrontendEvent('{"type":"unknown"}')).toThrow(/unknown frontend event type/);
  });

  it('encodes frontend input as json line', () => {
    expect(encodeFrontendInput({ type: 'submit_prompt', text: 'hello' })).toBe(
      '{"type":"submit_prompt","text":"hello"}\n'
    );
  });
});
