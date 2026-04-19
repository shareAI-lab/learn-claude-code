import {
  getSettingsFileCandidates,
  loadSettingsWithLegacyFallback,
  saveSettingsToPrimaryAndSyncLegacy,
} from '@utils/config/settingsFiles'

type ClaudeUserSettings = {
  statusLine?: unknown
  [key: string]: unknown
}

function normalizeString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

export function getClaudeUserSettingsPath(): string {
  const candidates = getSettingsFileCandidates({ destination: 'userSettings' })
  return candidates?.primary ?? ''
}

export function getStatusLineCommand(): string | null {
  const loaded = loadSettingsWithLegacyFallback({
    destination: 'userSettings',
    migrateToPrimary: true,
  })
  const settings = (loaded.settings as ClaudeUserSettings | null) ?? {}

  const raw = settings.statusLine
  if (typeof raw === 'string') return normalizeString(raw)
  if (raw && typeof raw === 'object') {
    const cmd = (raw as any).command
    return normalizeString(cmd)
  }
  return null
}

export function setStatusLineCommand(command: string | null): void {
  const loaded = loadSettingsWithLegacyFallback({
    destination: 'userSettings',
    migrateToPrimary: true,
  })
  const existing = (loaded.settings as ClaudeUserSettings | null) ?? {}
  const next: ClaudeUserSettings = { ...existing }
  if (command === null) {
    delete next.statusLine
  } else {
    next.statusLine = command
  }
  saveSettingsToPrimaryAndSyncLegacy({
    destination: 'userSettings',
    settings: next,
    syncLegacyIfExists: true,
  })
}
