import { useState } from 'react'
import { getHistory } from '@history'

export function useArrowKeyHistory(
  onSetInput: (value: string, mode: 'bash' | 'prompt') => void,
  currentInput: string,
) {
  const [historyIndex, setHistoryIndex] = useState(0)
  const [lastTypedInput, setLastTypedInput] = useState('')

  const updateInput = (input: string | undefined) => {
    if (input !== undefined) {
      const mode = input.startsWith('!') ? 'bash' : 'prompt'
      const value = mode === 'bash' ? input.slice(1) : input
      onSetInput(value, mode)
    }
  }

  function onHistoryUp() {
    const latestHistory = getHistory()
    if (historyIndex < latestHistory.length) {
      if (historyIndex === 0 && currentInput.trim() !== '') {
        setLastTypedInput(currentInput)
      }
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      updateInput(latestHistory[historyIndex])
    }
  }

  function onHistoryDown() {
    const latestHistory = getHistory()
    if (historyIndex > 1) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      updateInput(latestHistory[newIndex - 1])
    } else if (historyIndex === 1) {
      setHistoryIndex(0)
      updateInput(lastTypedInput)
    }
  }

  function resetHistory() {
    setLastTypedInput('')
    setHistoryIndex(0)
  }

  return {
    historyIndex,
    setHistoryIndex,
    onHistoryUp,
    onHistoryDown,
    resetHistory,
  }
}
