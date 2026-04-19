import OpenAI from 'openai'

type AnthropicImageBlock = {
  type: 'image'
  source:
    | { type: 'base64'; media_type: string; data: string }
    | { type: 'url'; url: string }
}

type AnthropicTextBlock = { type: 'text'; text: string }
type AnthropicToolUseBlock = {
  type: 'tool_use'
  id: string
  name: string
  input: unknown
}
type AnthropicToolResultBlock = {
  type: 'tool_result'
  tool_use_id: string
  content: unknown
}

type AnthropicBlock =
  | AnthropicTextBlock
  | AnthropicImageBlock
  | AnthropicToolUseBlock
  | AnthropicToolResultBlock
  | { type: string; [key: string]: unknown }

type AnthropicLikeMessage = {
  message: {
    role: 'user' | 'assistant'
    content: string | AnthropicBlock[] | AnthropicBlock
  }
}

export function convertAnthropicMessagesToOpenAIMessages(
  messages: AnthropicLikeMessage[],
): (
  | OpenAI.ChatCompletionMessageParam
  | OpenAI.ChatCompletionToolMessageParam
)[] {
  const openaiMessages: any[] = []

  const toolResults: Record<string, OpenAI.ChatCompletionToolMessageParam> = {}

  for (const message of messages) {
    const blocks: AnthropicBlock[] = []
    if (typeof message.message.content === 'string') {
      blocks.push({ type: 'text', text: message.message.content })
    } else if (Array.isArray(message.message.content)) {
      blocks.push(...message.message.content)
    } else if (message.message.content) {
      blocks.push(message.message.content)
    }

    const role = message.message.role

    const userContentParts: any[] = []
    const assistantTextParts: string[] = []
    const assistantToolCalls: any[] = []

    for (const block of blocks) {
      if (block.type === 'text') {
        const text =
          typeof (block as any).text === 'string' ? (block as any).text : ''
        if (!text) continue
        if (role === 'user') {
          userContentParts.push({ type: 'text', text })
        } else if (role === 'assistant') {
          assistantTextParts.push(text)
        }
        continue
      }

      if (block.type === 'image' && role === 'user') {
        const source = (block as AnthropicImageBlock).source
        if (source?.type === 'base64') {
          userContentParts.push({
            type: 'image_url',
            image_url: {
              url: `data:${source.media_type};base64,${source.data}`,
            },
          })
        } else if (source?.type === 'url') {
          userContentParts.push({
            type: 'image_url',
            image_url: { url: source.url },
          })
        }
        continue
      }

      if (block.type === 'tool_use') {
        assistantToolCalls.push({
          type: 'function',
          function: {
            name: (block as AnthropicToolUseBlock).name,
            arguments: JSON.stringify((block as AnthropicToolUseBlock).input),
          },
          id: (block as AnthropicToolUseBlock).id,
        })
        continue
      }

      if (block.type === 'tool_result') {
        const toolUseId = (block as AnthropicToolResultBlock).tool_use_id
        const rawToolContent = (block as AnthropicToolResultBlock).content
        const toolContent =
          typeof rawToolContent === 'string'
            ? rawToolContent
            : JSON.stringify(rawToolContent)
        toolResults[toolUseId] = {
          role: 'tool',
          content: toolContent,
          tool_call_id: toolUseId,
        }
        continue
      }
    }

    if (role === 'user') {
      if (
        userContentParts.length === 1 &&
        userContentParts[0]?.type === 'text'
      ) {
        openaiMessages.push({
          role: 'user',
          content: userContentParts[0].text,
        } as any)
      } else if (userContentParts.length > 0) {
        openaiMessages.push({ role: 'user', content: userContentParts } as any)
      }
      continue
    }

    if (role === 'assistant') {
      const text = assistantTextParts.filter(Boolean).join('\n')
      if (assistantToolCalls.length > 0) {
        openaiMessages.push({
          role: 'assistant',
          content: text ? text : undefined,
          tool_calls: assistantToolCalls,
        } as any)
        continue
      }
      if (text) {
        openaiMessages.push({ role: 'assistant', content: text } as any)
      }
    }
  }

  const finalMessages: any[] = []

  for (const message of openaiMessages) {
    finalMessages.push(message)

    if ('tool_calls' in message && message.tool_calls) {
      for (const toolCall of message.tool_calls) {
        if (toolResults[toolCall.id]) {
          finalMessages.push(toolResults[toolCall.id])
        }
      }
    }
  }

  return finalMessages
}
