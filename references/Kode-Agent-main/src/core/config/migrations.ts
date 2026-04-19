import type { GlobalConfig, ModelPointers, ModelProfile } from './schema'

export function migrateModelProfilesRemoveId(config: GlobalConfig): GlobalConfig {
  if (!config.modelProfiles) return config

  const idToModelNameMap = new Map<string, string>()
  const migratedProfiles = config.modelProfiles.map(profile => {
    if ((profile as any).id && profile.modelName) {
      idToModelNameMap.set((profile as any).id, profile.modelName)
    }

    const { id, ...profileWithoutId } = profile as any
    return profileWithoutId as ModelProfile
  })

  const migratedPointers: ModelPointers = {
    main: '',
    task: '',
    compact: '',
    quick: '',
  }

  const rawPointers = config.modelPointers as
    | Record<string, unknown>
    | undefined
  const rawMain = typeof rawPointers?.main === 'string' ? rawPointers.main : ''
  const rawTask = typeof rawPointers?.task === 'string' ? rawPointers.task : ''
  const rawQuick =
    typeof rawPointers?.quick === 'string' ? rawPointers.quick : ''
  const rawCompact =
    typeof rawPointers?.compact === 'string'
      ? rawPointers.compact
      : typeof rawPointers?.reasoning === 'string'
        ? rawPointers.reasoning
        : ''

  if (rawMain) migratedPointers.main = idToModelNameMap.get(rawMain) || rawMain
  if (rawTask) migratedPointers.task = idToModelNameMap.get(rawTask) || rawTask
  if (rawCompact)
    migratedPointers.compact = idToModelNameMap.get(rawCompact) || rawCompact
  if (rawQuick)
    migratedPointers.quick = idToModelNameMap.get(rawQuick) || rawQuick

  let defaultModelName: string | undefined
  if ((config as any).defaultModelId) {
    defaultModelName =
      idToModelNameMap.get((config as any).defaultModelId) ||
      (config as any).defaultModelId
  } else if ((config as any).defaultModelName) {
    defaultModelName = (config as any).defaultModelName
  }

  const migratedConfig = { ...config }
  delete (migratedConfig as any).defaultModelId
  delete (migratedConfig as any).currentSelectedModelId
  delete (migratedConfig as any).mainAgentModelId
  delete (migratedConfig as any).taskToolModelId

  return {
    ...migratedConfig,
    modelProfiles: migratedProfiles,
    modelPointers: migratedPointers,
    defaultModelName,
  }
}

