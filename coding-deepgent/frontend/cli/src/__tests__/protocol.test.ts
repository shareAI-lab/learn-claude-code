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

  it('rejects unknown frontend events', () => {
    expect(() => parseFrontendEvent('{"type":"unknown"}')).toThrow(/unknown frontend event type/);
  });

  it('encodes frontend input as json line', () => {
    expect(encodeFrontendInput({ type: 'submit_prompt', text: 'hello' })).toBe(
      '{"type":"submit_prompt","text":"hello"}\n'
    );
  });
});

