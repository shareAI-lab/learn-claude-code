import { Box, Text } from 'ink'
import * as React from 'react'
import { Hunk } from 'diff'
import { getTheme, ThemeNames } from '@utils/theme'
import { useMemo } from 'react'
import { wrapText } from '@utils/terminal/format'

type Props = {
  patch: Hunk
  dim: boolean
  width: number
  overrideTheme?: ThemeNames
  key?: React.Key
}

export function StructuredDiff({
  patch,
  dim,
  width,
  overrideTheme,
}: Props): React.ReactNode {
  const diff = useMemo(
    () => formatDiff(patch.lines, patch.oldStart, width, dim, overrideTheme),
    [patch.lines, patch.oldStart, width, dim, overrideTheme],
  )

  return diff.map((_, i) => <Box key={i}>{_}</Box>)
}

function formatDiff(
  lines: string[],
  startingLineNumber: number,
  width: number,
  dim: boolean,
  overrideTheme?: ThemeNames,
): React.ReactNode[] {
  const theme = getTheme(overrideTheme)

  const ls = numberDiffLines(
    lines.map(code => {
      if (code.startsWith('+')) {
        return {
          code: ' ' + code.slice(1),
          i: 0,
          type: 'add',
        }
      }
      if (code.startsWith('-')) {
        return {
          code: ' ' + code.slice(1),
          i: 0,
          type: 'remove',
        }
      }
      return { code, i: 0, type: 'nochange' }
    }),
    startingLineNumber,
  )

  const maxLineNumber = Math.max(...ls.map(({ i }) => i))
  const maxWidth = maxLineNumber.toString().length

  return ls.flatMap(({ type, code, i }) => {
    const wrappedLines = wrapText(code, width - maxWidth)
    return wrappedLines.map((line, lineIndex) => {
      const key = `${type}-${i}-${lineIndex}`
      switch (type) {
        case 'add':
          return (
            <React.Fragment key={key}>
              <Text>
                <LineNumber
                  i={lineIndex === 0 ? i : undefined}
                  width={maxWidth}
                />
                <Text
                  color={overrideTheme ? theme.text : undefined}
                  backgroundColor={
                    dim ? theme.diff.addedDimmed : theme.diff.added
                  }
                  dimColor={dim}
                >
                  {line}
                </Text>
              </Text>
            </React.Fragment>
          )
        case 'remove':
          return (
            <React.Fragment key={key}>
              <Text>
                <LineNumber
                  i={lineIndex === 0 ? i : undefined}
                  width={maxWidth}
                />
                <Text
                  color={overrideTheme ? theme.text : undefined}
                  backgroundColor={
                    dim ? theme.diff.removedDimmed : theme.diff.removed
                  }
                  dimColor={dim}
                >
                  {line}
                </Text>
              </Text>
            </React.Fragment>
          )
        case 'nochange':
          return (
            <React.Fragment key={key}>
              <Text>
                <LineNumber
                  i={lineIndex === 0 ? i : undefined}
                  width={maxWidth}
                />
                <Text
                  color={overrideTheme ? theme.text : undefined}
                  dimColor={dim}
                >
                  {line}
                </Text>
              </Text>
            </React.Fragment>
          )
      }
    })
  })
}

function LineNumber({
  i,
  width,
}: {
  i: number | undefined
  width: number
}): React.ReactNode {
  return (
    <Text color={getTheme().secondaryText}>
      {i !== undefined ? i.toString().padStart(width) : ' '.repeat(width)}{' '}
    </Text>
  )
}

function numberDiffLines(
  diff: { code: string; type: string }[],
  startLine: number,
): { code: string; type: string; i: number }[] {
  let i = startLine
  const result: { code: string; type: string; i: number }[] = []
  const queue = [...diff]

  while (queue.length > 0) {
    const { code, type } = queue.shift()!
    const line = {
      code: code,
      type,
      i,
    }

    switch (type) {
      case 'nochange':
        i++
        result.push(line)
        break
      case 'add':
        i++
        result.push(line)
        break
      case 'remove': {
        result.push(line)
        let numRemoved = 0
        while (queue[0]?.type === 'remove') {
          i++
          const { code, type } = queue.shift()!
          const line = {
            code: code,
            type,
            i,
          }
          result.push(line)
          numRemoved++
        }
        i -= numRemoved
        break
      }
    }
  }

  return result
}
