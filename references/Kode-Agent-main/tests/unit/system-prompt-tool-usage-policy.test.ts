import { describe, expect, test } from 'bun:test'
import { getSystemPrompt } from '@constants/prompts'

describe('System prompt tool usage policy (Reference CLI parity)', () => {
  test('encourages parallel only when independent (no placeholders)', async () => {
    const parts = await getSystemPrompt()
    const prompt = parts.join('\n')

    expect(prompt).toContain(
      'If you intend to call multiple tools and there are no dependencies between them, make all independent tool calls in parallel.',
    )
    expect(prompt).toContain(
      'Never use placeholders or guess missing parameters in tool calls.',
    )
    expect(prompt).not.toContain(
      'When making multiple bash tool calls, you MUST send a single message with multiple tools calls to run the calls in parallel.',
    )
  })
})
