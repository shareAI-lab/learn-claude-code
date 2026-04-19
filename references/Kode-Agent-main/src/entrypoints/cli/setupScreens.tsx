import React from 'react'

import { MACRO } from '@constants/macros'
import { Onboarding } from '@components/Onboarding'
import { TrustDialog } from '@components/TrustDialog'
import {
  checkHasTrustDialogAccepted,
  getGlobalConfig,
  saveGlobalConfig,
} from '@utils/config'
import { clearTerminal } from '@utils/terminal'
import { grantReadPermissionForOriginalDir } from '@utils/permissions/filesystem'
import { handleMcprcServerApprovals } from '@screens/MCPServerApproval'

export function completeOnboarding(): void {
  const config = getGlobalConfig()
  saveGlobalConfig({
    ...config,
    hasCompletedOnboarding: true,
    lastOnboardingVersion: MACRO.VERSION,
  })
}

export async function showSetupScreens(
  safeMode?: boolean,
  print?: boolean,
): Promise<void> {
  if (process.env.NODE_ENV === 'test') {
    return
  }

  const config = getGlobalConfig()
  if (!config.theme || !config.hasCompletedOnboarding) {
    await clearTerminal()
    const { render } = await import('ink')
    await new Promise<void>(resolve => {
      render(
        <Onboarding
          onDone={async () => {
            completeOnboarding()
            await clearTerminal()
            resolve()
          }}
        />,
        {
          exitOnCtrlC: false,
        },
      )
    })
  }

  if (!print) {
    if (safeMode) {
      if (!checkHasTrustDialogAccepted()) {
        await new Promise<void>(resolve => {
          const onDone = () => {
            grantReadPermissionForOriginalDir()
            resolve()
          }
          ;(async () => {
            const { render } = await import('ink')
            render(<TrustDialog onDone={onDone} />, {
              exitOnCtrlC: false,
            })
          })()
        })
      }
    }

    await handleMcprcServerApprovals()
  }
}
