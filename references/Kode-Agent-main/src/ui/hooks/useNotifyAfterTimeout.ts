import { useEffect } from 'react'
import { sendNotification } from '@services/notifier'
import { memoize } from 'lodash-es'

const DEFAULT_INTERACTION_THRESHOLD_MS = 6000

const STATE = {
  lastInteractionTime: Date.now(),
}

function updateLastInteractionTime(): void {
  STATE.lastInteractionTime = Date.now()
}

function getTimeSinceLastInteraction(): number {
  return Date.now() - STATE.lastInteractionTime
}

function hasRecentInteraction(threshold: number): boolean {
  return getTimeSinceLastInteraction() < threshold
}

function shouldNotify(threshold: number): boolean {
  return process.env.NODE_ENV !== 'test' && !hasRecentInteraction(threshold)
}

const init = memoize(() => process.stdin.on('data', updateLastInteractionTime))

export function useNotifyAfterTimeout(
  message: string,
  timeout: number = DEFAULT_INTERACTION_THRESHOLD_MS,
): void {
  useEffect(() => {
    init()
    updateLastInteractionTime()
  }, [])

  useEffect(() => {
    let hasNotified = false
    const timer = setInterval(() => {
      if (shouldNotify(timeout) && !hasNotified) {
        hasNotified = true
        sendNotification({
          message,
        })
      }
    }, timeout)

    return () => clearTimeout(timer)
  }, [message, timeout])
}
