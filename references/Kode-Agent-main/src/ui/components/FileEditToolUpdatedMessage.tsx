import { Hunk } from 'diff'
import { Box, Text } from 'ink'
import * as React from 'react'
import { intersperse } from '@utils/text/array'
import { StructuredDiff } from './StructuredDiff'
import { getTheme } from '@utils/theme'
import { getCwd } from '@utils/state'
import { relative } from 'path'
import { useTerminalSize } from '@hooks/useTerminalSize'

type Props = {
  filePath: string
  structuredPatch?: Hunk[]
  verbose: boolean
}

export function FileEditToolUpdatedMessage({
  filePath,
  structuredPatch,
  verbose,
}: Props): React.ReactNode {
  const { columns } = useTerminalSize()
  const patches = Array.isArray(structuredPatch) ? structuredPatch : []
  const numAdditions = patches.reduce(
    (count, hunk) => count + hunk.lines.filter(_ => _.startsWith('+')).length,
    0,
  )
  const numRemovals = patches.reduce(
    (count, hunk) => count + hunk.lines.filter(_ => _.startsWith('-')).length,
    0,
  )

  return (
    <Box flexDirection="column">
      <Text>
        {'  '}⎿ Updated{' '}
        <Text bold>{verbose ? filePath : relative(getCwd(), filePath)}</Text>
        {numAdditions > 0 || numRemovals > 0 ? ' with ' : ''}
        {numAdditions > 0 ? (
          <>
            <Text bold>{numAdditions}</Text>{' '}
            {numAdditions > 1 ? 'additions' : 'addition'}
          </>
        ) : null}
        {numAdditions > 0 && numRemovals > 0 ? ' and ' : null}
        {numRemovals > 0 ? (
          <>
            <Text bold>{numRemovals}</Text>{' '}
            {numRemovals > 1 ? 'removals' : 'removal'}
          </>
        ) : null}
      </Text>
      {patches.length > 0 &&
        intersperse(
          patches.map(_ => (
            <Box flexDirection="column" paddingLeft={5} key={_.newStart}>
              <StructuredDiff patch={_} dim={false} width={columns - 12} />
            </Box>
          )),
          i => (
            <Box paddingLeft={5} key={`ellipsis-${i}`}>
              <Text color={getTheme().secondaryText}>...</Text>
            </Box>
          ),
        )}
    </Box>
  )
}
