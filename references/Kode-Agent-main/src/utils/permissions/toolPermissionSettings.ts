import type {
  ToolPermissionContext,
  ToolPermissionContextUpdate,
  ToolPermissionRuleBehavior,
  ToolPermissionUpdateDestination,
} from '@kode-types/toolPermissionContext'
import {
  createDefaultToolPermissionContext,
  isPersistableToolPermissionDestination,
} from '@kode-types/toolPermissionContext'
import { getCurrentProjectConfig } from '@utils/config'
import { getCwd } from '@utils/state'
import { logError } from '@utils/log'
import {
  getSettingsFileCandidates,
  loadSettingsWithLegacyFallback,
  saveSettingsToPrimaryAndSyncLegacy,
  type SettingsFile,
} from '@utils/config/settingsFiles'

type SettingsPermissions = {
  allow?: unknown
  deny?: unknown
  ask?: unknown
  additionalDirectories?: unknown
}

type SettingsFileWithPermissions = {
  permissions?: SettingsPermissions
  [key: string]: unknown
}

function uniqueStrings(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const out: string[] = []
  const seen = new Set<string>()
  for (const item of value) {
    if (typeof item !== 'string') continue
    if (seen.has(item)) continue
    seen.add(item)
    out.push(item)
  }
  return out
}

function getPrimarySettingsFilePathForDestination(options: {
  destination: ToolPermissionUpdateDestination
  projectDir?: string
  homeDir?: string
}): string | null {
  const candidates = getSettingsFileCandidates({
    destination: options.destination as any,
    projectDir: options.projectDir,
    homeDir: options.homeDir,
  })
  return candidates?.primary ?? null
}

export function loadToolPermissionContextFromDisk(options?: {
  projectDir?: string
  homeDir?: string
  includeKodeProjectConfig?: boolean
  isBypassPermissionsModeAvailable?: boolean
}): ToolPermissionContext {
  const projectDir = options?.projectDir ?? getCwd()
  const homeDir = options?.homeDir
  const includeKodeProjectConfig = options?.includeKodeProjectConfig ?? true

  const base = createDefaultToolPermissionContext({
    isBypassPermissionsModeAvailable:
      options?.isBypassPermissionsModeAvailable ?? false,
  })

  const destinations: ToolPermissionUpdateDestination[] = [
    'userSettings',
    'projectSettings',
    'localSettings',
  ]

  for (const destination of destinations) {
    const settings = loadSettingsWithLegacyFallback({
      destination: destination as any,
      projectDir,
      homeDir,
      migrateToPrimary: true,
    }).settings as SettingsFileWithPermissions | null
    const perms = settings?.permissions
    const allow = uniqueStrings(perms?.allow)
    const deny = uniqueStrings(perms?.deny)
    const ask = uniqueStrings(perms?.ask)
    const additionalDirectories = uniqueStrings(perms?.additionalDirectories)

    if (allow.length > 0) base.alwaysAllowRules[destination] = allow
    if (deny.length > 0) base.alwaysDenyRules[destination] = deny
    if (ask.length > 0) base.alwaysAskRules[destination] = ask

    for (const dir of additionalDirectories) {
      base.additionalWorkingDirectories.set(dir, {
        path: dir,
        source: destination,
      })
    }
  }

  if (includeKodeProjectConfig) {
    try {
      const cfg = getCurrentProjectConfig()
      const allow = Array.isArray(cfg.allowedTools) ? cfg.allowedTools : []
      const deny = Array.isArray((cfg as any).deniedTools)
        ? (cfg as any).deniedTools
        : []
      const ask = Array.isArray((cfg as any).askedTools)
        ? (cfg as any).askedTools
        : []

      if (allow.length > 0) {
        const prev = base.alwaysAllowRules.localSettings ?? []
        base.alwaysAllowRules.localSettings = [...new Set([...prev, ...allow])]
      }
      if (deny.length > 0) {
        const prev = base.alwaysDenyRules.localSettings ?? []
        base.alwaysDenyRules.localSettings = [...new Set([...prev, ...deny])]
      }
      if (ask.length > 0) {
        const prev = base.alwaysAskRules.localSettings ?? []
        base.alwaysAskRules.localSettings = [...new Set([...prev, ...ask])]
      }
    } catch (error) {
      logError(error)
    }
  }

  return base
}

function getOrCreatePermissions(
  settings: SettingsFileWithPermissions,
): Required<SettingsFileWithPermissions>['permissions'] {
  const existing = settings.permissions
  if (existing && typeof existing === 'object') {
    return existing as SettingsPermissions
  }
  settings.permissions = {}
  return settings.permissions as SettingsPermissions
}

function behaviorKey(
  behavior: ToolPermissionRuleBehavior,
): keyof SettingsPermissions {
  switch (behavior) {
    case 'allow':
      return 'allow'
    case 'deny':
      return 'deny'
    case 'ask':
      return 'ask'
  }
}

export function persistToolPermissionUpdateToDisk(options: {
  update: ToolPermissionContextUpdate
  projectDir?: string
  homeDir?: string
}): { persisted: boolean } {
  const update = options.update
  if (!isPersistableToolPermissionDestination(update.destination)) {
    return { persisted: false }
  }
  if (update.type === 'setMode') {
    return { persisted: false }
  }

  const filePath = getPrimarySettingsFilePathForDestination({
    destination: update.destination,
    projectDir: options.projectDir,
    homeDir: options.homeDir,
  })
  if (!filePath) return { persisted: false }

  const existing =
    (loadSettingsWithLegacyFallback({
      destination: update.destination as any,
      projectDir: options.projectDir,
      homeDir: options.homeDir,
      migrateToPrimary: true,
    }).settings as SettingsFileWithPermissions | null) ?? {}
  const permissions = getOrCreatePermissions(existing)

  try {
    switch (update.type) {
      case 'addRules':
      case 'replaceRules':
      case 'removeRules': {
        const key = behaviorKey(update.behavior)
        const current = uniqueStrings(permissions[key])

        if (update.type === 'addRules') {
          const merged = [...new Set([...current, ...update.rules])]
          permissions[key] = merged
        } else if (update.type === 'replaceRules') {
          permissions[key] = uniqueStrings(update.rules)
        } else {
          const toRemove = new Set(update.rules)
          permissions[key] = current.filter(rule => !toRemove.has(rule))
        }
        break
      }
      case 'addDirectories':
      case 'removeDirectories': {
        const current = uniqueStrings(permissions.additionalDirectories)
        if (update.type === 'addDirectories') {
          permissions.additionalDirectories = [
            ...new Set([...current, ...update.directories]),
          ]
        } else {
          const toRemove = new Set(update.directories)
          permissions.additionalDirectories = current.filter(
            dir => !toRemove.has(dir),
          )
        }
        break
      }
      default:
        return { persisted: false }
    }

    saveSettingsToPrimaryAndSyncLegacy({
      destination: update.destination as any,
      projectDir: options.projectDir,
      homeDir: options.homeDir,
      settings: existing as SettingsFile,
      syncLegacyIfExists: true,
    })
    return { persisted: true }
  } catch (error) {
    logError(error)
    return { persisted: false }
  }
}
