import React, { useMemo, useRef } from 'react'
import { Box, Text, useInput } from 'ink'
import chalk from 'chalk'
import type { Command } from '@commands'
import { Select } from '@components/custom-select/select'
import { getTheme } from '@utils/theme'
import {
  DEFAULT_OUTPUT_STYLE,
  getAvailableOutputStyles,
  getCurrentOutputStyle,
  resolveOutputStyleName,
  setCurrentOutputStyle,
} from '@services/outputStyles'

const HELP_ARGS = new Set(['help', '-h', '--help'])
const CURRENT_ARGS = new Set(['?', 'current'])

function normalizeStyleName(value: string): string {
  return value.trim()
}

function OutputStyleMenu({
  onDone,
}: {
  onDone: (result?: string) => void
}): React.ReactNode {
  const theme = getTheme()
  const doneRef = useRef(false)

  const styles = useMemo(() => getAvailableOutputStyles(), [])
  const styleNames = useMemo(() => {
    const names = Object.keys(styles)
    return names.sort((a, b) => {
      if (a === DEFAULT_OUTPUT_STYLE && b !== DEFAULT_OUTPUT_STYLE) return -1
      if (b === DEFAULT_OUTPUT_STYLE && a !== DEFAULT_OUTPUT_STYLE) return 1
      return a.localeCompare(b)
    })
  }, [styles])

  const rawCurrentStyle = getCurrentOutputStyle()
  const resolvedCurrentStyle =
    resolveOutputStyleName(rawCurrentStyle) ?? DEFAULT_OUTPUT_STYLE

  const finish = (msg?: string) => {
    if (doneRef.current) return
    doneRef.current = true
    onDone(msg)
  }

  useInput((_input, key) => {
    if (key.escape) {
      finish(`Kept output style as ${chalk.bold(rawCurrentStyle)}`)
    }
  })

  return (
    <>
      <Box
        flexDirection="column"
        gap={1}
        padding={1}
        borderStyle="round"
        borderColor={theme.secondary}
      >
        <Text bold>Output style</Text>
        <Text dimColor>Current: {resolvedCurrentStyle}</Text>
        <Text>Choose a style:</Text>
        <Select
          options={styleNames.map(name => ({ label: name, value: name }))}
          defaultValue={resolvedCurrentStyle}
          visibleOptionCount={Math.min(10, Math.max(5, styleNames.length))}
          onChange={value => {
            const next = normalizeStyleName(value)
            setCurrentOutputStyle(next)
            finish(`Set output style to ${chalk.bold(next)}`)
          }}
        />
      </Box>
      <Box marginLeft={3}>
        <Text dimColor>↑↓ Navigate · Enter select · Esc cancel</Text>
      </Box>
    </>
  )
}

const outputStyle = {
  type: 'local-jsx',
  name: 'output-style',
  description: 'Set the output style directly or from a selection menu',
  isEnabled: true,
  isHidden: false,
  argumentHint: '[style]',
  userFacingName() {
    return 'output-style'
  },
  async call(onDone, _context, args) {
    const raw = (args ?? '').trim()

    if (CURRENT_ARGS.has(raw)) {
      const current = getCurrentOutputStyle()
      onDone(`Current output style: ${current}`)
      return null
    }

    if (HELP_ARGS.has(raw)) {
      onDone(
        'Run /output-style to open the output style selection menu, or /output-style [styleName] to set the output style.',
      )
      return null
    }

    if (raw) {
      const resolved = resolveOutputStyleName(raw)
      if (!resolved) {
        onDone(`Invalid output style: ${raw}`)
        return null
      }
      setCurrentOutputStyle(resolved)
      onDone(`Set output style to ${chalk.bold(resolved)}`)
      return null
    }

    return <OutputStyleMenu onDone={onDone} />
  },
} satisfies Command

export default outputStyle
