import React from 'react'
import { Box, Text } from 'ink'
import { getTheme } from '@utils/theme'

type Props = {
  addMargin: boolean
}

export function AssistantRedactedThinkingMessage({
  addMargin = false,
}: Props): React.ReactNode {
  return (
    <Box marginTop={addMargin ? 1 : 0}>
      <Text color={getTheme().secondaryText} italic>
        ✻ Thinking…
      </Text>
    </Box>
  )
}
