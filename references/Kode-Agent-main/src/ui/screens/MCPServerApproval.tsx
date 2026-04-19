import React from 'react'
import { render } from 'ink'
import { MCPServerMultiselectDialog } from '@components/MCPServerMultiselectDialog'
import { MCPServerApprovalDialog } from '@components/MCPServerApprovalDialog'
import { getMcprcServerStatus } from '@services/mcpClient'
import { getProjectMcpServerDefinitions } from '@utils/config'

export async function handleMcprcServerApprovals(): Promise<void> {
  const { servers } = getProjectMcpServerDefinitions()
  const pendingServers = Object.keys(servers).filter(
    serverName => getMcprcServerStatus(serverName) === 'pending',
  )

  if (pendingServers.length === 0) {
    return
  }

  await new Promise<void>(resolve => {
    const clearScreenAndResolve = () => {
      process.stdout.write('\x1b[2J\x1b[3J\x1b[H', () => {
        resolve()
      })
    }

    if (pendingServers.length === 1 && pendingServers[0] !== undefined) {
      const result = render(
        <MCPServerApprovalDialog
          serverName={pendingServers[0]}
          onDone={() => {
            result.unmount?.()
            clearScreenAndResolve()
          }}
        />,
        { exitOnCtrlC: false },
      )
    } else {
      const result = render(
        <MCPServerMultiselectDialog
          serverNames={pendingServers}
          onDone={() => {
            result.unmount?.()
            clearScreenAndResolve()
          }}
        />,
        { exitOnCtrlC: false },
      )
    }
  })
}

