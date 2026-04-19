import { useInput } from 'ink'
import { type SelectState } from './use-select-state'

export type UseSelectProps = {
  isDisabled?: boolean

  state: SelectState
}

export const useSelect = ({ isDisabled = false, state }: UseSelectProps) => {
  useInput(
    (_input, key) => {
      if (key.downArrow) {
        state.focusNextOption()
      }

      if (key.upArrow) {
        state.focusPreviousOption()
      }

      if (key.return) {
        state.selectFocusedOption()
      }
    },
    { isActive: !isDisabled },
  )
}
