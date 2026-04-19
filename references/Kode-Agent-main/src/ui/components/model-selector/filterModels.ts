import type { ModelInfo } from './types'

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(0)}K`
  }
  return num.toString()
}

function getModelDetails(model: ModelInfo): string {
  const details = []

  if (model.context_length) {
    details.push(`${formatNumber(model.context_length)} tokens`)
  } else if (model.max_tokens) {
    details.push(`${formatNumber(model.max_tokens)} tokens`)
  }

  if (model.supports_vision) {
    details.push('vision')
  }

  if (model.supports_function_calling) {
    details.push('tools')
  }

  return details.length > 0 ? ` (${details.join(', ')})` : ''
}

function sortModelsByPriority(models: ModelInfo[]): ModelInfo[] {
  const priorityKeywords = [
    'claude',
    'kimi',
    'deepseek',
    'minimax',
    'o3',
    'gpt',
    'qwen',
  ]

  return models.sort((a, b) => {
    const aModelLower = a.model?.toLowerCase() || ''
    const bModelLower = b.model?.toLowerCase() || ''

    const aHasPriority = priorityKeywords.some(keyword =>
      aModelLower.includes(keyword),
    )
    const bHasPriority = priorityKeywords.some(keyword =>
      bModelLower.includes(keyword),
    )

    if (aHasPriority && !bHasPriority) return -1
    if (!aHasPriority && bHasPriority) return 1

    return a.model.localeCompare(b.model)
  })
}

export function buildModelOptions(
  availableModels: ModelInfo[],
  modelSearchQuery: string,
): Array<{ label: string; value: string }> {
  const filteredModels = modelSearchQuery
    ? availableModels.filter(model =>
        model.model?.toLowerCase().includes(modelSearchQuery.toLowerCase()),
      )
    : availableModels

  const sortedFilteredModels = sortModelsByPriority(filteredModels)

  return sortedFilteredModels.map(model => ({
    label: `${model.model}${getModelDetails(model)}`,
    value: model.model,
  }))
}

