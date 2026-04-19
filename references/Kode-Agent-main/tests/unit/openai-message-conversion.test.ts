import { describe, expect, test } from 'bun:test'
import { convertAnthropicMessagesToOpenAIMessages } from '@utils/model/openaiMessageConversion'

describe('openaiMessageConversion', () => {
  test('converts user image+text blocks and preserves tool call/result ordering', () => {
    const messages: any[] = [
      {
        message: {
          role: 'user',
          content: [
            {
              type: 'image',
              source: {
                type: 'base64',
                media_type: 'image/png',
                data: 'Zm9v',
              },
            },
            { type: 'text', text: 'What is in this image?' },
          ],
        },
      },
      {
        message: {
          role: 'assistant',
          content: [
            {
              type: 'tool_use',
              id: 'tool_1',
              name: 'Read',
              input: { path: 'README.md' },
            },
          ],
        },
      },
      {
        message: {
          role: 'user',
          content: [
            {
              type: 'tool_result',
              tool_use_id: 'tool_1',
              content: 'file contents',
            },
          ],
        },
      },
      {
        message: {
          role: 'assistant',
          content: [{ type: 'text', text: 'Done' }],
        },
      },
    ]

    const converted = convertAnthropicMessagesToOpenAIMessages(messages)

    expect(converted[0]?.role).toBe('user')
    expect(Array.isArray((converted[0] as any)?.content)).toBe(true)
    expect((converted[0] as any).content[0]).toMatchObject({
      type: 'image_url',
      image_url: { url: 'data:image/png;base64,Zm9v' },
    })
    expect((converted[0] as any).content[1]).toMatchObject({
      type: 'text',
      text: 'What is in this image?',
    })

    expect((converted[1] as any)?.role).toBe('assistant')
    expect((converted[1] as any)?.tool_calls?.[0]).toMatchObject({
      id: 'tool_1',
      type: 'function',
      function: { name: 'Read' },
    })

    expect((converted[2] as any)?.role).toBe('tool')
    expect((converted[2] as any)?.tool_call_id).toBe('tool_1')
    expect((converted[2] as any)?.content).toBe('file contents')

    expect((converted[3] as any)?.role).toBe('assistant')
    expect((converted[3] as any)?.content).toBe('Done')
  })
})
