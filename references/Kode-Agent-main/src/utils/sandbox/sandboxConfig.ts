import { watchFile, unwatchFile } from 'fs'
import { homedir } from 'os'
import {
  getSettingsFileCandidates,
  loadSettingsWithLegacyFallback,
} from '@utils/config/settingsFiles'

export type SandboxNetworkConfig = {
  allowedDomains: string[]
  deniedDomains: string[]
  allowUnixSockets: string[]
  allowAllUnixSockets?: boolean
  allowLocalBinding?: boolean
  httpProxyPort?: number
  socksProxyPort?: number
}

export type SandboxFilesystemConfig = {
  denyRead: string[]
  allowWrite: string[]
  denyWrite: string[]
}

export type SandboxRipgrepConfig = {
  command: string
  args: string[]
}

export type SandboxRuntimeConfig = {
  network: SandboxNetworkConfig
  filesystem: SandboxFilesystemConfig
  ignoreViolations?: boolean
  enableWeakerNestedSandbox?: boolean
  ripgrep: SandboxRipgrepConfig
  excludedCommands?: string[]
}

type SettingsPermissions = {
  allow?: unknown
  deny?: unknown
}

type SettingsSandboxNetwork = {
  allowedDomains?: unknown
  deniedDomains?: unknown
  allowUnixSockets?: unknown
  allowAllUnixSockets?: unknown
  allowLocalBinding?: unknown
  httpProxyPort?: unknown
  socksProxyPort?: unknown
}

type SettingsSandboxRipgrep = {
  command?: unknown
  args?: unknown
}

type SettingsSandbox = {
  enabled?: unknown
  autoAllowBashIfSandboxed?: unknown
  allowUnsandboxedCommands?: unknown
  network?: SettingsSandboxNetwork
  ignoreViolations?: unknown
  enableWeakerNestedSandbox?: unknown
  ripgrep?: SettingsSandboxRipgrep
  excludedCommands?: unknown
}

export type KodeSettingsFile = {
  permissions?: SettingsPermissions
  sandbox?: SettingsSandbox
  [key: string]: unknown
}

type ToolRuleValue = { toolName: string; ruleContent?: string }

function parseToolRuleString(rule: string): ToolRuleValue {
  const match = rule.match(/^([^(]+)\(([^)]+)\)$/)
  if (!match) return { toolName: rule }

  const toolName = match[1]
  const ruleContent = match[2]
  if (!toolName || !ruleContent) return { toolName: rule }
  return { toolName, ruleContent }
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

function mergeSandboxSettings(
  base: SettingsSandbox | undefined,
  next: SettingsSandbox | undefined,
): SettingsSandbox | undefined {
  if (!base && !next) return undefined
  const merged: SettingsSandbox = { ...(base ?? {}) }

  const mergeBool = (k: keyof SettingsSandbox) => {
    if (next && k in next && next[k] !== undefined) merged[k] = next[k]
  }
  mergeBool('enabled')
  mergeBool('autoAllowBashIfSandboxed')
  mergeBool('allowUnsandboxedCommands')
  mergeBool('ignoreViolations')
  mergeBool('enableWeakerNestedSandbox')
  mergeBool('excludedCommands')

  if (next?.network) {
    merged.network = { ...(merged.network ?? {}), ...next.network }
  }
  if (next?.ripgrep) {
    merged.ripgrep = { ...(merged.ripgrep ?? {}), ...next.ripgrep }
  }

  return merged
}

export function loadMergedSettings(options?: {
  projectDir?: string
  homeDir?: string
}): KodeSettingsFile {
  const projectDir = options?.projectDir ?? process.cwd()
  const homeDir = options?.homeDir

  const user = loadSettingsWithLegacyFallback({
    destination: 'userSettings',
    homeDir,
    migrateToPrimary: true,
  }).settings as KodeSettingsFile | null
  const project = loadSettingsWithLegacyFallback({
    destination: 'projectSettings',
    projectDir,
    homeDir,
    migrateToPrimary: true,
  }).settings as KodeSettingsFile | null
  const local = loadSettingsWithLegacyFallback({
    destination: 'localSettings',
    projectDir,
    homeDir,
    migrateToPrimary: true,
  }).settings as KodeSettingsFile | null

  const allow = uniqueStringsUnion(
    uniqueStrings(user?.permissions?.allow),
    uniqueStrings(project?.permissions?.allow),
    uniqueStrings(local?.permissions?.allow),
  )
  const deny = uniqueStringsUnion(
    uniqueStrings(user?.permissions?.deny),
    uniqueStrings(project?.permissions?.deny),
    uniqueStrings(local?.permissions?.deny),
  )

  const sandbox = mergeSandboxSettings(
    mergeSandboxSettings(user?.sandbox, project?.sandbox),
    local?.sandbox,
  )

  return {
    permissions: { allow, deny },
    ...(sandbox ? { sandbox } : {}),
  }
}

export function normalizeSandboxRuntimeConfigFromSettings(
  settings: KodeSettingsFile,
  options?: {
    projectDir?: string
    homeDir?: string
    defaultRipgrep?: SandboxRipgrepConfig
  },
): SandboxRuntimeConfig {
  const projectDir = options?.projectDir ?? process.cwd()
  const homeDir = options?.homeDir ?? homedir()

  const permissions = settings.permissions ?? {}
  const allowRules = uniqueStrings(permissions.allow)
  const denyRules = uniqueStrings(permissions.deny)

  const explicitAllowedDomains = uniqueStrings(
    settings.sandbox?.network?.allowedDomains,
  )
  const allowedDomains: string[] = [...explicitAllowedDomains]
  const deniedDomains: string[] = []

  for (const rule of allowRules) {
    const parsed = parseToolRuleString(rule)
    if (
      parsed?.toolName === 'WebFetch' &&
      parsed.ruleContent?.startsWith('domain:')
    ) {
      allowedDomains.push(parsed.ruleContent.substring(7))
    }
  }

  for (const rule of denyRules) {
    const parsed = parseToolRuleString(rule)
    if (
      parsed?.toolName === 'WebFetch' &&
      parsed.ruleContent?.startsWith('domain:')
    ) {
      deniedDomains.push(parsed.ruleContent.substring(7))
    }
  }

  const allowWrite: string[] = ['.']
  const denyWrite: string[] = []
  const denyRead: string[] = []

  const userCandidates = getSettingsFileCandidates({
    destination: 'userSettings',
    homeDir,
  })
  const userCandidatesWithEnv = getSettingsFileCandidates({
    destination: 'userSettings',
  })
  const projectCandidates = getSettingsFileCandidates({
    destination: 'projectSettings',
    projectDir,
    homeDir,
  })
  const localCandidates = getSettingsFileCandidates({
    destination: 'localSettings',
    projectDir,
    homeDir,
  })

  for (const path of [
    userCandidates?.primary,
    ...(userCandidates?.legacy ?? []),
    userCandidatesWithEnv?.primary,
    ...(userCandidatesWithEnv?.legacy ?? []),
    projectCandidates?.primary,
    ...(projectCandidates?.legacy ?? []),
    localCandidates?.primary,
    ...(localCandidates?.legacy ?? []),
  ]) {
    if (!path) continue
    if (denyWrite.includes(path)) continue
    denyWrite.push(path)
  }

  for (const rule of allowRules) {
    const parsed = parseToolRuleString(rule)
    if (
      (parsed?.toolName === 'Write' || parsed?.toolName === 'Edit') &&
      parsed.ruleContent
    ) {
      allowWrite.push(parsed.ruleContent)
    }
  }

  for (const rule of denyRules) {
    const parsed = parseToolRuleString(rule)
    if (
      (parsed?.toolName === 'Write' || parsed?.toolName === 'Edit') &&
      parsed.ruleContent
    ) {
      denyWrite.push(parsed.ruleContent)
    }
    if (parsed?.toolName === 'Read' && parsed.ruleContent) {
      denyRead.push(parsed.ruleContent)
    }
  }

  const sandboxNetwork = settings.sandbox?.network

  const defaultRipgrep: SandboxRipgrepConfig = options?.defaultRipgrep ?? {
    command: 'rg',
    args: [],
  }
  const ripgrep: SandboxRipgrepConfig =
    typeof settings.sandbox?.ripgrep?.command === 'string'
      ? {
          command: settings.sandbox!.ripgrep!.command as string,
          args: Array.isArray(settings.sandbox?.ripgrep?.args)
            ? (settings.sandbox!.ripgrep!.args as unknown[]).filter(
                (v): v is string => typeof v === 'string',
              )
            : [],
        }
      : defaultRipgrep

  return {
    network: {
      allowedDomains: uniqueStringsUnion(allowedDomains),
      deniedDomains: uniqueStringsUnion(deniedDomains),
      allowUnixSockets: Array.isArray(sandboxNetwork?.allowUnixSockets)
        ? (sandboxNetwork!.allowUnixSockets as unknown[]).filter(
            (v): v is string => typeof v === 'string',
          )
        : [],
      allowAllUnixSockets:
        typeof sandboxNetwork?.allowAllUnixSockets === 'boolean'
          ? sandboxNetwork.allowAllUnixSockets
          : undefined,
      allowLocalBinding:
        typeof sandboxNetwork?.allowLocalBinding === 'boolean'
          ? sandboxNetwork.allowLocalBinding
          : undefined,
      httpProxyPort:
        typeof sandboxNetwork?.httpProxyPort === 'number'
          ? sandboxNetwork.httpProxyPort
          : undefined,
      socksProxyPort:
        typeof sandboxNetwork?.socksProxyPort === 'number'
          ? sandboxNetwork.socksProxyPort
          : undefined,
    },
    filesystem: {
      denyRead: uniqueStringsUnion(denyRead),
      allowWrite: uniqueStringsUnion(allowWrite),
      denyWrite: uniqueStringsUnion(denyWrite),
    },
    ignoreViolations:
      typeof settings.sandbox?.ignoreViolations === 'boolean'
        ? settings.sandbox.ignoreViolations
        : undefined,
    enableWeakerNestedSandbox:
      typeof settings.sandbox?.enableWeakerNestedSandbox === 'boolean'
        ? settings.sandbox.enableWeakerNestedSandbox
        : undefined,
    excludedCommands: uniqueStrings(settings.sandbox?.excludedCommands),
    ripgrep,
  }
}

function looksLikeLinuxGlobPattern(ruleContent: string): boolean {
  const trimmed = ruleContent.replace(/\/\*\*$/, '')
  return /[*?[\]]/.test(trimmed)
}

export function getLinuxSandboxGlobPatternWarnings(
  settings: KodeSettingsFile,
  options?: { platform?: NodeJS.Platform },
): string[] {
  const platform = options?.platform ?? process.platform
  if (platform !== 'linux') return []
  if (settings.sandbox?.enabled !== true) return []

  const permissions = settings.permissions ?? {}
  const allow = uniqueStrings(permissions.allow)
  const deny = uniqueStrings(permissions.deny)

  const warnings: string[] = []
  for (const rule of [...allow, ...deny]) {
    const parsed = parseToolRuleString(rule)
    if (!parsed?.ruleContent) continue
    if (
      parsed.toolName !== 'Write' &&
      parsed.toolName !== 'Edit' &&
      parsed.toolName !== 'Read'
    )
      continue
    if (!looksLikeLinuxGlobPattern(parsed.ruleContent)) continue
    warnings.push(rule)
  }

  return warnings
}

export type SandboxConfigListener = (config: SandboxRuntimeConfig) => void

export class SandboxConfigManager {
  private listeners = new Set<SandboxConfigListener>()
  private watchPaths: string[] = []
  private current: SandboxRuntimeConfig | null = null

  getCurrent(): SandboxRuntimeConfig {
    if (!this.current) {
      const settings = loadMergedSettings()
      this.current = normalizeSandboxRuntimeConfigFromSettings(settings)
    }
    return this.current
  }

  subscribe(listener: SandboxConfigListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  initialize(options?: { projectDir?: string; homeDir?: string }): void {
    const projectDir = options?.projectDir ?? process.cwd()
    const homeDir = options?.homeDir ?? homedir()
    const user = getSettingsFileCandidates({
      destination: 'userSettings',
      homeDir,
    })
    const userEnv = getSettingsFileCandidates({ destination: 'userSettings' })
    const project = getSettingsFileCandidates({
      destination: 'projectSettings',
      projectDir,
      homeDir,
    })
    const local = getSettingsFileCandidates({
      destination: 'localSettings',
      projectDir,
      homeDir,
    })

    const paths = [
      user?.primary,
      ...(user?.legacy ?? []),
      userEnv?.primary,
      ...(userEnv?.legacy ?? []),
      project?.primary,
      ...(project?.legacy ?? []),
      local?.primary,
      ...(local?.legacy ?? []),
    ].filter((p): p is string => Boolean(p))
    this.watchPaths = Array.from(new Set(paths))

    for (const p of this.watchPaths) {
      watchFile(p, { interval: 1000 }, () => {
        const settings = loadMergedSettings({ projectDir, homeDir })
        this.current = normalizeSandboxRuntimeConfigFromSettings(settings, {
          projectDir,
          homeDir,
        })
        for (const listener of this.listeners) listener(this.current)
      })
    }
  }

  close(): void {
    for (const p of this.watchPaths) {
      try {
        unwatchFile(p)
      } catch {}
    }
    this.watchPaths = []
  }
}
