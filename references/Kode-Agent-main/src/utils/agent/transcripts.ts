import type { Message as ConversationMessage } from '@query'

const transcripts = new Map<string, ConversationMessage[]>()

export function saveAgentTranscript(
  agentId: string,
  messages: ConversationMessage[],
): void {
  transcripts.set(agentId, messages)
}

export function getAgentTranscript(
  agentId: string,
): ConversationMessage[] | undefined {
  return transcripts.get(agentId)
}
