import { describe, expect, test } from 'bun:test'
import {
  AUTO_COMPACT_THRESHOLD_RATIO,
  calculateAutoCompactThresholds,
} from '@utils/session/autoCompactThreshold'

describe('autoCompactThreshold', () => {
  test('defaults to 90% of context window', () => {
    expect(AUTO_COMPACT_THRESHOLD_RATIO).toBe(0.9)

    const contextLimit = 1000
    const below = calculateAutoCompactThresholds(899, contextLimit)
    expect(below.isAboveAutoCompactThreshold).toBe(false)

    const at = calculateAutoCompactThresholds(900, contextLimit)
    expect(at.isAboveAutoCompactThreshold).toBe(true)
  })

  test('computes percentUsed and tokensRemaining consistently', () => {
    const contextLimit = 200_000
    const tokenCount = 180_000
    const result = calculateAutoCompactThresholds(tokenCount, contextLimit)

    expect(result.contextLimit).toBe(contextLimit)
    expect(result.autoCompactThreshold).toBe(
      contextLimit * AUTO_COMPACT_THRESHOLD_RATIO,
    )
    expect(result.percentUsed).toBe(
      Math.round((tokenCount / contextLimit) * 100),
    )
    expect(result.tokensRemaining).toBe(
      result.autoCompactThreshold - tokenCount,
    )
  })
})
