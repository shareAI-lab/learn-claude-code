import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'

const MAX_HISTORY_ITEMS = 100

export function getHistory(): string[] {
  return getCurrentProjectConfig().history ?? []
}

export function addToHistory(command: string): void {
  const projectConfig = getCurrentProjectConfig()
  const history = projectConfig.history ?? []

  if (history[0] === command) {
    return
  }

  history.unshift(command)
  saveCurrentProjectConfig({
    ...projectConfig,
    history: history.slice(0, MAX_HISTORY_ITEMS),
  })
}
