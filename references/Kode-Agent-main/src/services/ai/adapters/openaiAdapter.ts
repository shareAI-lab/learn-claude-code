import { ModelAPIAdapter, StreamingEvent, normalizeTokens } from './base'
import {
  UnifiedRequestParams,
  UnifiedResponse,
  ModelCapabilities,
  ReasoningStreamingContext,
} from '@kode-types/modelCapabilities'
import { ModelProfile } from '@utils/config'
import { Tool, getToolDescription } from '@tool'
import { zodToJsonSchema } from 'zod-to-json-schema'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

export { normalizeTokens, type StreamingEvent }

export abstract class OpenAIAdapter extends ModelAPIAdapter {
  constructor(capabilities: ModelCapabilities, modelProfile: ModelProfile) {
    super(capabilities, modelProfile)
  }

  async parseResponse(response: any): Promise<UnifiedResponse> {
    if (response?.body instanceof ReadableStream) {
      const { assistantMessage } =
        await this.parseStreamingOpenAIResponse(response)

      return {
        id: assistantMessage.responseId,
        content: assistantMessage.message.content,
        toolCalls: assistantMessage.message.content
          .filter((block: any) => block.type === 'tool_use')
          .map((block: any) => ({
            id: block.id,
            type: 'function',
            function: {
              name: block.name,
              arguments: JSON.stringify(block.input),
            },
          })),
        usage: this.normalizeUsageForAdapter(assistantMessage.message.usage),
        responseId: assistantMessage.responseId,
      }
    }

    return this.parseNonStreamingResponse(response)
  }

  async *parseStreamingResponse(response: any): AsyncGenerator<StreamingEvent> {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    let responseId = response.id || `openai_${Date.now()}`
    let hasStarted = false
    let accumulatedContent = ''

    const reasoningContext: ReasoningStreamingContext = {
      thinkOpen: false,
      thinkClosed: false,
      sawAnySummary: false,
      pendingSummaryParagraph: false,
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.trim()) {
            const parsed = this.parseSSEChunk(line)
            if (parsed) {
              if (parsed.id) {
                responseId = parsed.id
              }

              yield* this.processStreamingChunk(
                parsed,
                responseId,
                hasStarted,
                accumulatedContent,
                reasoningContext,
              )

              const stateUpdate = this.updateStreamingState(
                parsed,
                accumulatedContent,
              )
              if (stateUpdate.content) accumulatedContent = stateUpdate.content
              if (stateUpdate.hasStarted) hasStarted = true
            }
          }
        }
      }
    } catch (error) {
      logError(error)
      debugLogger.warn('OPENAI_ADAPTER_STREAM_READ_ERROR', {
        error: error instanceof Error ? error.message : String(error),
      })
      yield {
        type: 'error',
        error: error instanceof Error ? error.message : String(error),
      }
    } finally {
      reader.releaseLock()
    }

    const finalContent = accumulatedContent
      ? [{ type: 'text', text: accumulatedContent, citations: [] }]
      : [{ type: 'text', text: '', citations: [] }]

    yield {
      type: 'message_stop',
      message: {
        id: responseId,
        role: 'assistant',
        content: finalContent,
        responseId,
      },
    }
  }

  protected parseSSEChunk(line: string): any | null {
    if (line.startsWith('data: ')) {
      const data = line.slice(6).trim()
      if (data === '[DONE]') {
        return null
      }
      if (data) {
        try {
          return JSON.parse(data)
        } catch (error) {
          logError(error)
          debugLogger.warn('OPENAI_ADAPTER_SSE_PARSE_ERROR', {
            error: error instanceof Error ? error.message : String(error),
          })
          return null
        }
      }
    }
    return null
  }

  protected handleTextDelta(
    delta: string,
    responseId: string,
    hasStarted: boolean,
  ): StreamingEvent[] {
    const events: StreamingEvent[] = []

    if (!hasStarted && delta) {
      events.push({
        type: 'message_start',
        message: {
          role: 'assistant',
          content: [],
        },
        responseId,
      })
    }

    if (delta) {
      events.push({
        type: 'text_delta',
        delta,
        responseId,
      })
    }

    return events
  }

  protected normalizeUsageForAdapter(usage?: any) {
    if (!usage) {
      return {
        input_tokens: 0,
        output_tokens: 0,
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0,
        reasoningTokens: 0,
      }
    }

    const inputTokens =
      usage.input_tokens ?? usage.prompt_tokens ?? usage.promptTokens ?? 0
    const outputTokens =
      usage.output_tokens ??
      usage.completion_tokens ??
      usage.completionTokens ??
      0

    return {
      ...usage,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      promptTokens: inputTokens,
      completionTokens: outputTokens,
      totalTokens: usage.totalTokens ?? inputTokens + outputTokens,
      reasoningTokens: usage.reasoningTokens ?? 0,
    }
  }

  protected abstract processStreamingChunk(
    parsed: any,
    responseId: string,
    hasStarted: boolean,
    accumulatedContent: string,
    reasoningContext?: ReasoningStreamingContext,
  ): AsyncGenerator<StreamingEvent>

  protected abstract updateStreamingState(
    parsed: any,
    accumulatedContent: string,
  ): { content?: string; hasStarted?: boolean }

  protected abstract parseNonStreamingResponse(response: any): UnifiedResponse

  protected abstract parseStreamingOpenAIResponse(
    response: any,
  ): Promise<{ assistantMessage: any; rawResponse: any }>

  public buildTools(tools: Tool[]): any[] {
    return tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: getToolDescription(tool),
        parameters: zodToJsonSchema(tool.inputSchema as any) as any,
      },
    }))
  }
}
