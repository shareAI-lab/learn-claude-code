import type { Command } from '@commands'
import type { CompletionContext, UnifiedSuggestion } from './types'
import { generateFileSuggestions } from './fileSuggestions'
import { generateMentionSuggestions } from './mentionSuggestions'
import { generateSlashCommandSuggestions } from './slashCommandSuggestions'
import { generateUnixCommandSuggestions } from './unixCommandSuggestions'

export function generateSuggestionsForContext(args: {
  context: CompletionContext
  commands: Command[]
  agentSuggestions: UnifiedSuggestion[]
  modelSuggestions: UnifiedSuggestion[]
  systemCommands: string[]
  isLoadingCommands: boolean
  cwd: string
}): UnifiedSuggestion[] {
  const {
    context,
    commands,
    agentSuggestions,
    modelSuggestions,
    systemCommands,
    isLoadingCommands,
    cwd,
  } = args

  switch (context.type) {
    case 'command':
      return generateSlashCommandSuggestions({
        commands,
        prefix: context.prefix,
      })
    case 'agent': {
      const mentionSuggestions = generateMentionSuggestions({
        prefix: context.prefix,
        agentSuggestions,
        modelSuggestions,
      })
      const fileSuggestions = generateFileSuggestions({
        prefix: context.prefix,
        cwd,
      })

      const weightedSuggestions = [
        ...mentionSuggestions.map(s => ({
          ...s,
          weightedScore: s.score + 150,
        })),
        ...fileSuggestions.map(s => ({
          ...s,
          weightedScore: s.score + 10,
        })),
      ]

      return weightedSuggestions
        .sort((a, b) => b.weightedScore - a.weightedScore)
        .map(({ weightedScore, ...suggestion }) => suggestion)
    }
    case 'file': {
      const fileSuggestions = generateFileSuggestions({
        prefix: context.prefix,
        cwd,
      })
      const unixSuggestions = generateUnixCommandSuggestions({
        prefix: context.prefix,
        systemCommands,
        isLoadingCommands,
      })

      const mentionMatches = generateMentionSuggestions({
        prefix: context.prefix,
        agentSuggestions,
        modelSuggestions,
      }).map(s => ({
        ...s,
        isSmartMatch: true,
        displayValue: `\u2192 ${s.displayValue}`,
      }))

      const weightedSuggestions = [
        ...unixSuggestions.map(s => ({
          ...s,
          sourceWeight: s.score >= 10000 ? 5000 : 200,
          weightedScore: s.score >= 10000 ? s.score + 5000 : s.score + 200,
        })),
        ...mentionMatches.map(s => ({
          ...s,
          sourceWeight: 50,
          weightedScore: s.score + 50,
        })),
        ...fileSuggestions.map(s => ({
          ...s,
          sourceWeight: 0,
          weightedScore: s.score,
        })),
      ]

      const seen = new Set<string>()
      const deduplicatedResults = weightedSuggestions
        .sort((a, b) => b.weightedScore - a.weightedScore)
        .filter(item => {
          if (seen.has(item.value)) return false
          seen.add(item.value)
          return true
        })
        .map(({ weightedScore, sourceWeight, ...suggestion }) => suggestion)

      return deduplicatedResults
    }
    default:
      return []
  }
}
