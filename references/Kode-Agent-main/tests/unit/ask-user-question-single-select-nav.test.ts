import { describe, expect, test } from 'bun:test'
import { __applySingleSelectNavForTests } from '@components/permissions/ask-user-question-permission-request/AskUserQuestionPermissionRequest'

describe('AskUserQuestion single-select navigation parity', () => {
  test('down then up returns to original index', () => {
    const optionCount = 5
    const start = 1

    const down = __applySingleSelectNavForTests({
      focusedOptionIndex: start,
      key: { downArrow: true },
      optionCount,
    })
    expect(down).toBe(start + 1)

    const up = __applySingleSelectNavForTests({
      focusedOptionIndex: down,
      key: { upArrow: true },
      optionCount,
    })
    expect(up).toBe(start)
  })

  test('clamps at bounds', () => {
    expect(
      __applySingleSelectNavForTests({
        focusedOptionIndex: 0,
        key: { upArrow: true },
        optionCount: 3,
      }),
    ).toBe(0)

    expect(
      __applySingleSelectNavForTests({
        focusedOptionIndex: 2,
        key: { downArrow: true },
        optionCount: 3,
      }),
    ).toBe(2)
  })
})
