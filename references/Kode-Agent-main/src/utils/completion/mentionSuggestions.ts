import { matchCommands } from '@utils/completion/fuzzyMatcher'
import type { UnifiedSuggestion } from './types'

export function generateMentionSuggestions(args: {
  prefix: string
  agentSuggestions: UnifiedSuggestion[]
  modelSuggestions: UnifiedSuggestion[]
}): UnifiedSuggestion[] {
  const { prefix, agentSuggestions, modelSuggestions } = args
  const allSuggestions = [...agentSuggestions, ...modelSuggestions]

  if (!prefix) {
    return allSuggestions.sort((a, b) => {
      if (a.type === 'ask' && b.type === 'agent') return -1
      if (a.type === 'agent' && b.type === 'ask') return 1
      return b.score - a.score
    })
  }

  const candidates = allSuggestions.map(s => s.value)
  const matches = matchCommands(candidates, prefix)

  const fuzzyResults = matches
    .map(match => {
      const suggestion = allSuggestions.find(s => s.value === match.command)!
      return {
        ...suggestion,
        score: match.score,
      }
    })
    .sort((a, b) => {
      if (a.type === 'ask' && b.type === 'agent') return -1
      if (a.type === 'agent' && b.type === 'ask') return 1
      return b.score - a.score
    })

  return fuzzyResults
}
