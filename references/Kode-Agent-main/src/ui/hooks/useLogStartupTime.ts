import { useRef } from 'react'
import { logStartupProfile } from '@utils/config/startupProfile'

export function useLogStartupTime(): void {
  const didLog = useRef(false)
  if (!didLog.current) {
    didLog.current = true
    logStartupProfile('first_render')
  }
}
