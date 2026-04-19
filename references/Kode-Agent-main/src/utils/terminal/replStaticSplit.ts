import type { NormalizedMessage } from '@utils/messages'
import { getToolUseID } from '@utils/messages'
import type { ProgressMessage } from '@query'

function intersects<A>(a: Set<A>, b: Set<A>): boolean {
  return a.size > 0 && b.size > 0 && [...a].some(_ => b.has(_))
}

export function shouldRenderReplMessageStatically(
  message: NormalizedMessage,
  messages: NormalizedMessage[],
  unresolvedToolUseIDs: Set<string>,
): boolean {
  switch (message.type) {
    case 'user':
    case 'assistant': {
      const toolUseID = getToolUseID(message)
      if (!toolUseID) {
        return true
      }
      if (unresolvedToolUseIDs.has(toolUseID)) {
        return false
      }

      const correspondingProgressMessage = messages.find(
        _ => _.type === 'progress' && _.toolUseID === toolUseID,
      ) as ProgressMessage | null
      if (!correspondingProgressMessage) {
        return true
      }

      return !intersects(
        unresolvedToolUseIDs,
        correspondingProgressMessage.siblingToolUseIDs,
      )
    }
    case 'progress':
      return !intersects(unresolvedToolUseIDs, message.siblingToolUseIDs)
  }
}

export function getReplStaticPrefixLength(
  orderedMessages: NormalizedMessage[],
  allMessages: NormalizedMessage[],
  unresolvedToolUseIDs: Set<string>,
): number {
  for (let i = 0; i < orderedMessages.length; i++) {
    const message = orderedMessages[i]!
    if (
      !shouldRenderReplMessageStatically(
        message,
        allMessages,
        unresolvedToolUseIDs,
      )
    ) {
      return i
    }
  }
  return orderedMessages.length
}
