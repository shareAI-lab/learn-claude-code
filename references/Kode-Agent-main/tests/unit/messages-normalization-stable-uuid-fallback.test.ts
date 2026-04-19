import { describe, expect, test } from 'bun:test'
import { normalizeMessages } from '@utils/messages'

describe('normalizeMessages stable UUID fallback', () => {
  test('uses assistant message.id when uuid is missing', () => {
    const assistant: any = {
      type: 'assistant',
      costUSD: 0,
      durationMs: 0,
      message: {
        id: 'msg_123',
        model: 'test',
        role: 'assistant',
        stop_reason: 'stop',
        stop_sequence: '',
        type: 'message',
        usage: {
          input_tokens: 0,
          output_tokens: 0,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        },
        content: [
          { type: 'text', text: 'hello', citations: [] },
          { type: 'text', text: 'world', citations: [] },
        ],
      },
    }

    const first = normalizeMessages([assistant] as any).map(m => m.uuid)
    const second = normalizeMessages([assistant] as any).map(m => m.uuid)

    expect(first).toHaveLength(2)
    expect(first[0]).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    )
    expect(first[1]).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    )
    expect(first[0]).not.toBe(first[1])
    expect(second).toEqual(first)
  })
})
