import { Box, Text, useInput } from 'ink'
import React from 'react'
import { Select } from './custom-select/select'
import { getTheme } from '@utils/theme'
import Link from './Link'

interface Props {
  onDone: () => void
}

export function CostThresholdDialog({ onDone }: Props): React.ReactNode {
  useInput((input, key) => {
    if ((key.ctrl && (input === 'c' || input === 'd')) || key.escape) {
      onDone()
    }
  })

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      padding={1}
      borderColor={getTheme().secondaryBorder}
    >
      <Box marginBottom={1} flexDirection="column">
        <Text bold>
          You&apos;ve spent $5 on AI model API calls this session.
        </Text>
        <Text>Learn more about monitoring your AI usage costs:</Text>
        <Link url="https://github.com/shareAI-lab/kode/blob/main/README.md" />
      </Box>
      <Box>
        <Select
          options={[
            {
              value: 'ok',
              label: 'Got it, thanks!',
            },
          ]}
          onChange={onDone}
        />
      </Box>
    </Box>
  )
}
