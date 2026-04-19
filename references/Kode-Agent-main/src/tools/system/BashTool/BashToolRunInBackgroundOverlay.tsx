import { Box, Text, useInput } from 'ink'
import React from 'react'
import { RequestStatusIndicator } from '@components/RequestStatusIndicator'

export function BashToolRunInBackgroundOverlay({
  onBackground,
}: {
  onBackground: () => void
}): React.ReactNode {
  useInput((input, key) => {
    if (input === 'b' && key.ctrl) {
      onBackground()
      return true
    }
    return false
  })

  const shortcut = process.env.TMUX ? 'ctrl+b ctrl+b' : 'ctrl+b'

  return (
    <Box flexDirection="column">
      <RequestStatusIndicator />
      <Box paddingLeft={5}>
        <Text dimColor>{`${shortcut} run in background`}</Text>
      </Box>
    </Box>
  )
}
