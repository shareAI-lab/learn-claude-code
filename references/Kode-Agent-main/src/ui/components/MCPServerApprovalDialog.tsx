import React from 'react'
import { Box, Text, useInput } from 'ink'
import { getTheme } from '@utils/theme'
import { Select } from './custom-select/select'
import {
  saveCurrentProjectConfig,
  getCurrentProjectConfig,
} from '@utils/config'
import { MCPServerDialogCopy } from './MCPServerDialogCopy'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'

type Props = {
  serverName: string
  onDone(): void
}

export function MCPServerApprovalDialog({
  serverName,
  onDone,
}: Props): React.ReactNode {
  const theme = getTheme()
  function onChange(value: 'yes' | 'no') {
    const config = getCurrentProjectConfig()
    switch (value) {
      case 'yes': {
        if (!config.approvedMcprcServers) {
          config.approvedMcprcServers = []
        }
        if (!config.approvedMcprcServers.includes(serverName)) {
          config.approvedMcprcServers.push(serverName)
        }
        saveCurrentProjectConfig(config)
        onDone()
        break
      }
      case 'no': {
        if (!config.rejectedMcprcServers) {
          config.rejectedMcprcServers = []
        }
        if (!config.rejectedMcprcServers.includes(serverName)) {
          config.rejectedMcprcServers.push(serverName)
        }
        saveCurrentProjectConfig(config)
        onDone()
        break
      }
    }
  }

  const exitState = useExitOnCtrlCD(() => process.exit(0))

  useInput((_input, key) => {
    if (key.escape) {
      onDone()
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
          New MCP Server Detected
        </Text>
        <Text>
          This project contains an MCP config file (.mcp.json or .mcprc) with an
          MCP server that requires your approval:
        </Text>
        <Text bold>{serverName}</Text>

        <MCPServerDialogCopy />

        <Text>Do you want to approve this MCP server?</Text>

        <Select
          options={[
            { label: 'Yes, approve this server', value: 'yes' },
            { label: 'No, reject this server', value: 'no' },
          ]}
          onChange={value => onChange(value as 'yes' | 'no')}
        />
      </Box>
      <Box marginLeft={3}>
        <Text dimColor>
          {exitState.pending ? (
            <>Press {exitState.keyName} again to exit</>
          ) : (
            <>Enter to confirm · Esc to reject</>
          )}
        </Text>
      </Box>
    </>
  )
}
