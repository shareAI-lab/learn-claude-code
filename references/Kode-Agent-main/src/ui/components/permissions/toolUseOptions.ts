import { type Option } from '@inkjs/ui'
import chalk from 'chalk'
import {
  type ToolUseConfirm,
  toolUseConfirmGetPrefix,
} from './PermissionRequest'
import { isUnsafeCompoundCommand } from '@utils/commands'
import { getCwd } from '@utils/state'
import { getTheme } from '@utils/theme'
import { type OptionSubtree } from '@components/custom-select/select'

const SHELL_KEYWORD_PREFIXES = new Set([
  'for',
  'if',
  'while',
  'until',
  'case',
  'select',
  'function',
  'do',
  'then',
  'elif',
  'else',
  'fi',
  'done',
])

export function toolUseOptions({
  toolUseConfirm,
  command,
}: {
  toolUseConfirm: ToolUseConfirm
  command: string
}): (Option | OptionSubtree)[] {
  const showDontAskAgainOption =
    !isUnsafeCompoundCommand(command) &&
    toolUseConfirm.commandPrefix &&
    !toolUseConfirm.commandPrefix.commandInjectionDetected
  const prefix = toolUseConfirmGetPrefix(toolUseConfirm)
  const prefixBase =
    typeof prefix === 'string' ? prefix.trim().split(/\s+/)[0] : null
  const preferFullCommandOverPrefix =
    typeof prefixBase === 'string' && SHELL_KEYWORD_PREFIXES.has(prefixBase)
  const showDontAskAgainPrefixOption =
    showDontAskAgainOption && prefix !== null && !preferFullCommandOverPrefix

  let dontShowAgainOptions: (Option | OptionSubtree)[] = []
  if (showDontAskAgainPrefixOption) {
    dontShowAgainOptions = [
      {
        label: `Yes, and don't ask again for commands starting with ${chalk.bold(prefix)} in ${chalk.bold(getCwd())}`,
        value: 'yes-dont-ask-again-prefix',
      },
    ]
  } else if (showDontAskAgainOption) {
    dontShowAgainOptions = [
      {
        label: `Yes, and don't ask again for this exact command in ${chalk.bold(getCwd())}`,
        value: 'yes-dont-ask-again-full',
      },
    ]
  }

  return [
    {
      label: 'Yes',
      value: 'yes',
    },
    ...dontShowAgainOptions,
    {
      label: `No, and provide instructions (${chalk.bold.hex(getTheme().warning)('esc')})`,
      value: 'no',
    },
  ]
}
