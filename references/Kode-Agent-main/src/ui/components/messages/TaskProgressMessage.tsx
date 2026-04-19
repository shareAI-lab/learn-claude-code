import React from 'react'
import { Box, Text } from 'ink'
import { getTheme } from '@utils/theme'

interface Props {
  agentType: string
  status: string
  toolCount?: number
}

export function TaskProgressMessage({ agentType, status, toolCount }: Props) {
  const theme = getTheme()

  return (
    <Box flexDirection="column" marginTop={1}>
      <Box flexDirection="row">
        <Text color={theme.kode}>⎯ </Text>
        <Text color={theme.text} bold>
          [{agentType}]
        </Text>
        <Text color={theme.secondaryText}> {status}</Text>
      </Box>
      {toolCount && toolCount > 0 && (
        <Box marginLeft={3}>
          <Text color={theme.secondaryText}>Tools used: {toolCount}</Text>
        </Box>
      )}
    </Box>
  )
}
