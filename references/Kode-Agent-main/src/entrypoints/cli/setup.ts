import { getContext } from '@context'
import { getCurrentProjectConfig } from '@utils/config'
import { cleanupOldMessageFilesInBackground } from '@utils/session/cleanup'
import { grantReadPermissionForOriginalDir } from '@utils/permissions/filesystem'
import { setCwd, setOriginalCwd } from '@utils/state'
import { debug as debugLogger } from '@utils/log/debugLogger'

export async function setup(cwd: string, safeMode?: boolean): Promise<void> {
  if (cwd !== process.cwd()) {
    setOriginalCwd(cwd)
  }
  await setCwd(cwd)

  grantReadPermissionForOriginalDir()

  let agentLoader: any
  try {
    agentLoader = await import('@utils/agent/loader')
  } catch {
    agentLoader = await import('@utils/agent/loader')
  }
  const { startAgentWatcher } = agentLoader
  await startAgentWatcher(() => {
    debugLogger.info('AGENTS_HOT_RELOADED', { ok: true })
  })

  if (safeMode) {
    if (
      process.platform !== 'win32' &&
      typeof process.getuid === 'function' &&
      process.getuid() === 0
    ) {
      console.error(
        `--safe mode cannot be used with root/sudo privileges for security reasons`,
      )
      process.exit(1)
    }
  }

  if (process.env.NODE_ENV === 'test') {
    return
  }

  cleanupOldMessageFilesInBackground()
  getContext()

  const projectConfig = getCurrentProjectConfig()
  if (
    projectConfig.lastCost !== undefined &&
    projectConfig.lastDuration !== undefined
  ) {
  }

}
