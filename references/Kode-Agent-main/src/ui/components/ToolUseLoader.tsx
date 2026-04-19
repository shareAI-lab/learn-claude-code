import { Box, Text } from 'ink'
import React from 'react'
import { useInterval } from '@hooks/useInterval'
import { getTheme } from '@utils/theme'
import { BLACK_CIRCLE } from '@constants/figures'

type Props = {
  isError: boolean
  isUnresolved: boolean
  shouldAnimate: boolean
}

export function ToolUseLoader({
  isError,
  isUnresolved,
  shouldAnimate,
}: Props): React.ReactNode {
  const [isVisible, setIsVisible] = React.useState(true)

  useInterval(() => {
    if (!shouldAnimate) {
      return
    }
    setIsVisible(_ => !_)
  }, 600)

  const color = isUnresolved
    ? getTheme().secondaryText
    : isError
      ? getTheme().error
      : getTheme().success

  return (
    <Box minWidth={2}>
      <Text color={color}>{isVisible ? BLACK_CIRCLE : '  '}</Text>
    </Box>
  )
}
