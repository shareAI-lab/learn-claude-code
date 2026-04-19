import { describe, expect, test } from 'bun:test'
import { __applyMultiSelectNavForTests } from '@components/permissions/ask-user-question-permission-request/AskUserQuestionPermissionRequest'

describe('AskUserQuestion multi-select navigation parity', () => {
  test('downArrow on last option enters submit focus; upArrow exits back to last option', () => {
    const optionCount = 5

    const atLast = __applyMultiSelectNavForTests({
      state: { focusedOptionIndex: optionCount - 1, isSubmitFocused: false },
      key: { downArrow: true },
      optionCount,
    })
    expect(atLast).toEqual({
      focusedOptionIndex: optionCount - 1,
      isSubmitFocused: true,
    })

    const back = __applyMultiSelectNavForTests({
      state: atLast,
      key: { upArrow: true },
      optionCount,
    })
    expect(back).toEqual({
      focusedOptionIndex: optionCount - 1,
      isSubmitFocused: false,
    })
  })

  test('Tab/Shift+Tab mirror down/up navigation', () => {
    const optionCount = 3

    const next = __applyMultiSelectNavForTests({
      state: { focusedOptionIndex: 0, isSubmitFocused: false },
      key: { tab: true, shift: false },
      optionCount,
    })
    expect(next).toEqual({ focusedOptionIndex: 1, isSubmitFocused: false })

    const prev = __applyMultiSelectNavForTests({
      state: { focusedOptionIndex: 1, isSubmitFocused: false },
      key: { tab: true, shift: true },
      optionCount,
    })
    expect(prev).toEqual({ focusedOptionIndex: 0, isSubmitFocused: false })
  })
})
