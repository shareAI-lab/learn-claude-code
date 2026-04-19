import { OpenAIAdapter, StreamingEvent, normalizeTokens } from './openaiAdapter'
import {
  UnifiedRequestParams,
  UnifiedResponse,
  ReasoningStreamingContext,
} from '@kode-types/modelCapabilities'
import { Tool, getToolDescription } from '@tool'
import { zodToJsonSchema } from 'zod-to-json-schema'
import { processResponsesStream } from './responsesStreaming'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

export class ResponsesAPIAdapter extends OpenAIAdapter {
  createRequest(params: UnifiedRequestParams): any {
    const {
      messages,
      systemPrompt,
      tools,
      maxTokens,
      reasoningEffort,
      stopSequences,
    } = params

    const request: any = {
      model: this.modelProfile.modelName,
      input: this.convertMessagesToInput(messages),
      instructions: this.buildInstructions(systemPrompt),
    }

    const maxTokensField = this.getMaxTokensParam()
    request[maxTokensField] = maxTokens

    if (stopSequences && stopSequences.length > 0) {
      request.stop = stopSequences
    }

    request.stream =
      params.stream !== false && this.capabilities.streaming.supported

    const temperature = this.getTemperature()
    if (temperature !== undefined) {
      request.temperature = temperature
    }

    const include: string[] = []
    if (
      this.capabilities.parameters.supportsReasoningEffort &&
      (this.shouldIncludeReasoningEffort() || reasoningEffort)
    ) {
      include.push('reasoning.encrypted_content')
      request.reasoning = {
        effort:
          reasoningEffort || this.modelProfile.reasoningEffort || 'medium',
      }
    }

    if (
      this.capabilities.parameters.supportsVerbosity &&
      this.shouldIncludeVerbosity()
    ) {
      let defaultVerbosity: 'low' | 'medium' | 'high' = 'medium'
      if (params.verbosity) {
        defaultVerbosity = params.verbosity
      } else {
        const modelNameLower = this.modelProfile.modelName.toLowerCase()
        if (modelNameLower.includes('high')) {
          defaultVerbosity = 'high'
        } else if (modelNameLower.includes('low')) {
          defaultVerbosity = 'low'
        }
      }

      request.text = {
        verbosity: defaultVerbosity,
      }
    }

    if (tools && tools.length > 0) {
      request.tools = this.buildTools(tools)
    }

    request.tool_choice = 'auto'

    if (this.capabilities.toolCalling.supportsParallelCalls) {
      request.parallel_tool_calls = true
    }

    request.store = false

    if (
      params.previousResponseId &&
      this.capabilities.stateManagement.supportsPreviousResponseId
    ) {
      request.previous_response_id = params.previousResponseId
    }

    if (include.length > 0) {
      request.include = include
    }

    return request
  }

  buildTools(tools: Tool[]): any[] {
    return tools.map(tool => {
      let parameters: Record<string, unknown> | undefined =
        tool.inputJSONSchema as any

      if (!parameters && tool.inputSchema) {
        const isPlainObject = (obj: any): boolean => {
          return obj !== null && typeof obj === 'object' && !Array.isArray(obj)
        }

        if (
          isPlainObject(tool.inputSchema) &&
          ('type' in (tool.inputSchema as any) ||
            'properties' in (tool.inputSchema as any))
        ) {
          parameters = tool.inputSchema as any
        } else {
          try {
            parameters = zodToJsonSchema(tool.inputSchema as any) as any
          } catch (error) {
            logError(error)
            debugLogger.warn('RESPONSES_API_TOOL_SCHEMA_CONVERSION_FAILED', {
              toolName: tool.name,
              error: error instanceof Error ? error.message : String(error),
            })
            parameters = { type: 'object', properties: {} }
          }
        }
      }

      return {
        type: 'function',
        name: tool.name,
        description: getToolDescription(tool),
        parameters: (parameters as any) || { type: 'object', properties: {} },
      }
    })
  }

  async parseResponse(response: any): Promise<UnifiedResponse> {
    if (response?.body instanceof ReadableStream) {
      const { assistantMessage } = await processResponsesStream(
        this.parseStreamingResponse(response),
        Date.now(),
        response.id ?? `resp_${Date.now()}`,
      )

      const hasToolUseBlocks = assistantMessage.message.content.some(
        (block: any) => block.type === 'tool_use',
      )

      return {
        id: assistantMessage.responseId,
        content: assistantMessage.message.content,
        toolCalls: hasToolUseBlocks ? [] : [],
        usage: this.normalizeUsageForAdapter(assistantMessage.message.usage),
        responseId: assistantMessage.responseId,
      }
    }

    return this.parseNonStreamingResponse(response)
  }

  protected parseNonStreamingResponse(response: any): UnifiedResponse {
    let content = response.output_text || ''

    let reasoningContent = ''
    if (response.output && Array.isArray(response.output)) {
      const messageItems = response.output.filter(
        item => item.type === 'message',
      )
      if (messageItems.length > 0) {
        content = messageItems
          .map(item => {
            if (item.content && Array.isArray(item.content)) {
              return item.content
                .filter(c => c.type === 'text')
                .map(c => c.text)
                .join('\n')
            }
            return item.content || ''
          })
          .filter(Boolean)
          .join('\n\n')
      }

      const reasoningItems = response.output.filter(
        item => item.type === 'reasoning',
      )
      if (reasoningItems.length > 0) {
        reasoningContent = reasoningItems
          .map(item => item.content || '')
          .filter(Boolean)
          .join('\n\n')
      }
    }

    if (reasoningContent) {
      const thinkBlock = `

${reasoningContent}

`
      content = thinkBlock + content
    }

    const toolCalls = this.parseToolCalls(response)

    const contentArray = content
      ? [{ type: 'text', text: content, citations: [] }]
      : [{ type: 'text', text: '', citations: [] }]

    const promptTokens = response.usage?.input_tokens || 0
    const completionTokens = response.usage?.output_tokens || 0
    const totalTokens =
      response.usage?.total_tokens ?? promptTokens + completionTokens

    return {
      id: response.id || `resp_${Date.now()}`,
      content: contentArray,
      toolCalls,
      usage: {
        promptTokens,
        completionTokens,
        reasoningTokens:
          response.usage?.output_tokens_details?.reasoning_tokens,
      },
      responseId: response.id,
    }
  }

  protected async *processStreamingChunk(
    parsed: any,
    responseId: string,
    hasStarted: boolean,
    accumulatedContent: string,
    reasoningContext?: ReasoningStreamingContext,
  ): AsyncGenerator<StreamingEvent> {
    if (parsed.type === 'response.reasoning_summary_part.added') {
      const partIndex = parsed.summary_index || 0

      if (!reasoningContext?.thinkingContent) {
        reasoningContext!.thinkingContent = ''
        reasoningContext!.currentPartIndex = -1
      }

      reasoningContext!.currentPartIndex = partIndex

      if (partIndex > 0 && reasoningContext!.thinkingContent) {
        reasoningContext!.thinkingContent += '\n\n'

        yield {
          type: 'text_delta',
          delta: '\n\n',
          responseId,
        }
      }

      return
    }

    if (parsed.type === 'response.reasoning_summary_text.delta') {
      const delta = parsed.delta || ''

      if (delta && reasoningContext) {
        reasoningContext.thinkingContent += delta

        yield {
          type: 'text_delta',
          delta,
          responseId,
        }
      }

      return
    }

    if (parsed.type === 'response.reasoning_text.delta') {
      const delta = parsed.delta || ''

      if (delta && reasoningContext) {
        reasoningContext.thinkingContent += delta

        yield {
          type: 'text_delta',
          delta,
          responseId,
        }
      }

      return
    }

    if (parsed.type === 'response.output_text.delta') {
      const delta = parsed.delta || ''
      if (delta) {
        const textEvents = this.handleTextDelta(delta, responseId, hasStarted)
        for (const event of textEvents) {
          yield event
        }
      }
    }

    if (parsed.type === 'response.output_item.done') {
      const item = parsed.item || {}
      if (item.type === 'function_call') {
        const callId = item.call_id || item.id
        const name = item.name
        const args = item.arguments

        if (
          typeof callId === 'string' &&
          typeof name === 'string' &&
          typeof args === 'string'
        ) {
          yield {
            type: 'tool_request',
            tool: {
              id: callId,
              name: name,
              input: args,
            },
          }
        }
      }
    }

    if (parsed.usage) {
      const normalizedUsage = normalizeTokens(parsed.usage)

      if (parsed.usage.output_tokens_details?.reasoning_tokens) {
        normalizedUsage.reasoning =
          parsed.usage.output_tokens_details.reasoning_tokens
      }

      yield {
        type: 'usage',
        usage: normalizedUsage,
      }
    }
  }

  protected updateStreamingState(
    parsed: any,
    accumulatedContent: string,
  ): { content?: string; hasStarted?: boolean } {
    const state: { content?: string; hasStarted?: boolean } = {}

    if (parsed.type === 'response.output_text.delta' && parsed.delta) {
      state.content = accumulatedContent + parsed.delta
      state.hasStarted = true
    }

    return state
  }


  protected async parseStreamingOpenAIResponse(
    response: any,
  ): Promise<{ assistantMessage: any; rawResponse: any }> {
    const { processResponsesStream } = await import('./responsesStreaming')

    return await processResponsesStream(
      this.parseStreamingResponse(response),
      Date.now(),
      response.id ?? `resp_${Date.now()}`,
    )
  }

  protected normalizeUsageForAdapter(usage?: any) {
    const baseUsage = super.normalizeUsageForAdapter(usage)

    return {
      ...baseUsage,
      reasoningTokens: usage?.output_tokens_details?.reasoning_tokens ?? 0,
    }
  }

  private convertMessagesToInput(messages: any[]): any[] {
    const inputItems = []

    for (const message of messages) {
      const role = message.role

      if (role === 'tool') {
        const callId = message.tool_call_id || message.id
        if (typeof callId === 'string' && callId) {
          let content = message.content || ''
          if (Array.isArray(content)) {
            const texts = []
            for (const part of content) {
              if (typeof part === 'object' && part !== null) {
                const t = part.text || part.content
                if (typeof t === 'string' && t) {
                  texts.push(t)
                }
              }
            }
            content = texts.join('\n')
          }
          if (typeof content === 'string') {
            inputItems.push({
              type: 'function_call_output',
              call_id: callId,
              output: content,
            })
          }
        }
        continue
      }

      if (role === 'assistant' && Array.isArray(message.tool_calls)) {
        for (const tc of message.tool_calls) {
          if (typeof tc !== 'object' || tc === null) {
            continue
          }
          const tcType = tc.type || 'function'
          if (tcType !== 'function') {
            continue
          }
          const callId = tc.id || tc.call_id
          const fn = tc.function
          const name = typeof fn === 'object' && fn !== null ? fn.name : null
          const args =
            typeof fn === 'object' && fn !== null ? fn.arguments : null

          if (
            typeof callId === 'string' &&
            typeof name === 'string' &&
            typeof args === 'string'
          ) {
            inputItems.push({
              type: 'function_call',
              name: name,
              arguments: args,
              call_id: callId,
            })
          }
        }
        continue
      }

      const content = message.content || ''
      const contentItems = []

      if (Array.isArray(content)) {
        for (const part of content) {
          if (typeof part !== 'object' || part === null) continue
          const ptype = part.type
          if (ptype === 'text') {
            const text = part.text || part.content || ''
            if (typeof text === 'string' && text) {
              const kind = role === 'assistant' ? 'output_text' : 'input_text'
              contentItems.push({ type: kind, text: text })
            }
          } else if (ptype === 'image_url') {
            const image = part.image_url
            const url =
              typeof image === 'object' && image !== null ? image.url : image
            if (typeof url === 'string' && url) {
              contentItems.push({ type: 'input_image', image_url: url })
            }
          }
        }
      } else if (typeof content === 'string' && content) {
        const kind = role === 'assistant' ? 'output_text' : 'input_text'
        contentItems.push({ type: kind, text: content })
      }

      if (contentItems.length) {
        const roleOut = role === 'assistant' ? 'assistant' : 'user'
        inputItems.push({
          type: 'message',
          role: roleOut,
          content: contentItems,
        })
      }
    }

    return inputItems
  }

  private buildInstructions(systemPrompt: string[]): string {
    const systemContent = systemPrompt
      .filter(content => content.trim())
      .join('\n\n')

    return systemContent
  }

  private parseToolCalls(response: any): any[] {
    if (!response.output || !Array.isArray(response.output)) {
      return []
    }

    const toolCalls = []

    for (const item of response.output) {
      if (item.type === 'function_call') {
        const callId = item.call_id || item.id
        const name = item.name || ''
        const args = item.arguments || '{}'

        if (
          typeof callId === 'string' &&
          typeof name === 'string' &&
          typeof args === 'string'
        ) {
          toolCalls.push({
            id: callId,
            type: 'function',
            function: {
              name: name,
              arguments: args,
            },
          })
        }
      } else if (item.type === 'tool_call') {
        const callId =
          item.id || `tool_${Math.random().toString(36).substring(2, 15)}`
        toolCalls.push({
          id: callId,
          type: 'tool_call',
          name: item.name,
          arguments: item.arguments,
        })
      }
    }

    return toolCalls
  }

  private applyReasoningToMessage(
    message: any,
    reasoningSummaryText: string,
    reasoningFullText: string,
  ): any {
    const rtxtParts = []
    if (
      typeof reasoningSummaryText === 'string' &&
      reasoningSummaryText.trim()
    ) {
      rtxtParts.push(reasoningSummaryText)
    }
    if (typeof reasoningFullText === 'string' && reasoningFullText.trim()) {
      rtxtParts.push(reasoningFullText)
    }
    const rtxt = rtxtParts.filter(p => p).join('\n\n')
    if (rtxt) {
      const thinkBlock = `<think>\n${rtxt}\n</think>\n`
      const contentText = message.content || ''
      message.content =
        thinkBlock + (typeof contentText === 'string' ? contentText : '')
    }
    return message
  }
}
