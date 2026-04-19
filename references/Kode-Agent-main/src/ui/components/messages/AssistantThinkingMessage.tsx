import React from 'react'
import { Box, Text } from 'ink'
import { getTheme } from '@utils/theme'
import { applyMarkdown } from '@utils/text/markdown'
import {
  ThinkingBlock,
  ThinkingBlockParam,
} from '@anthropic-ai/sdk/resources/index.mjs'

type Props = {
  param: ThinkingBlock | ThinkingBlockParam
  addMargin: boolean
}

export function AssistantThinkingMessage({
  param: { thinking },
  addMargin = false,
}: Props): React.ReactNode {
  if (!thinking || thinking.trim().length === 0) {
    return null
  }

  return (
    <Box
      flexDirection="column"
      gap={1}
      marginTop={addMargin ? 1 : 0}
      width="100%"
    >
      <Text color={getTheme().secondaryText} italic>
        ✻ Thinking…
      </Text>
      <Box paddingLeft={2}>
        <Text color={getTheme().secondaryText} italic>
          {applyMarkdown(thinking)}
        </Text>
      </Box>
    </Box>
  )
}
