import React from 'react'
import { Box, Newline, Text, useInput } from 'ink'
import { getTheme } from '@utils/theme'
import { Select } from './custom-select/select'
import { render } from 'ink'
import { writeFileSync } from 'fs'
import { ConfigParseError } from '@utils/text/errors'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
interface InvalidConfigHandlerProps {
  error: ConfigParseError
}

interface InvalidConfigDialogProps {
  filePath: string
  errorDescription: string
  onExit: () => void
  onReset: () => void
}

function InvalidConfigDialog({
  filePath,
  errorDescription,
  onExit,
  onReset,
}: InvalidConfigDialogProps): React.ReactNode {
  const theme = getTheme()

  useInput((_, key) => {
    if (key.escape) {
      onExit()
    }
  })

  const exitState = useExitOnCtrlCD(() => process.exit(0))

  const handleSelect = (value: string) => {
    if (value === 'exit') {
      onExit()
    } else {
      onReset()
    }
  }

  return (
    <>
      <Box
        flexDirection="column"
        borderColor={theme.error}
        borderStyle="round"
        padding={1}
        width={70}
        gap={1}
      >
        <Text bold>Configuration Error</Text>

        <Box flexDirection="column" gap={1}>
          <Text>
            The configuration file at <Text bold>{filePath}</Text> contains
            invalid JSON.
          </Text>
          <Text>{errorDescription}</Text>
        </Box>

        <Box flexDirection="column">
          <Text bold>Choose an option:</Text>
          <Select
            options={[
              { label: 'Exit and fix manually', value: 'exit' },
              { label: 'Reset with default configuration', value: 'reset' },
            ]}
            onChange={handleSelect}
          />
        </Box>
      </Box>
      {exitState.pending ? (
        <Text dimColor>Press {exitState.keyName} again to exit</Text>
      ) : (
        <Newline />
      )}
    </>
  )
}

export function showInvalidConfigDialog({
  error,
}: InvalidConfigHandlerProps): Promise<void> {
  return new Promise(resolve => {
    render(
      <InvalidConfigDialog
        filePath={error.filePath}
        errorDescription={error.message}
        onExit={() => {
          resolve()
          process.exit(1)
        }}
        onReset={() => {
          writeFileSync(
            error.filePath,
            JSON.stringify(error.defaultConfig, null, 2),
          )
          resolve()
          process.exit(0)
        }}
      />,
      { exitOnCtrlC: false },
    )
  })
}
