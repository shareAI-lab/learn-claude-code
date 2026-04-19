import { StreamingEvent } from './base'
import { AssistantMessage } from '@query'
import { setRequestStatus } from '@utils/session/requestStatus'

export async function processResponsesStream(
  stream: AsyncGenerator<StreamingEvent>,
  startTime: number,
  fallbackResponseId: string,
): Promise<{ assistantMessage: AssistantMessage; rawResponse: any }> {
  const contentBlocks: any[] = []
  const usage: any = {
    prompt_tokens: 0,
    completion_tokens: 0,
  }

  let responseId = fallbackResponseId
  const pendingToolCalls: any[] = []
  let hasMarkedStreaming = false

  for await (const event of stream) {
    if (event.type === 'message_start') {
      responseId = event.responseId || responseId
      continue
    }

    if (event.type === 'text_delta') {
      if (!hasMarkedStreaming) {
        setRequestStatus({ kind: 'streaming' })
        hasMarkedStreaming = true
      }
      const last = contentBlocks[contentBlocks.length - 1]
      if (!last || last.type !== 'text') {
        contentBlocks.push({ type: 'text', text: event.delta, citations: [] })
      } else {
        last.text += event.delta
      }
      continue
    }

    if (event.type === 'tool_request') {
      setRequestStatus({ kind: 'tool', detail: event.tool?.name })
      pendingToolCalls.push(event.tool)
      continue
    }

    if (event.type === 'usage') {
      usage.prompt_tokens = event.usage.input
      usage.completion_tokens = event.usage.output
      usage.promptTokens = event.usage.input
      usage.completionTokens = event.usage.output
      usage.totalTokens =
        event.usage.total ?? event.usage.input + event.usage.output
      if (event.usage.reasoning !== undefined) {
        usage.reasoningTokens = event.usage.reasoning
      }
      continue
    }
  }

  for (const toolCall of pendingToolCalls) {
    let toolArgs = {}
    try {
      toolArgs = toolCall.input ? JSON.parse(toolCall.input) : {}
    } catch {}

    contentBlocks.push({
      type: 'tool_use',
      id: toolCall.id,
      name: toolCall.name,
      input: toolArgs,
    })
  }

  const assistantMessage: AssistantMessage = {
    type: 'assistant',
    message: {
      role: 'assistant',
      content: contentBlocks,
      usage: {
        input_tokens: usage.prompt_tokens ?? 0,
        output_tokens: usage.completion_tokens ?? 0,
        prompt_tokens: usage.prompt_tokens ?? 0,
        completion_tokens: usage.completion_tokens ?? 0,
        totalTokens:
          usage.totalTokens ??
          (usage.prompt_tokens || 0) + (usage.completion_tokens || 0),
        reasoningTokens: usage.reasoningTokens,
      },
    },
    costUSD: 0,
    durationMs: Date.now() - startTime,
    uuid: `${Date.now()}-${Math.random().toString(36).slice(2, 11)}` as any,
    responseId,
  }

  return {
    assistantMessage,
    rawResponse: {
      id: responseId,
      content: contentBlocks,
      usage,
    },
  }
}
