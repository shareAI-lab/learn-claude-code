import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileEditToolDiff } from '@components/permissions/file-edit-permission-request/FileEditToolDiff'
import { Message } from '@components/Message'
import { normalizeMessages, type NormalizedMessage } from '@utils/messages'
import type { Tool } from '@tool'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { FileWriteToolDiff } from '@components/permissions/file-write-permission-request/FileWriteToolDiff'
import type { AssistantMessage } from '@query'
import * as React from 'react'
import { Box } from 'ink'

type Props = {
  debug: boolean
  erroredToolUseIDs: Set<string>
  inProgressToolUseIDs: Set<string>
  message: AssistantMessage
  normalizedMessages: NormalizedMessage[]
  tools: Tool[]
  unresolvedToolUseIDs: Set<string>
  verbose: boolean
}

export function BinaryFeedbackOption({
  debug,
  erroredToolUseIDs,
  inProgressToolUseIDs,
  message,
  normalizedMessages,
  tools,
  unresolvedToolUseIDs,
  verbose,
}: Props): React.ReactNode {
  const { columns } = useTerminalSize()
  return normalizeMessages([message])
    .filter(_ => _.type !== 'progress')
    .map((_, index) => (
      <Box flexDirection="column" key={index}>
        <Message
          addMargin={false}
          erroredToolUseIDs={erroredToolUseIDs}
          debug={debug}
          inProgressToolUseIDs={inProgressToolUseIDs}
          message={_}
          messages={normalizedMessages}
          shouldAnimate={false}
          shouldShowDot={true}
          tools={tools}
          unresolvedToolUseIDs={unresolvedToolUseIDs}
          verbose={verbose}
          width={columns / 2 - 6}
        />
        <AdditionalContext message={_} verbose={verbose} />
      </Box>
    ))
}

function AdditionalContext({
  message,
  verbose,
}: {
  message: NormalizedMessage
  verbose: boolean
}) {
  const { columns } = useTerminalSize()
  if (message.type !== 'assistant') {
    return null
  }
  const content = message.message.content[0]!
  switch (content.type) {
    case 'tool_use':
      switch (content.name) {
        case FileEditTool.name: {
          const input = FileEditTool.inputSchema.safeParse(content.input)
          if (!input.success) {
            return null
          }
          return (
            <FileEditToolDiff
              file_path={input.data.file_path}
              new_string={input.data.new_string}
              old_string={input.data.old_string}
              verbose={verbose}
              width={columns / 2 - 12}
            />
          )
        }
        case FileWriteTool.name: {
          const input = FileWriteTool.inputSchema.safeParse(content.input)
          if (!input.success) {
            return null
          }
          return (
            <FileWriteToolDiff
              file_path={input.data.file_path}
              content={input.data.content}
              verbose={verbose}
              width={columns / 2 - 12}
            />
          )
        }
        default:
          return null
      }
    default:
      return null
  }
}
