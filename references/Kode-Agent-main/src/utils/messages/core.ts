import { createHash, randomUUID, UUID } from 'crypto'
import { AssistantMessage, Message, ProgressMessage, UserMessage } from '@query'
import { last, memoize } from 'lodash-es'
import type { Tool } from '@tool'
import { NO_CONTENT_MESSAGE } from '@services/llmConstants'
import {
  ImageBlockParam,
  TextBlockParam,
  ToolResultBlockParam,
  ToolUseBlockParam,
  Message as APIMessage,
  ContentBlockParam,
  ContentBlock,
} from '@anthropic-ai/sdk/resources/index.mjs'

export const INTERRUPT_MESSAGE = '[Request interrupted by user]'
export const INTERRUPT_MESSAGE_FOR_TOOL_USE =
  '[Request interrupted by user for tool use]'
export const CANCEL_MESSAGE =
  "The user doesn't want to take this action right now. STOP what you are doing and wait for the user to tell you how to proceed."
export const REJECT_MESSAGE =
  "The user doesn't want to proceed with this tool use. The tool use was rejected (eg. if it was a file edit, the new_string was NOT written to the file). STOP what you are doing and wait for the user to tell you how to proceed."
export const REJECT_MESSAGE_WITH_FEEDBACK_PREFIX = `The user doesn't want to proceed with this tool use. The tool use was rejected (eg. if it was a file edit, the new_string was NOT written to the file). To tell you how to proceed, the user said:\n`
export const REJECTED_PLAN_PREFIX = `The agent proposed a plan that was rejected by the user. The user chose to stay in plan mode rather than proceed with implementation.\n\nRejected plan:\n`
export const NO_RESPONSE_REQUESTED = 'No response requested.'

export const SYNTHETIC_ASSISTANT_MESSAGES = new Set([
  INTERRUPT_MESSAGE,
  INTERRUPT_MESSAGE_FOR_TOOL_USE,
  CANCEL_MESSAGE,
  REJECT_MESSAGE,
  NO_RESPONSE_REQUESTED,
])

function stableUuidFromSeed(seed: string): UUID {
  const hex = createHash('sha256').update(seed).digest('hex').slice(0, 32)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}` as UUID
}

function baseCreateAssistantMessage(
  content: ContentBlock[],
  extra?: Partial<AssistantMessage>,
): AssistantMessage {
  return {
    type: 'assistant',
    costUSD: 0,
    durationMs: 0,
    uuid: randomUUID(),
    message: {
      id: randomUUID(),
      model: '<synthetic>',
      role: 'assistant',
      stop_reason: 'stop_sequence',
      stop_sequence: '',
      type: 'message',
      usage: {
        input_tokens: 0,
        output_tokens: 0,
        cache_creation_input_tokens: 0,
        cache_read_input_tokens: 0,
      },
      content,
    },
    ...extra,
  }
}

export function createAssistantMessage(content: string): AssistantMessage {
  return baseCreateAssistantMessage([
    {
      type: 'text' as const,
      text: content === '' ? NO_CONTENT_MESSAGE : content,
      citations: [],
    },
  ])
}

export function createAssistantAPIErrorMessage(
  content: string,
): AssistantMessage {
  return baseCreateAssistantMessage(
    [
      {
        type: 'text' as const,
        text: content === '' ? NO_CONTENT_MESSAGE : content,
        citations: [],
      },
    ],
    { isApiErrorMessage: true },
  )
}

export type FullToolUseResult = {
  data: unknown
  resultForAssistant: ToolResultBlockParam['content']
  newMessages?: Message[]
  contextModifier?: { modifyContext: (ctx: any) => any }
}

export function createUserMessage(
  content: string | ContentBlockParam[],
  toolUseResult?: FullToolUseResult,
): UserMessage {
  const m: UserMessage = {
    type: 'user',
    message: {
      role: 'user',
      content,
    },
    uuid: randomUUID(),
    toolUseResult,
  }
  return m
}

export function createProgressMessage(
  toolUseID: string,
  siblingToolUseIDs: Set<string>,
  content: AssistantMessage,
  normalizedMessages: NormalizedMessage[],
  tools: Tool[],
): ProgressMessage {
  return {
    type: 'progress',
    content,
    normalizedMessages,
    siblingToolUseIDs,
    tools,
    toolUseID,
    uuid: randomUUID(),
  }
}

export function createToolResultStopMessage(
  toolUseID: string,
): ToolResultBlockParam {
  return {
    type: 'tool_result',
    content: CANCEL_MESSAGE,
    is_error: true,
    tool_use_id: toolUseID,
  }
}

export function extractTagFromMessage(
  message: Message,
  tagName: string,
): string | null {
  if (message.type === 'progress') {
    return null
  }
  if (typeof message.message.content !== 'string') {
    return null
  }
  return extractTag(message.message.content, tagName)
}

export function extractTag(html: string, tagName: string): string | null {
  if (!html.trim() || !tagName.trim()) {
    return null
  }

  const escapedTag = tagName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

  const pattern = new RegExp(
    `<${escapedTag}(?:\\s+[^>]*)?>` + '([\\s\\S]*?)' + `<\\/${escapedTag}>`,
    'gi',
  )

  let match
  let depth = 0
  let lastIndex = 0
  const openingTag = new RegExp(`<${escapedTag}(?:\\s+[^>]*?)?>`, 'gi')
  const closingTag = new RegExp(`<\\/${escapedTag}>`, 'gi')

  while ((match = pattern.exec(html)) !== null) {
    const content = match[1]
    const beforeMatch = html.slice(lastIndex, match.index)

    depth = 0

    openingTag.lastIndex = 0
    while (openingTag.exec(beforeMatch) !== null) {
      depth++
    }

    closingTag.lastIndex = 0
    while (closingTag.exec(beforeMatch) !== null) {
      depth--
    }

    if (depth === 0 && content) {
      return content
    }

    lastIndex = match.index + match[0].length
  }

  return null
}

export function isNotEmptyMessage(message: Message): boolean {
  if (message.type === 'progress') {
    return true
  }

  if (typeof message.message.content === 'string') {
    return message.message.content.trim().length > 0
  }

  if (message.message.content.length === 0) {
    return false
  }

  if (message.message.content.length > 1) {
    return true
  }

  if (message.message.content[0]!.type !== 'text') {
    return true
  }

  return (
    message.message.content[0]!.text.trim().length > 0 &&
    message.message.content[0]!.text !== NO_CONTENT_MESSAGE &&
    message.message.content[0]!.text !== INTERRUPT_MESSAGE_FOR_TOOL_USE
  )
}

type NormalizedUserMessage = {
  message: {
    content: [
      | TextBlockParam
      | ImageBlockParam
      | ToolUseBlockParam
      | ToolResultBlockParam,
    ]
    role: 'user'
  }
  type: 'user'
  uuid: UUID
}

export type NormalizedMessage =
  | NormalizedUserMessage
  | AssistantMessage
  | ProgressMessage

export function normalizeMessages(messages: Message[]): NormalizedMessage[] {
  return messages.flatMap(message => {
    if (message.type === 'progress') {
      return [message] as NormalizedMessage[]
    }
    if (typeof message.message.content === 'string') {
      return [message] as NormalizedMessage[]
    }
    const contentBlocks = message.message.content.filter(
      block =>
        !(
          block.type === 'thinking' &&
          (typeof (block as any).thinking !== 'string' ||
            (block as any).thinking.trim().length === 0)
        ),
    )

    return contentBlocks.map((block, blockIndex) => {
      switch (message.type) {
        case 'assistant':
          const baseSeed = String(
            (message as any).uuid ??
              (message as any).message?.id ??
              randomUUID(),
          )
          return {
            type: 'assistant',
            uuid: stableUuidFromSeed(`${baseSeed}:${blockIndex}`),
            message: {
              ...message.message,
              content: [block],
            },
            costUSD:
              (message as AssistantMessage).costUSD / contentBlocks.length,
            durationMs: (message as AssistantMessage).durationMs,
          } as NormalizedMessage
        case 'user':
          return message as NormalizedUserMessage
      }
    })
  })
}

type ToolUseRequestMessage = AssistantMessage & {
  message: { content: any[] }
}

type ToolUseLikeBlockParam = ToolUseBlockParam & {
  type: 'tool_use' | 'server_tool_use' | 'mcp_tool_use'
}

function isToolUseLikeBlockParam(block: any): block is ToolUseLikeBlockParam {
  return (
    block &&
    typeof block === 'object' &&
    (block.type === 'tool_use' ||
      block.type === 'server_tool_use' ||
      block.type === 'mcp_tool_use') &&
    typeof block.id === 'string'
  )
}

function isToolUseRequestMessage(
  message: Message,
): message is ToolUseRequestMessage {
  return (
    message.type === 'assistant' &&
    'costUSD' in message &&
    message.message.content.some(isToolUseLikeBlockParam)
  )
}

export function reorderMessages(
  messages: NormalizedMessage[],
): NormalizedMessage[] {
  const ms: NormalizedMessage[] = []
  const toolUseMessages: ToolUseRequestMessage[] = []

  for (const message of messages) {
    if (isToolUseRequestMessage(message)) {
      toolUseMessages.push(message)
    }

    if (message.type === 'progress') {
      const existingProgressMessage = ms.find(
        _ => _.type === 'progress' && _.toolUseID === message.toolUseID,
      )
      if (existingProgressMessage) {
        ms[ms.indexOf(existingProgressMessage)] = message
        continue
      }
      const toolUseMessage = toolUseMessages.find(
        _ => _.message.content[0]?.id === message.toolUseID,
      )
      if (toolUseMessage) {
        ms.splice(ms.indexOf(toolUseMessage) + 1, 0, message)
        continue
      }
    }

    if (
      message.type === 'user' &&
      Array.isArray(message.message.content) &&
      message.message.content[0]?.type === 'tool_result'
    ) {
      const toolUseID = (message.message.content[0] as ToolResultBlockParam)
        ?.tool_use_id

      const lastProgressMessage = ms.find(
        _ => _.type === 'progress' && _.toolUseID === toolUseID,
      )
      if (lastProgressMessage) {
        ms.splice(ms.indexOf(lastProgressMessage) + 1, 0, message)
        continue
      }

      const toolUseMessage = toolUseMessages.find(
        _ => _.message.content[0]?.id === toolUseID,
      )
      if (toolUseMessage) {
        ms.splice(ms.indexOf(toolUseMessage) + 1, 0, message)
        continue
      }
    }

    else {
      ms.push(message)
    }
  }

  return ms
}

const getToolResultIDs = memoize(
  (normalizedMessages: NormalizedMessage[]): { [toolUseID: string]: boolean } =>
    Object.fromEntries(
      normalizedMessages.flatMap(_ =>
        _.type === 'user' && _.message.content[0]?.type === 'tool_result'
          ? [
              [
                _.message.content[0]!.tool_use_id,
                _.message.content[0]!.is_error ?? false,
              ],
            ]
          : ([] as [string, boolean][]),
      ),
    ),
)

export function getUnresolvedToolUseIDs(
  normalizedMessages: NormalizedMessage[],
): Set<string> {
  const toolResults = getToolResultIDs(normalizedMessages)
  return new Set(
    normalizedMessages
      .filter(
        (
          _,
        ): _ is AssistantMessage & {
          message: { content: [ToolUseLikeBlockParam] }
        } =>
          _.type === 'assistant' &&
          Array.isArray(_.message.content) &&
          isToolUseLikeBlockParam(_.message.content[0]) &&
          !(_.message.content[0].id in toolResults),
      )
      .map(_ => _.message.content[0].id),
  )
}

export function getInProgressToolUseIDs(
  normalizedMessages: NormalizedMessage[],
): Set<string> {
  const unresolvedToolUseIDs = getUnresolvedToolUseIDs(normalizedMessages)

  function isQueuedWaitingProgressMessage(message: NormalizedMessage): boolean {
    if (message.type !== 'progress') return false
    const firstBlock = message.content.message.content[0]
    if (!firstBlock || firstBlock.type !== 'text') return false
    const rawText = String(firstBlock.text ?? '')
    const text = rawText.startsWith('<tool-progress>')
      ? (extractTag(rawText, 'tool-progress') ?? rawText)
      : rawText
    return text.trim() === 'Waiting…'
  }

  const toolUseIDsThatHaveProgressMessages = new Set(
    normalizedMessages
      .filter(
        (_): _ is ProgressMessage =>
          _.type === 'progress' && !isQueuedWaitingProgressMessage(_),
      )
      .map(_ => _.toolUseID),
  )
  return new Set(
    (
      normalizedMessages.filter(_ => {
        if (_.type !== 'assistant') {
          return false
        }
        const firstBlock = _.message.content[0]
        if (!isToolUseLikeBlockParam(firstBlock)) return false
        const toolUseID = firstBlock.id
        if (toolUseID === unresolvedToolUseIDs.values().next().value) {
          return true
        }

        if (
          toolUseIDsThatHaveProgressMessages.has(toolUseID) &&
          unresolvedToolUseIDs.has(toolUseID)
        ) {
          return true
        }

        return false
      }) as AssistantMessage[]
    ).map(_ => (_.message.content[0]! as ToolUseBlockParam).id),
  )
}

export function getErroredToolUseMessages(
  normalizedMessages: NormalizedMessage[],
): AssistantMessage[] {
  const toolResults = getToolResultIDs(normalizedMessages)
  return normalizedMessages.filter(
    _ =>
      _.type === 'assistant' &&
      Array.isArray(_.message.content) &&
      isToolUseLikeBlockParam(_.message.content[0]) &&
      _.message.content[0].id in toolResults &&
      toolResults[_.message.content[0].id],
  ) as AssistantMessage[]
}

export function normalizeMessagesForAPI(
  messages: Message[],
): (UserMessage | AssistantMessage)[] {
  function isSyntheticApiErrorMessage(message: Message): boolean {
    return (
      message.type === 'assistant' &&
      message.isApiErrorMessage === true &&
      message.message.model === '<synthetic>'
    )
  }

  function normalizeUserContent(
    content: UserMessage['message']['content'],
  ): ContentBlockParam[] {
    if (typeof content === 'string') {
      return [{ type: 'text', text: content }]
    }
    return content
  }

  function toolResultsFirst(content: ContentBlockParam[]): ContentBlockParam[] {
    const toolResults: ContentBlockParam[] = []
    const rest: ContentBlockParam[] = []
    for (const block of content) {
      if (block.type === 'tool_result') {
        toolResults.push(block)
      } else {
        rest.push(block)
      }
    }
    return [...toolResults, ...rest]
  }

  function mergeUserMessages(
    base: UserMessage,
    next: UserMessage,
  ): UserMessage {
    const baseBlocks = normalizeUserContent(base.message.content)
    const nextBlocks = normalizeUserContent(next.message.content)
    return {
      ...base,
      message: {
        ...base.message,
        content: toolResultsFirst([...baseBlocks, ...nextBlocks]),
      },
    }
  }

  function isUserToolResultMessage(message: Message): message is UserMessage {
    if (message.type !== 'user') return false
    if (!Array.isArray(message.message.content)) return false
    return message.message.content.some(block => block.type === 'tool_result')
  }

  const result: (UserMessage | AssistantMessage)[] = []
  for (const message of messages) {
    if (message.type === 'progress') continue
    if (isSyntheticApiErrorMessage(message)) continue

    switch (message.type) {
      case 'user': {
        const prev = last(result)
        if (prev?.type === 'user') {
          result[result.indexOf(prev)] = mergeUserMessages(prev, message)
        } else {
          result.push(message)
        }
        break
      }
      case 'assistant': {
        let merged = false
        for (let i = result.length - 1; i >= 0; i--) {
          const prev = result[i]
          if (prev.type !== 'assistant' && !isUserToolResultMessage(prev)) {
            break
          }
          if (prev.type === 'assistant') {
            if (prev.message.id === message.message.id) {
              result[i] = {
                ...prev,
                message: {
                  ...prev.message,
                  content: [
                    ...(Array.isArray(prev.message.content)
                      ? prev.message.content
                      : []),
                    ...(Array.isArray(message.message.content)
                      ? message.message.content
                      : []),
                  ],
                },
              }
              merged = true
            }
            break
          }
        }
        if (!merged) {
          result.push(message)
        }
        break
      }
    }
  }

  return result
}

export function normalizeContentFromAPI(
  content: APIMessage['content'],
): APIMessage['content'] {
  const filteredContent = content.filter(
    _ => _.type !== 'text' || _.text.trim().length > 0,
  )

  if (filteredContent.length === 0) {
    return [{ type: 'text', text: NO_CONTENT_MESSAGE, citations: [] }]
  }

  return filteredContent
}

export function isEmptyMessageText(text: string): boolean {
  return (
    stripSystemMessages(text).trim() === '' ||
    text.trim() === NO_CONTENT_MESSAGE
  )
}

/**
 * Filter messages to get user text messages for the undo menu (2xESC).
 * Excludes:
 * - Assistant messages
 * - User messages that only contain tool_result blocks
 */
export function filterUserTextMessagesForUndo(
  messages: (UserMessage | AssistantMessage)[],
): UserMessage[] {
  return messages.filter((msg): msg is UserMessage => {
    if (msg.type !== 'user') return false
    if (!Array.isArray(msg.message.content)) return true
    return !msg.message.content.every(block => block.type === 'tool_result')
  })
}
const STRIPPED_TAGS = [
  'commit_analysis',
  'context',
  'function_analysis',
  'pr_analysis',
]

export function stripSystemMessages(content: string): string {
  const regex = new RegExp(`<(${STRIPPED_TAGS.join('|')})>.*?</\\1>\n?`, 'gs')
  return content.replace(regex, '').trim()
}

export function getToolUseID(message: NormalizedMessage): string | null {
  switch (message.type) {
    case 'assistant':
      return isToolUseLikeBlockParam(message.message.content[0])
        ? message.message.content[0].id
        : null
    case 'user':
      if (message.message.content[0]?.type !== 'tool_result') {
        return null
      }
      return message.message.content[0].tool_use_id
    case 'progress':
      return message.toolUseID
  }
}

export function getLastAssistantMessageId(
  messages: Message[],
): string | undefined {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message && message.type === 'assistant') {
      return message.message.id
    }
  }
  return undefined
}
