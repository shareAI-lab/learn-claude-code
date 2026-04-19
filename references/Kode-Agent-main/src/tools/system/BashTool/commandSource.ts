
export type CommandSource = 'user_bash_mode' | 'agent_call'

export interface BashValidationContext {
  source: CommandSource
}

export function getCommandSource(context: any): CommandSource {
  if (context?.commandSource === 'user_bash_mode') {
    return 'user_bash_mode'
  }

  return 'agent_call'
}
