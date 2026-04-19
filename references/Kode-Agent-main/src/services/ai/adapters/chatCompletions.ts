import { OpenAIAdapter, StreamingEvent, normalizeTokens } from './openaiAdapter'
import {
  UnifiedRequestParams,
  UnifiedResponse,
  ReasoningStreamingContext,
} from '@kode-types/modelCapabilities'
import { Tool, getToolDescription } from '@tool'
import { zodToJsonSchema } from 'zod-to-json-schema'
import { setRequestStatus } from '@utils/session/requestStatus'

export class ChatCompletionsAdapter extends OpenAIAdapter {
  createRequest(params: UnifiedRequestParams): any {
    const { messages, systemPrompt, tools, maxTokens, stream } = params

    const fullMessages = this.buildMessages(systemPrompt, messages)

    const request: any = {
      model: this.modelProfile.modelName,
      messages: fullMessages,
      [this.getMaxTokensParam()]: maxTokens,
      temperature: this.getTemperature(),
    }

    if (tools && tools.length > 0) {
      request.tools = this.buildTools(tools)
      request.tool_choice = 'auto'
    }

    if (
      this.capabilities.parameters.supportsReasoningEffort &&
      params.reasoningEffort
    ) {
      request.reasoning_effort = params.reasoningEffort
    }

    if (this.capabilities.parameters.supportsVerbosity && params.verbosity) {
      request.verbosity = params.verbosity
    }

    if (stream && this.capabilities.streaming.supported) {
      request.stream = true
      if (this.capabilities.streaming.includesUsage) {
        request.stream_options = {
          include_usage: true,
        }
      }
    }

    if (this.capabilities.parameters.temperatureMode === 'fixed_one') {
      delete request.temperature
    }

    if (!this.capabilities.streaming.supported) {
      delete request.stream
      delete request.stream_options
    }

    return request
  }

  buildTools(tools: Tool[]): any[] {
    return tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: getToolDescription(tool),
        parameters:
          tool.inputJSONSchema ||
          (zodToJsonSchema(tool.inputSchema as any) as any),
      },
    }))
  }


  protected parseNonStreamingResponse(response: any): UnifiedResponse {
    if (!response || typeof response !== 'object') {
      throw new Error('Invalid response: response must be an object')
    }

    const choice = response.choices?.[0]
    if (!choice) {
      throw new Error('Invalid response: no choices found in response')
    }

    const message = choice.message || {}
    const content = typeof message.content === 'string' ? message.content : ''
    const toolCalls = Array.isArray(message.tool_calls)
      ? message.tool_calls
      : []

    const usage = response.usage || {}
    const promptTokens = Number(usage.prompt_tokens) || 0
    const completionTokens = Number(usage.completion_tokens) || 0

    return {
      id: response.id || `chatcmpl_${Date.now()}`,
      content,
      toolCalls,
      usage: {
        promptTokens,
        completionTokens,
      },
    }
  }

  private buildMessages(systemPrompt: string[], messages: any[]): any[] {
    const systemMessages = systemPrompt.map(prompt => ({
      role: 'system',
      content: prompt,
    }))

    const normalizedMessages = this.normalizeToolMessages(messages)

    return [...systemMessages, ...normalizedMessages]
  }

  private normalizeToolMessages(messages: any[]): any[] {
    if (!Array.isArray(messages)) {
      return []
    }

    return messages.map(msg => {
      if (!msg || typeof msg !== 'object') {
        return msg
      }

      if (msg.role === 'tool') {
        if (Array.isArray(msg.content)) {
          return {
            ...msg,
            content:
              msg.content
                .map(c => c?.text || '')
                .filter(Boolean)
                .join('\n\n') || '(empty content)',
          }
        } else if (typeof msg.content !== 'string') {
          return {
            ...msg,
            content:
              msg.content === null || msg.content === undefined
                ? '(empty content)'
                : JSON.stringify(msg.content),
          }
        }
      }
      return msg
    })
  }

  protected async *processStreamingChunk(
    parsed: any,
    responseId: string,
    hasStarted: boolean,
    accumulatedContent: string,
    reasoningContext?: ReasoningStreamingContext,
  ): AsyncGenerator<StreamingEvent> {
    if (!parsed || typeof parsed !== 'object') {
      return
    }

    const choice = parsed.choices?.[0]
    if (choice?.delta && typeof choice.delta === 'object') {
      const delta =
        typeof choice.delta.content === 'string' ? choice.delta.content : ''
      const reasoningDelta =
        typeof choice.delta.reasoning_content === 'string'
          ? choice.delta.reasoning_content
          : ''
      const fullDelta = delta + reasoningDelta

      if (fullDelta) {
        const textEvents = this.handleTextDelta(
          fullDelta,
          responseId,
          hasStarted,
        )
        for (const event of textEvents) {
          yield event
        }
      }
    }

    if (choice?.delta?.tool_calls && Array.isArray(choice.delta.tool_calls)) {
      for (const toolCall of choice.delta.tool_calls) {
        if (toolCall && typeof toolCall === 'object') {
          yield {
            type: 'tool_request',
            tool: {
              id: toolCall.id || `tool_${Date.now()}`,
              name: toolCall.function?.name || 'unknown',
              input: toolCall.function?.arguments || '{}',
            },
          }
        }
      }
    }

    if (parsed.usage && typeof parsed.usage === 'object') {
      const normalizedUsage = normalizeTokens(parsed.usage)
      this.updateCumulativeUsage(normalizedUsage)
      yield {
        type: 'usage',
        usage: { ...this.cumulativeUsage },
      }
    }
  }

  protected updateStreamingState(
    parsed: any,
    accumulatedContent: string,
  ): { content?: string; hasStarted?: boolean } {
    const state: { content?: string; hasStarted?: boolean } = {}

    const choice = parsed.choices?.[0]
    if (choice?.delta) {
      const delta = choice.delta.content || ''
      const reasoningDelta = choice.delta.reasoning_content || ''
      const fullDelta = delta + reasoningDelta

      if (fullDelta) {
        state.content = accumulatedContent + fullDelta
        state.hasStarted = true
      }
    }

    return state
  }

  protected async parseStreamingOpenAIResponse(
    response: any,
    signal?: AbortSignal,
  ): Promise<{ assistantMessage: any; rawResponse: any }> {
    const contentBlocks: any[] = []
    const usage: any = {
      prompt_tokens: 0,
      completion_tokens: 0,
    }

    let responseId = response.id || `chatcmpl_${Date.now()}`
    const pendingToolCalls: any[] = []
    let hasMarkedStreaming = false

    try {
      this.resetCumulativeUsage()

      for await (const event of this.parseStreamingResponse(response)) {
        if (signal?.aborted) {
          throw new Error('Stream aborted by user')
        }

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
            contentBlocks.push({
              type: 'text',
              text: event.delta,
              citations: [],
            })
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
          usage.totalTokens =
            event.usage.total ?? event.usage.input + event.usage.output
          usage.promptTokens = event.usage.input
          usage.completionTokens = event.usage.output
          continue
        }
      }
    } catch (error) {
      if (signal?.aborted) {
        const assistantMessage = {
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
                (usage.prompt_tokens || 0) + (usage.completion_tokens || 0),
            },
          },
          costUSD: 0,
          durationMs: Date.now() - Date.now(),
          uuid: `${Date.now()}-${Math.random().toString(36).slice(2, 11)}` as any,
          responseId,
        }

        return {
          assistantMessage,
          rawResponse: {
            id: responseId,
            content: contentBlocks,
            usage,
            aborted: true,
          },
        }
      }
      throw error
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

    const assistantMessage = {
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
        },
      },
      costUSD: 0,
      durationMs: Date.now() - Date.now(),
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

  protected normalizeUsageForAdapter(usage?: any) {
    return super.normalizeUsageForAdapter(usage)
  }
}
