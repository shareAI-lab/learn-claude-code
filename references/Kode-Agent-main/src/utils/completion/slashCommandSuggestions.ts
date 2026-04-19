import type { Command } from '@commands'
import type { UnifiedSuggestion } from './types'

export function generateSlashCommandSuggestions(args: {
  commands: Command[]
  prefix: string
}): UnifiedSuggestion[] {
  const { commands, prefix } = args
  const filteredCommands = commands.filter(cmd => !cmd.isHidden)

  if (!prefix) {
    return filteredCommands.map(cmd => ({
      value: cmd.userFacingName(),
      displayValue: `/${cmd.userFacingName()}`,
      type: 'command' as const,
      score: 100,
    }))
  }

  return filteredCommands
    .filter(cmd => {
      const names = [cmd.userFacingName(), ...(cmd.aliases || [])]
      return names.some(name =>
        name.toLowerCase().startsWith(prefix.toLowerCase()),
      )
    })
    .map(cmd => ({
      value: cmd.userFacingName(),
      displayValue: `/${cmd.userFacingName()}`,
      type: 'command' as const,
      score:
        100 -
        prefix.length +
        (cmd.userFacingName().startsWith(prefix) ? 10 : 0),
    }))
}
