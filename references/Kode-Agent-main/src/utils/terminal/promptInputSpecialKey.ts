import type { Key } from 'ink'
import type { InputShortcut } from '@utils/terminal/permissionModeCycleShortcut'

type KeyWithOption = Key & { option?: boolean }

export type PromptInputSpecialKeyAction =
  | 'modeCycle'
  | 'modelSwitch'
  | 'externalEditor'
  | null

export function getPromptInputSpecialKeyAction(args: {
  inputChar: string
  key: KeyWithOption
  modeCycleShortcut: InputShortcut
}): PromptInputSpecialKeyAction {
  if (args.modeCycleShortcut.check(args.inputChar, args.key)) {
    return 'modeCycle'
  }

  const optionOrMeta = Boolean(args.key.meta) || Boolean(args.key.option)

  if (
    args.inputChar === 'µ' ||
    (optionOrMeta && (args.inputChar === 'm' || args.inputChar === 'M'))
  ) {
    return 'modelSwitch'
  }

  if (
    args.inputChar === '©' ||
    (optionOrMeta && (args.inputChar === 'g' || args.inputChar === 'G'))
  ) {
    return 'externalEditor'
  }

  return null
}

export function __getPromptInputSpecialKeyActionForTests(
  args: Parameters<typeof getPromptInputSpecialKeyAction>[0],
): PromptInputSpecialKeyAction {
  return getPromptInputSpecialKeyAction(args)
}
