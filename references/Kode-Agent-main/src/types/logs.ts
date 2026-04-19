
import { UUID } from 'crypto'

export interface SerializedMessage {
  type: 'user' | 'assistant' | 'progress'
  uuid: UUID
  message?: {
    content: string | Array<{ type: string; text?: string }>
    role: 'user' | 'assistant' | 'system'
  }
  costUSD?: number
  durationMs?: number
  timestamp: string
  cwd?: string
  userType?: string
  sessionId?: string
  version?: string
}

export interface LogOption {
  date: string
  fullPath: string
  value: number

  created: Date
  modified: Date

  firstPrompt: string
  messageCount: number
  messages: SerializedMessage[]

  forkNumber?: number
  sidechainNumber?: number
}

export interface LogListProps {
  context: {
    unmount?: () => void
  }
}
