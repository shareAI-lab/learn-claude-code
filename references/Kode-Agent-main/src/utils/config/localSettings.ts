import { join } from 'path'
import { getCwd } from '@utils/state'
import {
  getSettingsFileCandidates,
  loadSettingsWithLegacyFallback,
  saveSettingsToPrimaryAndSyncLegacy,
} from '@utils/config/settingsFiles'

export type LocalSettings = {
  outputStyle?: unknown
  [key: string]: unknown
}

export function getLocalSettingsPath(options?: {
  projectDir?: string
}): string {
  const projectDir = options?.projectDir ?? getCwd()
  return join(projectDir, '.kode', 'settings.local.json')
}

export function readLocalSettings(options?: {
  projectDir?: string
}): LocalSettings {
  const projectDir = options?.projectDir ?? getCwd()
  const loaded = loadSettingsWithLegacyFallback({
    destination: 'localSettings',
    projectDir,
    migrateToPrimary: true,
  })
  return (loaded.settings as LocalSettings | null) ?? {}
}

export function updateLocalSettings(
  patch: Record<string, unknown>,
  options?: {
    projectDir?: string
  },
): LocalSettings {
  const projectDir = options?.projectDir ?? getCwd()
  const candidates = getSettingsFileCandidates({
    destination: 'localSettings',
    projectDir,
  })
  const existing =
    (candidates
      ? loadSettingsWithLegacyFallback({
          destination: 'localSettings',
          projectDir,
          migrateToPrimary: true,
        }).settings
      : null) ?? {}

  const next = { ...(existing as Record<string, unknown>), ...patch }

  if (candidates) {
    saveSettingsToPrimaryAndSyncLegacy({
      destination: 'localSettings',
      projectDir,
      settings: next,
      syncLegacyIfExists: true,
    })
  }

  return next as LocalSettings
}
