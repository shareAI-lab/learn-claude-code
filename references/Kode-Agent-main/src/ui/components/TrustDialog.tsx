import React from 'react'
import { Box, Text, useInput } from 'ink'
import { getTheme } from '@utils/theme'
import { Select } from './custom-select/select'
import {
  saveCurrentProjectConfig,
  getCurrentProjectConfig,
} from '@utils/config'
import { PRODUCT_NAME } from '@constants/product'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { homedir } from 'os'
import { getCwd } from '@utils/state'
import Link from './Link'

type Props = {
  onDone(): void
}

export function TrustDialog({ onDone }: Props): React.ReactNode {
  const theme = getTheme()
  React.useEffect(() => {}, [])

  function onChange(value: 'yes' | 'no') {
    const config = getCurrentProjectConfig()
    switch (value) {
      case 'yes': {
        const isHomeDir = homedir() === getCwd()

        if (!isHomeDir) {
          saveCurrentProjectConfig({
            ...config,
            hasTrustDialogAccepted: true,
          })
        }
        onDone()
        break
      }
      case 'no': {
        process.exit(1)
        break
      }
    }
  }

  const exitState = useExitOnCtrlCD(() => process.exit(0))

  useInput((_input, key) => {
    if (key.escape) {
      process.exit(0)
      return
    }
  })

  return (
    <>
      <Box
        flexDirection="column"
        gap={1}
        padding={1}
        borderStyle="round"
        borderColor={theme.warning}
      >
        <Text bold color={theme.warning}>
          Do you trust the files in this folder?
        </Text>
        <Text bold>{process.cwd()}</Text>

        <Box flexDirection="column" gap={1}>
          <Text>
            {PRODUCT_NAME} may read files in this folder. Reading untrusted
            files may lead to {PRODUCT_NAME} to behave in an unexpected ways.
          </Text>
          <Text>
            With your permission {PRODUCT_NAME} may execute files in this
            folder. Executing untrusted code is unsafe.
          </Text>
        </Box>

        <Select
          options={[
            { label: 'Yes, proceed', value: 'yes' },
            { label: 'No, exit', value: 'no' },
          ]}
          onChange={value => onChange(value as 'yes' | 'no')}
        />
      </Box>
      <Box marginLeft={3}>
        <Text dimColor>
          {exitState.pending ? (
            <>Press {exitState.keyName} again to exit</>
          ) : (
            <>Enter to confirm · Esc to exit</>
          )}
        </Text>
      </Box>
    </>
  )
}
