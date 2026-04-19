import React from 'react'
import { Box, Text } from 'ink'
import { Select } from './custom-select/select'
import { getTheme } from '@utils/theme'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { formatDate } from '@utils/log'
import type { KodeAgentSessionListItem } from '@utils/protocol/kodeAgentSessionResume'

type SessionSelectorProps = {
  sessions: KodeAgentSessionListItem[]
  onSelect: (index: number) => void
}

export function SessionSelector({
  sessions,
  onSelect,
}: SessionSelectorProps): React.ReactNode {
  const { rows, columns } = useTerminalSize()
  if (sessions.length === 0) return null

  const visibleCount = rows - 3
  const hiddenCount = Math.max(0, sessions.length - visibleCount)

  const indexWidth = 7
  const modifiedWidth = 21
  const createdWidth = 21
  const tagWidth = 10

  const options = sessions.map((s, i) => {
    const index = `[${i}]`.padEnd(indexWidth)
    const modified = formatDate(
      s.modifiedAt ?? s.createdAt ?? new Date(0),
    ).padEnd(modifiedWidth)
    const created = formatDate(
      s.createdAt ?? s.modifiedAt ?? new Date(0),
    ).padEnd(createdWidth)
    const tag = (s.tag ? `#${s.tag}` : '').padEnd(tagWidth)

    const name = s.customTitle ?? s.slug ?? s.sessionId
    const summary = s.summary ? s.summary.split('\n')[0] : ''

    const labelTxt = `${index}${modified}${created}${tag}${name}${summary ? ` — ${summary}` : ''}`
    const truncated =
      labelTxt.length > columns - 2
        ? `${labelTxt.slice(0, columns - 5)}...`
        : labelTxt

    return { label: truncated, value: String(i) }
  })

  return (
    <Box flexDirection="column" height="100%" width="100%">
      <Box paddingLeft={9}>
        <Text bold color={getTheme().text}>
          Modified
        </Text>
        <Text>{'             '}</Text>
        <Text bold color={getTheme().text}>
          Created
        </Text>
        <Text>{'             '}</Text>
        <Text bold color={getTheme().text}>
          Tag
        </Text>
        <Text>{'      '}</Text>
        <Text bold color={getTheme().text}>
          Session
        </Text>
      </Box>
      <Select
        options={options}
        onChange={value => onSelect(parseInt(value, 10))}
        visibleOptionCount={visibleCount}
      />
      {hiddenCount > 0 && (
        <Box paddingLeft={2}>
          <Text color={getTheme().secondaryText}>and {hiddenCount} more…</Text>
        </Box>
      )}
    </Box>
  )
}
