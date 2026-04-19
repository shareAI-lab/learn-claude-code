interface ConversationState {
  previousResponseId?: string
  lastUpdate: number
}

class ResponseStateManager {
  private conversationStates = new Map<string, ConversationState>()

  private readonly CLEANUP_INTERVAL = 60 * 60 * 1000

  constructor() {
    setInterval(() => {
      this.cleanup()
    }, this.CLEANUP_INTERVAL)
  }

  setPreviousResponseId(conversationId: string, responseId: string): void {
    this.conversationStates.set(conversationId, {
      previousResponseId: responseId,
      lastUpdate: Date.now(),
    })
  }

  getPreviousResponseId(conversationId: string): string | undefined {
    const state = this.conversationStates.get(conversationId)
    if (state) {
      state.lastUpdate = Date.now()
      return state.previousResponseId
    }
    return undefined
  }

  clearConversation(conversationId: string): void {
    this.conversationStates.delete(conversationId)
  }

  clearAll(): void {
    this.conversationStates.clear()
  }

  private cleanup(): void {
    const now = Date.now()
    for (const [conversationId, state] of this.conversationStates.entries()) {
      if (now - state.lastUpdate > this.CLEANUP_INTERVAL) {
        this.conversationStates.delete(conversationId)
      }
    }
  }

  getStateSize(): number {
    return this.conversationStates.size
  }
}

export const responseStateManager = new ResponseStateManager()

export function getConversationId(
  agentId?: string,
  messageId?: string,
): string {
  return (
    agentId ||
    messageId ||
    `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  )
}
