import type { CommandSource } from '@tools/BashTool/commandSource'

export type SystemSandboxMode = 'disabled' | 'auto' | 'required'
export type SystemSandboxNetworkMode = 'none' | 'inherit'

function parseBoolLike(value: string): boolean | null {
  const v = value.trim().toLowerCase()
  if (['1', 'true', 'yes', 'y', 'on', 'enable', 'enabled'].includes(v))
    return true
  if (['0', 'false', 'no', 'n', 'off', 'disable', 'disabled'].includes(v))
    return false
  return null
}

export function getSystemSandboxModeFromEnv(): SystemSandboxMode | null {
  const raw = process.env.KODE_SYSTEM_SANDBOX
  if (!raw) return null
  const bool = parseBoolLike(raw)
  if (bool === true) return 'auto'
  if (bool === false) return 'disabled'

  const v = raw.trim().toLowerCase()
  if (['required', 'strict', 'enforce', 'must'].includes(v)) return 'required'
  if (['auto'].includes(v)) return 'auto'
  if (['disabled', 'off', 'none'].includes(v)) return 'disabled'
  return null
}

export function getSystemSandboxNetworkModeFromEnv(): SystemSandboxNetworkMode | null {
  const raw = process.env.KODE_SYSTEM_SANDBOX_NETWORK
  if (!raw) return null
  const v = raw.trim().toLowerCase()
  if (['inherit', 'allow', 'enabled', 'true', '1'].includes(v)) return 'inherit'
  if (['none', 'deny', 'disabled', 'false', '0'].includes(v)) return 'none'
  return null
}

export type SystemSandboxDecision = {
  enabled: boolean
  required: boolean
  allowNetwork: boolean
}

export function decideSystemSandboxForBashTool(params: {
  safeMode: boolean
  commandSource: CommandSource
  dangerouslyDisableSandbox: boolean
}): SystemSandboxDecision {
  const modeFromEnv = getSystemSandboxModeFromEnv()
  const networkFromEnv = getSystemSandboxNetworkModeFromEnv()

  const enabledByDefault =
    params.safeMode && params.commandSource === 'agent_call'
  const mode: SystemSandboxMode =
    modeFromEnv ?? (enabledByDefault ? 'auto' : 'disabled')

  const enabled =
    mode !== 'disabled' &&
    params.commandSource === 'agent_call' &&
    !params.dangerouslyDisableSandbox
  const required = mode === 'required'

  const allowNetwork = (networkFromEnv ?? 'none') === 'inherit'

  return {
    enabled,
    required,
    allowNetwork,
  }
}
