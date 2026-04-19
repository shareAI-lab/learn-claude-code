import * as React from 'react'
import { Tool } from '@tool'
import { Message } from '@query'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { useGetToolFromMessages } from './utils'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { usePermissionContext } from '@context/PermissionContext'

type Props = {
  toolUseID: string
  messages: Message[]
  tools: Tool[]
  verbose: boolean
}

export function UserToolRejectMessage({
  toolUseID,
  tools,
  messages,
  verbose,
}: Props): React.ReactNode {
  const { columns } = useTerminalSize()
  const { conversationKey } = usePermissionContext()
  const { tool, toolUse } = useGetToolFromMessages(toolUseID, tools, messages)
  const input = tool.inputSchema.safeParse(toolUse.input)
  if (input.success) {
    return tool.renderToolUseRejectedMessage(input.data, {
      columns,
      verbose,
      conversationKey,
    })
  }
  return <FallbackToolUseRejectedMessage />
}
