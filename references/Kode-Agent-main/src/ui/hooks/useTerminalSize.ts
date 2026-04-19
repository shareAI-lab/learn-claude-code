import { useEffect, useState } from 'react'

let globalSize = {
  columns: process.stdout.columns || 80,
  rows: process.stdout.rows || 24,
}

const listeners = new Set<() => void>()
let isListenerAttached = false

function updateAllListeners() {
  globalSize = {
    columns: process.stdout.columns || 80,
    rows: process.stdout.rows || 24,
  }
  listeners.forEach(listener => listener())
}

export function useTerminalSize() {
  const [size, setSize] = useState(globalSize)

  useEffect(() => {
    const updateSize = () => setSize({ ...globalSize })
    listeners.add(updateSize)

    if (!isListenerAttached) {
      process.stdout.setMaxListeners(20)
      process.stdout.on('resize', updateAllListeners)
      isListenerAttached = true
    }

    return () => {
      listeners.delete(updateSize)

      if (listeners.size === 0 && isListenerAttached) {
        process.stdout.off('resize', updateAllListeners)
        isListenerAttached = false
      }
    }
  }, [])

  return size
}
