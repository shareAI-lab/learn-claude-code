import React from 'react'
import { Box, Text } from 'ink'
import { getTheme } from '@utils/theme'

export type ScreenContainerExitState = { pending: boolean; keyName: string }

type Props = {
  title: string
  exitState: ScreenContainerExitState
  children: React.ReactNode
  paddingY?: number
  gap?: number
}

export function ScreenContainer({
  title,
  exitState,
  children,
  paddingY = 1,
  gap = 1,
}: Props) {
  const theme = getTheme()
  return (
    <Box
      flexDirection="column"
      gap={gap}
      borderStyle="round"
      borderColor={theme.secondaryBorder}
      paddingX={2}
      paddingY={paddingY}
    >
      <Text bold>
        {title}{' '}
        {exitState.pending ? `(press ${exitState.keyName} again to exit)` : ''}
      </Text>
      {children}
    </Box>
  )
}
