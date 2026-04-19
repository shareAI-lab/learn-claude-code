import { useInput } from 'ink'
import { ToolUseConfirm } from '@components/permissions/PermissionRequest'
import { BinaryFeedbackContext } from '@screens/REPL'
import type { SetToolJSXFn } from '@tool'

export function useCancelRequest(
  setToolJSX: SetToolJSXFn,
  setToolUseConfirm: (toolUseConfirm: ToolUseConfirm | null) => void,
  setBinaryFeedbackContext: (bfContext: BinaryFeedbackContext | null) => void,
  onCancel: () => void,
  isLoading: boolean,
  isMessageSelectorVisible: boolean,
  abortSignal?: AbortSignal,
) {
  useInput((_, key) => {
    if (!key.escape) {
      return
    }
    if (abortSignal?.aborted) {
      return
    }
    if (!abortSignal) {
      return
    }
    if (!isLoading) {
      return
    }
    if (isMessageSelectorVisible) {
      return
    }

    setToolJSX(null)
    setToolUseConfirm(null)
    setBinaryFeedbackContext(null)
    onCancel()
  })
}
