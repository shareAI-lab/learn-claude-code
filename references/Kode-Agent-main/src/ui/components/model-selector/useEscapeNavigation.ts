import { useRef } from 'react'
import { useInput } from 'ink'

export function useEscapeNavigation(
  onEscape: () => void,
  _abortController?: AbortController,
) {
  const handledRef = useRef(false)

  useInput(
    (_input, key) => {
      if (key.escape && !handledRef.current) {
        handledRef.current = true
        setTimeout(() => {
          handledRef.current = false
        }, 100)
        onEscape()
      }
    },
    { isActive: true },
  )
}
