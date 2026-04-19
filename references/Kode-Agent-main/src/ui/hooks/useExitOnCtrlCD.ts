import { useInput } from 'ink'
import { useDoublePress } from './useDoublePress'
import { useState } from 'react'

type ExitState = {
  pending: boolean
  keyName: 'Ctrl-C' | 'Ctrl-D' | null
}

export function useExitOnCtrlCD(onExit: () => void): ExitState {
  const [exitState, setExitState] = useState<ExitState>({
    pending: false,
    keyName: null,
  })

  const handleCtrlC = useDoublePress(
    pending => setExitState({ pending, keyName: 'Ctrl-C' }),
    onExit,
  )
  const handleCtrlD = useDoublePress(
    pending => setExitState({ pending, keyName: 'Ctrl-D' }),
    onExit,
  )

  useInput((input, key) => {
    if (key.ctrl && input === 'c') handleCtrlC()
    if (key.ctrl && input === 'd') handleCtrlD()
  })

  return exitState
}
