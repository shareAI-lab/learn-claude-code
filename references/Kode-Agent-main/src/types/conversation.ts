
import { UUID } from 'crypto'
import type { MessageParam } from '@anthropic-ai/sdk/resources/index.mjs'
import type { Message as APIAssistantMessage } from '@anthropic-ai/sdk/resources/index.mjs'

export type Message = UserMessage | AssistantMessage | ProgressMessage

export interface UserMessage {
  message: MessageParam
  type: 'user'
  uuid: UUID
  toolUseResult?: any
  options?: {
    isKodingRequest?: boolean
    kodingContext?: string
  }
}

export interface AssistantMessage {
  costUSD: number
  durationMs: number
  message: APIAssistantMessage
  type: 'assistant'
  uuid: UUID
  isApiErrorMessage?: boolean
}

export interface ProgressMessage {
  content: AssistantMessage
  normalizedMessages: any[]
  siblingToolUseIDs: Set<string>
  tools: any[]
  toolUseID: string
  type: 'progress'
  uuid: UUID
}
