import React from 'react'
import { TextBlockParam } from '@anthropic-ai/sdk/resources/index.mjs'
import { Box, Text } from 'ink'
import { getTheme } from '@utils/theme'
import { logError } from '@utils/log'
import { useTerminalSize } from '@hooks/useTerminalSize'

type Props = {
  addMargin: boolean
  param: TextBlockParam
}

export function UserPromptMessage({
  addMargin,
  param: { text },
}: Props): React.ReactNode {
  const { columns } = useTerminalSize()
  if (!text) {
    logError('No content found in user prompt message')
    return null
  }

  return (
    <Box flexDirection="row" marginTop={addMargin ? 1 : 0} width="100%">
      <Box minWidth={2} width={2}>
        <Text color={getTheme().secondaryText}>&gt;</Text>
      </Box>
      <Box flexDirection="column" width={columns - 4}>
        <Text color={getTheme().secondaryText} wrap="wrap">
          {text}
        </Text>
      </Box>
    </Box>
  )
}
