import { Box, Text } from 'ink'
import * as React from 'react'

type Props = {
  children: React.ReactNode
}

export function MessageResponse({ children }: Props): React.ReactNode {
  return (
    <Box flexDirection="row">
      <Text>{'  '}⎿ &nbsp;</Text>
      <Box flexDirection="column" flexGrow={1}>
        {children}
      </Box>
    </Box>
  )
}
