import { ToolResultBlockParam } from '@anthropic-ai/sdk/resources/index.mjs'
import * as React from 'react'
import { Tool } from '@tool'
import { Message, UserMessage } from '@query'
import {
  CANCEL_MESSAGE,
  REJECT_MESSAGE,
  REJECT_MESSAGE_WITH_FEEDBACK_PREFIX,
} from '@utils/messages'
import { UserToolCanceledMessage } from './UserToolCanceledMessage'
import { UserToolErrorMessage } from './UserToolErrorMessage'
import { UserToolRejectMessage } from './UserToolRejectMessage'
import { UserToolSuccessMessage } from './UserToolSuccessMessage'

type Props = {
  param: ToolResultBlockParam
  message: UserMessage
  messages: Message[]
  tools: Tool[]
  verbose: boolean
  width: number | string
}

export function UserToolResultMessage({
  param,
  message,
  messages,
  tools,
  verbose,
  width,
}: Props): React.ReactNode {
  const content = typeof param.content === 'string' ? param.content : null

  if (content === CANCEL_MESSAGE) {
    return <UserToolCanceledMessage />
  }

  if (
    content === REJECT_MESSAGE ||
    (param.is_error === true &&
      typeof content === 'string' &&
      content.startsWith(REJECT_MESSAGE_WITH_FEEDBACK_PREFIX))
  ) {
    return (
      <UserToolRejectMessage
        toolUseID={param.tool_use_id}
        tools={tools}
        messages={messages}
        verbose={verbose}
      />
    )
  }

  if (param.is_error) {
    return <UserToolErrorMessage param={param} verbose={verbose} />
  }

  return (
    <UserToolSuccessMessage
      param={param}
      message={message}
      messages={messages}
      tools={tools}
      verbose={verbose}
      width={width}
    />
  )
}
