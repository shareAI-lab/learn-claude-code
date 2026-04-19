import { memoize } from 'lodash-es'

import { logError } from '@utils/log'
import { debug as debugLogger } from '@utils/log/debugLogger'
import {
  getGlobalConfig,
  ModelProfile,
  ModelPointerType,
  saveGlobalConfig,
} from '@utils/config'

export const USE_BEDROCK = !!(
  process.env.KODE_USE_BEDROCK ?? process.env.CLAUDE_CODE_USE_BEDROCK
)
export const USE_VERTEX = !!(
  process.env.KODE_USE_VERTEX ?? process.env.CLAUDE_CODE_USE_VERTEX
)

export interface ModelConfig {
  bedrock: string
  vertex: string
  firstParty: string
}

const DEFAULT_MODEL_CONFIG: ModelConfig = {
  bedrock: 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
  vertex: 'claude-3-7-sonnet@20250219',
  firstParty: 'claude-sonnet-4-20250514',
}

async function getModelConfig(): Promise<ModelConfig> {
  return DEFAULT_MODEL_CONFIG
}

export const getSlowAndCapableModel = memoize(async (): Promise<string> => {
  const config = await getGlobalConfig()

  const modelManager = new ModelManager(config)
  const model = modelManager.getMainAgentModel()

  if (model) {
    return model
  }

  const modelConfig = await getModelConfig()
  if (USE_BEDROCK) return modelConfig.bedrock
  if (USE_VERTEX) return modelConfig.vertex
  return modelConfig.firstParty
})

export async function isDefaultSlowAndCapableModel(): Promise<boolean> {
  return (
    !process.env.ANTHROPIC_MODEL ||
    process.env.ANTHROPIC_MODEL === (await getSlowAndCapableModel())
  )
}

export function getVertexRegionForModel(
  model: string | undefined,
): string | undefined {
  if (model?.startsWith('claude-3-5-haiku')) {
    return process.env.VERTEX_REGION_CLAUDE_3_5_HAIKU
  } else if (model?.startsWith('claude-3-5-sonnet')) {
    return process.env.VERTEX_REGION_CLAUDE_3_5_SONNET
  } else if (model?.startsWith('claude-3-7-sonnet')) {
    return process.env.VERTEX_REGION_CLAUDE_3_7_SONNET
  }
}

export class ModelManager {
  private config: any
  private modelProfiles: ModelProfile[]

  constructor(config: any) {
    this.config = config
    this.modelProfiles = config.modelProfiles || []
  }

  getCurrentModel(): string | null {
    const mainModelName = this.config.modelPointers?.main
    if (mainModelName) {
      const profile = this.findModelProfile(mainModelName)
      if (profile && profile.isActive) {
        return profile.modelName
      }
    }

    return this.getMainAgentModel()
  }

  getMainAgentModel(): string | null {
    const mainModelName = this.config.modelPointers?.main
    if (mainModelName) {
      const profile = this.findModelProfile(mainModelName)
      if (profile && profile.isActive) {
        return profile.modelName
      }
    }

    const activeProfile = this.modelProfiles.find(p => p.isActive)
    if (activeProfile) {
      return activeProfile.modelName
    }

    return null
  }

  getTaskToolModel(): string | null {
    const taskModelName = this.config.modelPointers?.task
    if (taskModelName) {
      const profile = this.findModelProfile(taskModelName)
      if (profile && profile.isActive) {
        return profile.modelName
      }
    }

    return this.getMainAgentModel()
  }

  switchToNextModelWithContextCheck(currentContextTokens: number = 0): {
    success: boolean
    modelName: string | null
    previousModelName: string | null
    contextOverflow: boolean
    usagePercentage: number
    currentContextTokens: number
    skippedModels?: Array<{
      name: string
      provider: string
      contextLength: number
      budgetTokens: number | null
      usagePercentage: number
    }>
  } {
    const allProfiles = this.getAllConfiguredModels()
    if (allProfiles.length === 0) {
      return {
        success: false,
        modelName: null,
        previousModelName: null,
        contextOverflow: false,
        usagePercentage: 0,
        currentContextTokens,
      }
    }

    allProfiles.sort((a, b) => a.createdAt - b.createdAt)

    const currentMainModelName = this.config.modelPointers?.main
    const currentModel = currentMainModelName
      ? this.findModelProfile(currentMainModelName)
      : null
    const previousModelName = currentModel?.name || null

    const budgetForModel = (
      model: ModelProfile,
    ): {
      budgetTokens: number | null
      usagePercentage: number
      compatible: boolean
    } => {
      const contextLength = Number(model.contextLength)
      if (!Number.isFinite(contextLength) || contextLength <= 0) {
        return { budgetTokens: null, usagePercentage: 0, compatible: true }
      }
      const budgetTokens = Math.floor(contextLength * 0.9)
      const usagePercentage =
        budgetTokens > 0 ? (currentContextTokens / budgetTokens) * 100 : 0
      return {
        budgetTokens,
        usagePercentage,
        compatible:
          budgetTokens > 0 ? currentContextTokens <= budgetTokens : true,
      }
    }

    const currentIndex = currentMainModelName
      ? allProfiles.findIndex(p => p.modelName === currentMainModelName)
      : -1
    const startIndex = currentIndex >= 0 ? currentIndex : -1

    if (allProfiles.length === 1) {
      return {
        success: false,
        modelName: null,
        previousModelName,
        contextOverflow: false,
        usagePercentage: 0,
        currentContextTokens,
      }
    }

    const maxOffsets =
      startIndex === -1 ? allProfiles.length : allProfiles.length - 1
    const skippedModels: NonNullable<
      ReturnType<
        ModelManager['switchToNextModelWithContextCheck']
      >['skippedModels']
    > = []

    let selected: ModelProfile | null = null
    let selectedUsagePercentage = 0

    for (let offset = 1; offset <= maxOffsets; offset++) {
      const candidateIndex =
        (startIndex + offset + allProfiles.length) % allProfiles.length
      const candidate = allProfiles[candidateIndex]
      if (!candidate) continue

      const { budgetTokens, usagePercentage, compatible } =
        budgetForModel(candidate)
      if (compatible) {
        selected = candidate
        selectedUsagePercentage = usagePercentage
        break
      }
      skippedModels.push({
        name: candidate.name,
        provider: candidate.provider,
        contextLength: candidate.contextLength,
        budgetTokens,
        usagePercentage,
      })
    }

    if (!selected) {
      const firstSkipped = skippedModels[0]
      return {
        success: false,
        modelName: null,
        previousModelName,
        contextOverflow: true,
        usagePercentage: firstSkipped?.usagePercentage ?? 0,
        currentContextTokens,
        skippedModels,
      }
    }

    if (!selected.isActive) {
      selected.isActive = true
    }

    this.setPointer('main', selected.modelName)
    this.updateLastUsed(selected.modelName)

    return {
      success: true,
      modelName: selected.name,
      previousModelName,
      contextOverflow: false,
      usagePercentage: selectedUsagePercentage,
      currentContextTokens,
      skippedModels,
    }
  }

  switchToNextModel(currentContextTokens: number = 0): {
    success: boolean
    modelName: string | null
    blocked?: boolean
    message?: string
  } {
    const result = this.switchToNextModelWithContextCheck(currentContextTokens)

    const formatTokens = (tokens: number): string => {
      if (!Number.isFinite(tokens)) return 'unknown'
      if (tokens >= 1000) return `${Math.round(tokens / 1000)}k`
      return String(Math.round(tokens))
    }

    const allModels = this.getAllConfiguredModels()
    if (allModels.length === 0) {
      return {
        success: false,
        modelName: null,
        blocked: false,
        message: '❌ No models configured. Use /model to add models.',
      }
    }
    if (allModels.length === 1) {
      return {
        success: false,
        modelName: null,
        blocked: false,
        message: `⚠️ Only one model configured (${allModels[0].modelName}). Use /model to add more models for switching.`,
      }
    }

    const currentModel = this.findModelProfile(this.config.modelPointers?.main)
    const modelsSorted = [...allModels].sort(
      (a, b) => a.createdAt - b.createdAt,
    )
    const currentIndex = modelsSorted.findIndex(
      m => m.modelName === currentModel?.modelName,
    )
    const totalModels = modelsSorted.length

    if (result.success && result.modelName) {
      const skippedCount = result.skippedModels?.length ?? 0
      const skippedSuffix =
        skippedCount > 0 ? ` · skipped ${skippedCount} incompatible` : ''
      const contextSuffix =
        currentModel?.contextLength && result.currentContextTokens
          ? ` · context ~${formatTokens(result.currentContextTokens)}/${formatTokens(currentModel.contextLength)}`
          : ''

      return {
        success: true,
        modelName: result.modelName,
        blocked: false,
        message: `✅ Switched to ${result.modelName} (${currentIndex + 1}/${totalModels})${currentModel?.provider ? ` [${currentModel.provider}]` : ''}${skippedSuffix}${contextSuffix}`,
      }
    }

    if (result.contextOverflow) {
      const attempted = result.skippedModels?.[0]
      const attemptedContext = attempted?.contextLength
      const attemptedBudget = attempted?.budgetTokens
      const currentLabel =
        currentModel?.name || currentModel?.modelName || 'current model'

      const attemptedText = attempted
        ? `Can't switch to ${attempted.name}: current ~${formatTokens(result.currentContextTokens)} tokens exceeds safe budget (~${formatTokens(attemptedBudget ?? 0)} tokens, 90% of ${formatTokens(attemptedContext ?? 0)}).`
        : `Can't switch models due to context size (~${formatTokens(result.currentContextTokens)} tokens).`

      return {
        success: false,
        modelName: null,
        blocked: true,
        message: `⚠️ ${attemptedText} Keeping ${currentLabel}.`,
      }
    }

    return {
      success: false,
      modelName: null,
      blocked: false,
      message: '❌ Failed to switch models',
    }
  }

  revertToPreviousModel(previousModelName: string): boolean {
    const previousModel = this.modelProfiles.find(
      p => p.name === previousModelName && p.isActive,
    )
    if (!previousModel) {
      return false
    }

    this.setPointer('main', previousModel.modelName)
    this.updateLastUsed(previousModel.modelName)
    return true
  }

  analyzeContextCompatibility(
    model: ModelProfile,
    contextTokens: number,
  ): {
    compatible: boolean
    severity: 'safe' | 'warning' | 'critical'
    usagePercentage: number
    recommendation: string
  } {
    const usableContext = Math.floor(model.contextLength * 0.8)
    const usagePercentage = (contextTokens / usableContext) * 100

    if (usagePercentage <= 70) {
      return {
        compatible: true,
        severity: 'safe',
        usagePercentage,
        recommendation: 'Full context preserved',
      }
    } else if (usagePercentage <= 90) {
      return {
        compatible: true,
        severity: 'warning',
        usagePercentage,
        recommendation: 'Context usage high, consider compression',
      }
    } else {
      return {
        compatible: false,
        severity: 'critical',
        usagePercentage,
        recommendation: 'Auto-compression or message truncation required',
      }
    }
  }

  switchToNextModelWithAnalysis(currentContextTokens: number = 0): {
    modelName: string | null
    contextAnalysis: ReturnType<typeof this.analyzeContextCompatibility> | null
    requiresCompression: boolean
    estimatedTokensAfterSwitch: number
  } {
    const result = this.switchToNextModel(currentContextTokens)

    if (!result.success || !result.modelName) {
      return {
        modelName: null,
        contextAnalysis: null,
        requiresCompression: false,
        estimatedTokensAfterSwitch: 0,
      }
    }

    const newModel = this.getModel('main')
    if (!newModel) {
      return {
        modelName: result.modelName,
        contextAnalysis: null,
        requiresCompression: false,
        estimatedTokensAfterSwitch: currentContextTokens,
      }
    }

    const analysis = this.analyzeContextCompatibility(
      newModel,
      currentContextTokens,
    )

    return {
      modelName: result.modelName,
      contextAnalysis: analysis,
      requiresCompression: analysis.severity === 'critical',
      estimatedTokensAfterSwitch: currentContextTokens,
    }
  }

  canModelHandleContext(model: ModelProfile, contextTokens: number): boolean {
    const analysis = this.analyzeContextCompatibility(model, contextTokens)
    return analysis.compatible
  }

  findModelWithSufficientContext(
    models: ModelProfile[],
    contextTokens: number,
  ): ModelProfile | null {
    return (
      models.find(model => this.canModelHandleContext(model, contextTokens)) ||
      null
    )
  }

  getModelForContext(
    contextType: 'terminal' | 'main-agent' | 'task-tool',
  ): string | null {
    switch (contextType) {
      case 'terminal':
        return this.getCurrentModel()
      case 'main-agent':
        return this.getMainAgentModel()
      case 'task-tool':
        return this.getTaskToolModel()
      default:
        return this.getMainAgentModel()
    }
  }

  getActiveModelProfiles(): ModelProfile[] {
    return this.modelProfiles.filter(p => p.isActive)
  }

  hasConfiguredModels(): boolean {
    return this.getActiveModelProfiles().length > 0
  }


  getModel(pointer: ModelPointerType): ModelProfile | null {
    const pointerId = this.config.modelPointers?.[pointer]
    if (!pointerId) {
      return this.getDefaultModel()
    }

    const profile = this.findModelProfile(pointerId)
    return profile && profile.isActive ? profile : this.getDefaultModel()
  }

  getModelName(pointer: ModelPointerType): string | null {
    const profile = this.getModel(pointer)
    return profile ? profile.modelName : null
  }

  getCompactModel(): string | null {
    return this.getModelName('compact') || this.getModelName('main')
  }

  getQuickModel(): string | null {
    return (
      this.getModelName('quick') ||
      this.getModelName('task') ||
      this.getModelName('main')
    )
  }

  async addModel(
    config: Omit<ModelProfile, 'createdAt' | 'isActive'>,
  ): Promise<string> {
    const existingByModelName = this.modelProfiles.find(
      p => p.modelName === config.modelName,
    )
    if (existingByModelName) {
      throw new Error(
        `Model with modelName '${config.modelName}' already exists: ${existingByModelName.name}`,
      )
    }

    const existingByName = this.modelProfiles.find(p => p.name === config.name)
    if (existingByName) {
      throw new Error(`Model with name '${config.name}' already exists`)
    }

    const newModel: ModelProfile = {
      ...config,
      createdAt: Date.now(),
      isActive: true,
    }

    this.modelProfiles.push(newModel)

    if (this.modelProfiles.length === 1) {
      this.config.modelPointers = {
        main: config.modelName,
        task: config.modelName,
        compact: config.modelName,
        quick: config.modelName,
      }
      this.config.defaultModelName = config.modelName
    } else {
      if (!this.config.modelPointers) {
        this.config.modelPointers = {
          main: config.modelName,
          task: '',
          compact: '',
          quick: '',
        }
      } else {
        this.config.modelPointers.main = config.modelName
      }
    }

    this.saveConfig()
    return config.modelName
  }

  setPointer(pointer: ModelPointerType, modelName: string): void {
    if (!this.findModelProfile(modelName)) {
      throw new Error(`Model '${modelName}' not found`)
    }

    if (!this.config.modelPointers) {
      this.config.modelPointers = {
        main: '',
        task: '',
        compact: '',
        quick: '',
      }
    }

    this.config.modelPointers[pointer] = modelName
    this.saveConfig()
  }

  getAvailableModels(): ModelProfile[] {
    return this.modelProfiles.filter(p => p.isActive)
  }

  getAllConfiguredModels(): ModelProfile[] {
    return this.modelProfiles
  }

  getAllAvailableModelNames(): string[] {
    return this.getAvailableModels().map(p => p.modelName)
  }

  getAllConfiguredModelNames(): string[] {
    return this.getAllConfiguredModels().map(p => p.modelName)
  }

  getModelSwitchingDebugInfo(): {
    totalModels: number
    activeModels: number
    inactiveModels: number
    currentMainModel: string | null
    availableModels: Array<{
      name: string
      modelName: string
      provider: string
      isActive: boolean
      lastUsed?: number
    }>
    modelPointers: Record<string, string | undefined>
  } {
    const availableModels = this.getAvailableModels()
    const currentMainModelName = this.config.modelPointers?.main

    return {
      totalModels: this.modelProfiles.length,
      activeModels: availableModels.length,
      inactiveModels: this.modelProfiles.length - availableModels.length,
      currentMainModel: currentMainModelName || null,
      availableModels: this.modelProfiles.map(p => ({
        name: p.name,
        modelName: p.modelName,
        provider: p.provider,
        isActive: p.isActive,
        lastUsed: p.lastUsed,
      })),
      modelPointers: this.config.modelPointers || {},
    }
  }

  removeModel(modelName: string): void {
    this.modelProfiles = this.modelProfiles.filter(
      p => p.modelName !== modelName,
    )

    if (this.config.modelPointers) {
      Object.keys(this.config.modelPointers).forEach(pointer => {
        if (
          this.config.modelPointers[pointer as ModelPointerType] === modelName
        ) {
          this.config.modelPointers[pointer as ModelPointerType] =
            this.config.defaultModelName || ''
        }
      })
    }

    this.saveConfig()
  }

  private getDefaultModel(): ModelProfile | null {
    if (this.config.defaultModelId) {
      const profile = this.findModelProfile(this.config.defaultModelId)
      if (profile && profile.isActive) {
        return profile
      }
    }
    return this.modelProfiles.find(p => p.isActive) || null
  }

  private saveConfig(): void {
    const updatedConfig = {
      ...this.config,
      modelProfiles: this.modelProfiles,
    }
    saveGlobalConfig(updatedConfig)
  }

  async getFallbackModel(): Promise<string> {
    const modelConfig = await getModelConfig()
    if (USE_BEDROCK) return modelConfig.bedrock
    if (USE_VERTEX) return modelConfig.vertex
    return modelConfig.firstParty
  }

  resolveModel(modelParam: string | ModelPointerType): ModelProfile | null {
    if (['main', 'task', 'compact', 'quick'].includes(modelParam)) {
      const pointerId =
        this.config.modelPointers?.[modelParam as ModelPointerType]
      if (pointerId) {
        let profile = this.findModelProfile(pointerId)
        if (!profile) {
          profile = this.findModelProfileByModelName(pointerId)
        }
        if (profile && profile.isActive) {
          return profile
        }
      }
      return this.getDefaultModel()
    }

    let profile = this.findModelProfile(modelParam)
    if (profile && profile.isActive) {
      return profile
    }

    profile = this.findModelProfileByModelName(modelParam)
    if (profile && profile.isActive) {
      return profile
    }

    profile = this.findModelProfileByName(modelParam)
    if (profile && profile.isActive) {
      return profile
    }

    if (typeof modelParam === 'string') {
      const qualified = this.resolveProviderQualifiedModel(modelParam)
      if (qualified && qualified.isActive) {
        return qualified
      }
    }

    return this.getDefaultModel()
  }

  resolveModelWithInfo(modelParam: string | ModelPointerType): {
    success: boolean
    profile: ModelProfile | null
    error?: string
  } {
    const isPointer = ['main', 'task', 'compact', 'quick'].includes(modelParam)

    if (isPointer) {
      const pointerId =
        this.config.modelPointers?.[modelParam as ModelPointerType]
      if (!pointerId) {
        return {
          success: false,
          profile: null,
          error: `Model pointer '${modelParam}' is not configured. Use /model to set up models.`,
        }
      }

      let profile = this.findModelProfile(pointerId)
      if (!profile) {
        profile = this.findModelProfileByModelName(pointerId)
      }

      if (!profile) {
        return {
          success: false,
          profile: null,
          error: `Model pointer '${modelParam}' points to invalid model '${pointerId}'. Use /model to reconfigure.`,
        }
      }

      if (!profile.isActive) {
        return {
          success: false,
          profile: null,
          error: `Model '${profile.name}' (pointed by '${modelParam}') is inactive. Use /model to activate it.`,
        }
      }

      return {
        success: true,
        profile,
      }
    } else {
      let profile = this.findModelProfile(modelParam)
      if (!profile) {
        profile = this.findModelProfileByModelName(modelParam)
      }
      if (!profile) {
        profile = this.findModelProfileByName(modelParam)
      }

      if (!profile && typeof modelParam === 'string') {
        profile = this.resolveProviderQualifiedModel(modelParam)
      }

      if (!profile) {
        return {
          success: false,
          profile: null,
          error: `Model '${modelParam}' not found. Use /model to add models, or run 'kode models list' to see configured profiles.`,
        }
      }

      if (!profile.isActive) {
        return {
          success: false,
          profile: null,
          error: `Model '${profile.name}' is inactive. Use /model to activate it.`,
        }
      }

      return {
        success: true,
        profile,
      }
    }
  }

  private resolveProviderQualifiedModel(input: string): ModelProfile | null {
    const trimmed = input.trim()
    const colonIndex = trimmed.indexOf(':')
    if (colonIndex <= 0 || colonIndex >= trimmed.length - 1) return null

    const provider = trimmed.slice(0, colonIndex).trim().toLowerCase()
    const modelOrName = trimmed.slice(colonIndex + 1).trim()
    if (!provider || !modelOrName) return null

    const providerProfiles = this.modelProfiles.filter(
      p => String(p.provider).trim().toLowerCase() === provider,
    )
    if (providerProfiles.length === 0) return null

    const byModelName = providerProfiles.find(p => p.modelName === modelOrName)
    if (byModelName) return byModelName

    const byName = providerProfiles.find(p => p.name === modelOrName)
    if (byName) return byName

    return null
  }

  private findModelProfile(modelName: string): ModelProfile | null {
    return this.modelProfiles.find(p => p.modelName === modelName) || null
  }

  private findModelProfileByModelName(modelName: string): ModelProfile | null {
    return this.modelProfiles.find(p => p.modelName === modelName) || null
  }

  private findModelProfileByName(name: string): ModelProfile | null {
    return this.modelProfiles.find(p => p.name === name) || null
  }

  private updateLastUsed(modelName: string): void {
    const profile = this.findModelProfile(modelName)
    if (profile) {
      profile.lastUsed = Date.now()
    }
  }
}

let globalModelManager: ModelManager | null = null

export const getModelManager = (): ModelManager => {
  try {
    if (!globalModelManager) {
      const config = getGlobalConfig()
      if (!config) {
        debugLogger.warn('MODEL_MANAGER_GLOBAL_CONFIG_MISSING', {})
        globalModelManager = new ModelManager({
          modelProfiles: [],
          modelPointers: { main: '', task: '', compact: '', quick: '' },
        })
      } else {
        globalModelManager = new ModelManager(config)
      }
    }
    return globalModelManager
  } catch (error) {
    logError(error)
    debugLogger.error('MODEL_MANAGER_CREATE_FAILED', {
      error: error instanceof Error ? error.message : String(error),
    })
    return new ModelManager({
      modelProfiles: [],
      modelPointers: { main: '', task: '', compact: '', quick: '' },
    })
  }
}

export const reloadModelManager = (): void => {
  globalModelManager = null
  getModelManager()
}

export const getQuickModel = (): string => {
  const manager = getModelManager()
  const quickModel = manager.getModel('quick')
  return quickModel?.modelName || 'quick'
}
