import { Box, Text } from 'ink'
import * as React from 'react'
import { getTheme } from '@utils/theme'
import { MAX_RENDERED_LINES } from './prompt'
import chalk from 'chalk'

function renderTruncatedContent(content: string, totalLines: number): string {
  const allLines = content.split('\n')
  if (allLines.length <= MAX_RENDERED_LINES) {
    return allLines.join('\n')
  }

  const lastLines = allLines.slice(-MAX_RENDERED_LINES)
  return [
    chalk.grey(
      `Showing last ${MAX_RENDERED_LINES} lines of ${totalLines} total lines`,
    ),
    ...lastLines,
  ].join('\n')
}

export function OutputLine({
  content,
  lines,
  verbose,
  isError,
}: {
  content: string
  lines: number
  verbose: boolean
  isError?: boolean
  key?: React.Key
}) {
  return (
    <Box justifyContent="space-between" width="100%">
      <Box flexDirection="row">
        <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
        <Box flexDirection="column">
          <Text color={isError ? getTheme().error : undefined}>
            {verbose
              ? content.trim()
              : renderTruncatedContent(content.trim(), lines)}
          </Text>
        </Box>
      </Box>
    </Box>
  )
}
