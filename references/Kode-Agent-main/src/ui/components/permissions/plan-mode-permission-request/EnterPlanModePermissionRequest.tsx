import { Box, Text, useInput } from 'ink'
import React from 'react'
import { Select } from '@components/custom-select/select'
import { PermissionRequestTitle } from '@components/permissions/PermissionRequestTitle'
import type { ToolUseConfirm } from '@components/permissions/PermissionRequest'
import { getTheme } from '@utils/theme'
import { usePermissionContext } from '@context/PermissionContext'

type Props = {
  toolUseConfirm: ToolUseConfirm
  onDone(): void
}

export function EnterPlanModePermissionRequest({
  toolUseConfirm,
  onDone,
}: Props): React.ReactNode {
  const theme = getTheme()
  const { setMode } = usePermissionContext()

  useInput((_input, key) => {
    if (key.escape) {
      toolUseConfirm.onReject()
      onDone()
    }
  })

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.permission}
      marginTop={1}
      paddingLeft={1}
      paddingRight={1}
      paddingBottom={1}
    >
      <PermissionRequestTitle title="Enter plan mode?" riskScore={null} />

      <Box flexDirection="column" paddingX={2} paddingY={1}>
        <Text>
          The assistant wants to enter plan mode to explore and design an
          implementation approach.
        </Text>
      </Box>

      <Box flexDirection="column" paddingX={2}>
        <Text dimColor>In plan mode, the assistant will:</Text>
        <Text dimColor> · Explore the codebase thoroughly</Text>
        <Text dimColor> · Identify existing patterns</Text>
        <Text dimColor> · Design an implementation strategy</Text>
        <Text dimColor> · Present a plan for your approval</Text>
      </Box>

      <Box flexDirection="column" paddingX={2} marginTop={1}>
        <Text dimColor>
          No code changes will be made until you approve the plan.
        </Text>
      </Box>

      <Box flexDirection="column">
        <Text>Would you like to proceed?</Text>
        <Select
          options={[
            { label: 'Yes, enter plan mode', value: 'yes' },
            { label: 'No, start implementing now', value: 'no' },
          ]}
          onChange={value => {
            if (value === 'yes') {
              setMode('plan')
              toolUseConfirm.onAllow('temporary')
              onDone()
              return
            }

            toolUseConfirm.onReject()
            onDone()
          }}
        />
      </Box>
    </Box>
  )
}
