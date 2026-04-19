import type { ModelPointerType, ModelProfile, ProviderType } from './schema'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { getGlobalConfig, saveGlobalConfig } from './loader'

export function setAllPointersToModel(modelName: string): void {
  const config = getGlobalConfig()
  const updatedConfig = {
    ...config,
    modelPointers: {
      main: modelName,
      task: modelName,
      compact: modelName,
      quick: modelName,
    },
    defaultModelName: modelName,
  }
  saveGlobalConfig(updatedConfig)
}

export function setModelPointer(
  pointer: ModelPointerType,
  modelName: string,
): void {
  const config = getGlobalConfig()
  const updatedConfig = {
    ...config,
    modelPointers: {
      ...config.modelPointers,
      [pointer]: modelName,
    },
  }
  saveGlobalConfig(updatedConfig)

  import('../../utils/model').then(({ reloadModelManager }) => {
    reloadModelManager()
  })
}

export function isGPT5ModelName(modelName: string): boolean {
  if (!modelName || typeof modelName !== 'string') return false
  const lowerName = modelName.toLowerCase()
  return lowerName.startsWith('gpt-5') || lowerName.includes('gpt-5')
}

export function validateAndRepairGPT5Profile(
  profile: ModelProfile,
): ModelProfile {
  const isGPT5 = isGPT5ModelName(profile.modelName)
  const now = Date.now()

  const repairedProfile: ModelProfile = { ...profile }
  let wasRepaired = false

  if (isGPT5 !== profile.isGPT5) {
    repairedProfile.isGPT5 = isGPT5
    wasRepaired = true
  }

  if (isGPT5) {

    const validReasoningEfforts = ['minimal', 'low', 'medium', 'high']
    if (
      !profile.reasoningEffort ||
      !validReasoningEfforts.includes(profile.reasoningEffort)
    ) {
      repairedProfile.reasoningEffort = 'medium'
      wasRepaired = true
      debugLogger.state('GPT5_CONFIG_AUTO_REPAIR', {
        model: profile.modelName,
        field: 'reasoningEffort',
        value: 'medium',
      })
    }

    if (profile.contextLength < 128000) {
      repairedProfile.contextLength = 128000
      wasRepaired = true
      debugLogger.state('GPT5_CONFIG_AUTO_REPAIR', {
        model: profile.modelName,
        field: 'contextLength',
        value: 128000,
      })
    }

    if (profile.maxTokens < 4000) {
      repairedProfile.maxTokens = 8192
      wasRepaired = true
      debugLogger.state('GPT5_CONFIG_AUTO_REPAIR', {
        model: profile.modelName,
        field: 'maxTokens',
        value: 8192,
      })
    }

    if (
      profile.provider !== 'openai' &&
      profile.provider !== 'custom-openai' &&
      profile.provider !== 'azure'
    ) {
      debugLogger.warn('GPT5_CONFIG_UNEXPECTED_PROVIDER', {
        model: profile.modelName,
        provider: profile.provider,
        expectedProviders: ['openai', 'custom-openai', 'azure'],
      })
    }

    if (profile.modelName.includes('gpt-5') && !profile.baseURL) {
      repairedProfile.baseURL = 'https://api.openai.com/v1'
      wasRepaired = true
      debugLogger.state('GPT5_CONFIG_AUTO_REPAIR', {
        model: profile.modelName,
        field: 'baseURL',
        value: 'https://api.openai.com/v1',
      })
    }
  }

  repairedProfile.validationStatus = wasRepaired ? 'auto_repaired' : 'valid'
  repairedProfile.lastValidation = now

  if (wasRepaired) {
    debugLogger.info('GPT5_CONFIG_AUTO_REPAIRED', { model: profile.modelName })
  }

  return repairedProfile
}

export function validateAndRepairAllGPT5Profiles(): {
  repaired: number
  total: number
} {
  const config = getGlobalConfig()
  if (!config.modelProfiles) {
    return { repaired: 0, total: 0 }
  }

  let repairCount = 0
  const repairedProfiles = config.modelProfiles.map(profile => {
    const repairedProfile = validateAndRepairGPT5Profile(profile)
    if (repairedProfile.validationStatus === 'auto_repaired') {
      repairCount++
    }
    return repairedProfile
  })

  if (repairCount > 0) {
    const updatedConfig = {
      ...config,
      modelProfiles: repairedProfiles,
    }
    saveGlobalConfig(updatedConfig)
    debugLogger.info('GPT5_CONFIG_AUTO_REPAIR_SUMMARY', {
      repaired: repairCount,
      total: config.modelProfiles.length,
    })
  }

  return { repaired: repairCount, total: config.modelProfiles.length }
}

export function getGPT5ConfigRecommendations(
  modelName: string,
): Partial<ModelProfile> {
  if (!isGPT5ModelName(modelName)) {
    return {}
  }

  const recommendations: Partial<ModelProfile> = {
    contextLength: 128000,
    maxTokens: 8192,
    reasoningEffort: 'medium',
    isGPT5: true,
  }

  if (modelName.includes('gpt-5-mini')) {
    recommendations.maxTokens = 4096
    recommendations.reasoningEffort = 'low'
  } else if (modelName.includes('gpt-5-nano')) {
    recommendations.maxTokens = 2048
    recommendations.reasoningEffort = 'minimal'
  }

  return recommendations
}

export function createGPT5ModelProfile(
  name: string,
  modelName: string,
  apiKey: string,
  baseURL?: string,
  provider: ProviderType = 'openai',
): ModelProfile {
  const recommendations = getGPT5ConfigRecommendations(modelName)

  const profile: ModelProfile = {
    name,
    provider,
    modelName,
    baseURL: baseURL || 'https://api.openai.com/v1',
    apiKey,
    maxTokens: recommendations.maxTokens || 8192,
    contextLength: recommendations.contextLength || 128000,
    reasoningEffort: recommendations.reasoningEffort || 'medium',
    isActive: true,
    createdAt: Date.now(),
    isGPT5: true,
    validationStatus: 'valid',
    lastValidation: Date.now(),
  }

  return profile
}

