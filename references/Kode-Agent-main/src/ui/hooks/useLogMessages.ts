import { useEffect } from 'react'
import { type Message } from '@query'
import { overwriteLog, getMessagesPath } from '@utils/log'

export function useLogMessages(
  messages: Message[],
  messageLogName: string,
  forkNumber: number,
): void {
  useEffect(() => {
    overwriteLog(
      getMessagesPath(messageLogName, forkNumber, 0),
      messages.filter(_ => _.type !== 'progress'),
      { conversationKey: `${messageLogName}:${forkNumber}` },
    )
  }, [messages, messageLogName, forkNumber])
}
