import { homedir } from 'os'
import { join } from 'path'
import type { ToolUseContext } from '@tool'
import type { BunShellSandboxOptions } from '@utils/bun/shell'
import which from 'which'
import {
  loadMergedSettings,
  normalizeSandboxRuntimeConfigFromSettings,
  type SandboxRuntimeConfig,
} from './sandboxConfig'
import { getCwd } from '@utils/state'

type SandboxIoOverrides = {
  projectDir?: string
  homeDir?: string
  platform?: NodeJS.Platform
  bwrapPath?: string | null
}

function getSandboxIoOverridesFromContext(
  context?: ToolUseContext,
): SandboxIoOverrides {
  const opts: any = context?.options ?? {}
  return {
    projectDir:
      typeof opts.__sandboxProjectDir === 'string'
        ? opts.__sandboxProjectDir
        : undefined,
    homeDir:
      typeof opts.__sandboxHomeDir === 'string'
        ? opts.__sandboxHomeDir
        : undefined,
    platform:
      typeof opts.__sandboxPlatform === 'string'
        ? (opts.__sandboxPlatform as NodeJS.Platform)
        : undefined,
    bwrapPath:
      opts.__sandboxBwrapPath === undefined
        ? undefined
        : (opts.__sandboxBwrapPath as string | null),
  }
}

function uniqueStrings(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const out: string[] = []
  const seen = new Set<string>()
  for (const item of value) {
    if (typeof item !== 'string') continue
    const trimmed = item.trim()
    if (!trimmed) continue
    if (seen.has(trimmed)) continue
    seen.add(trimmed)
    out.push(trimmed)
  }
  return out
}

function uniqueStringsUnion(...lists: string[][]): string[] {
  const out: string[] = []
  const seen = new Set<string>()
  for (const list of lists) {
    for (const item of list) {
      const trimmed = item.trim()
      if (!trimmed) continue
      if (seen.has(trimmed)) continue
      seen.add(trimmed)
      out.push(trimmed)
    }
  }
  return out
}

function getSandboxDefaultWriteAllowPaths(homeDir: string): string[] {
  return [
    '/dev/stdout',
    '/dev/stderr',
    '/dev/null',
    '/dev/tty',
    '/dev/dtracehelper',
    '/dev/autofs_nowait',
    '/tmp/kode',
    '/private/tmp/kode',
    join(homeDir, '.npm', '_logs'),
    join(homeDir, '.kode', 'debug'),
  ]
}

export type BunShellSandboxSettings = {
  enabled: boolean
  autoAllowBashIfSandboxed: boolean
  allowUnsandboxedCommands: boolean
  excludedCommands: string[]
}

export type BunShellSandboxPlan = {
  settings: BunShellSandboxSettings
  runtimeConfig: SandboxRuntimeConfig
  sandboxAvailable: boolean
  isExcluded: boolean
  willSandbox: boolean
  shouldAutoAllowBashPermissions: boolean
  shouldBlockUnsandboxedCommand: boolean
  bunShellSandboxOptions: BunShellSandboxOptions | undefined
}

function matchExcludedCommand(
  command: string,
  excludedCommands: string[],
): boolean {
  const trimmed = command.trim()
  if (!trimmed) return false
  for (const raw of excludedCommands) {
    const entry = raw.trim()
    if (!entry) continue
    if (entry.endsWith(':*')) {
      const prefix = entry.slice(0, -2).trim()
      if (!prefix) continue
      if (trimmed === prefix) return true
      if (trimmed.startsWith(prefix + ' ')) return true
      continue
    }
    if (trimmed === entry) return true
  }
  return false
}

function isSandboxAvailable(context?: ToolUseContext): boolean {
  const overrides = getSandboxIoOverridesFromContext(context)
  const platform = overrides.platform ?? process.platform
  if (platform === 'linux') {
    const bwrapPath =
      overrides.bwrapPath !== undefined
        ? overrides.bwrapPath
        : (which.sync('bwrap', { nothrow: true }) ??
          which.sync('bubblewrap', { nothrow: true }))
    return typeof bwrapPath === 'string' && bwrapPath.length > 0
  }

  if (platform === 'darwin') {
    const sandboxExecPath = which.sync('sandbox-exec', { nothrow: true })
    return typeof sandboxExecPath === 'string' && sandboxExecPath.length > 0
  }

  return false
}

function getSandboxDirs(context?: ToolUseContext): {
  projectDir: string
  homeDir: string
} {
  const overrides = getSandboxIoOverridesFromContext(context)
  return {
    projectDir: overrides.projectDir ?? getCwd(),
    homeDir: overrides.homeDir ?? homedir(),
  }
}

function getSandboxSettings(settingsFile: any): BunShellSandboxSettings {
  const sandbox = settingsFile?.sandbox ?? {}
  return {
    enabled: sandbox?.enabled === true,
    autoAllowBashIfSandboxed:
      typeof sandbox?.autoAllowBashIfSandboxed === 'boolean'
        ? sandbox.autoAllowBashIfSandboxed
        : true,
    allowUnsandboxedCommands:
      typeof sandbox?.allowUnsandboxedCommands === 'boolean'
        ? sandbox.allowUnsandboxedCommands
        : true,
    excludedCommands: uniqueStrings(sandbox?.excludedCommands),
  }
}

export function getBunShellSandboxPlan(args: {
  command: string
  dangerouslyDisableSandbox?: boolean
  toolUseContext?: ToolUseContext
}): BunShellSandboxPlan {
  const { projectDir, homeDir } = getSandboxDirs(args.toolUseContext)

  const merged = loadMergedSettings({ projectDir, homeDir })
  const runtimeConfig = normalizeSandboxRuntimeConfigFromSettings(merged, {
    projectDir,
    homeDir,
  })

  const settings = getSandboxSettings(merged as any)
  const sandboxEnabled = settings.enabled === true

  const sandboxAvailable = isSandboxAvailable(args.toolUseContext)
  const isExcluded = matchExcludedCommand(
    args.command,
    settings.excludedCommands,
  )

  const dangerousDisableEffective =
    args.dangerouslyDisableSandbox === true &&
    settings.allowUnsandboxedCommands === true

  const willSandbox =
    sandboxEnabled &&
    sandboxAvailable &&
    !dangerousDisableEffective &&
    !isExcluded
  const shouldAutoAllowBashPermissions =
    willSandbox && settings.autoAllowBashIfSandboxed
  const shouldBlockUnsandboxedCommand =
    sandboxEnabled &&
    !settings.allowUnsandboxedCommands &&
    !willSandbox &&
    !isExcluded

  const needsNetworkRestriction = sandboxEnabled

  const bunShellSandboxOptions: BunShellSandboxOptions | undefined = willSandbox
    ? {
        enabled: true,
        require: !settings.allowUnsandboxedCommands,
        needsNetworkRestriction,
        allowUnixSockets: runtimeConfig.network.allowUnixSockets,
        allowAllUnixSockets: runtimeConfig.network.allowAllUnixSockets,
        allowLocalBinding: runtimeConfig.network.allowLocalBinding,
        httpProxyPort: runtimeConfig.network.httpProxyPort,
        socksProxyPort: runtimeConfig.network.socksProxyPort,
        readConfig: { denyOnly: runtimeConfig.filesystem.denyRead },
        writeConfig: {
          allowOnly: uniqueStringsUnion(
            runtimeConfig.filesystem.allowWrite,
            getSandboxDefaultWriteAllowPaths(homeDir),
          ),
          denyWithinAllow: runtimeConfig.filesystem.denyWrite,
        },
        enableWeakerNestedSandbox: runtimeConfig.enableWeakerNestedSandbox,
        chdir: projectDir,
      }
    : undefined

  return {
    settings,
    runtimeConfig,
    sandboxAvailable,
    isExcluded,
    willSandbox,
    shouldAutoAllowBashPermissions,
    shouldBlockUnsandboxedCommand,
    bunShellSandboxOptions,
  }
}
