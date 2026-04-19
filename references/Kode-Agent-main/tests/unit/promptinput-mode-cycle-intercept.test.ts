import { describe, expect, test } from 'bun:test'
import { __getPermissionModeCycleShortcutForTests } from '@utils/terminal/permissionModeCycleShortcut'
import { __getPromptInputSpecialKeyActionForTests } from '@utils/terminal/promptInputSpecialKey'
import { __shouldHandleUnifiedCompletionTabKeyForTests } from '@hooks/useUnifiedCompletion'

describe('PromptInput mode-cycle intercept', () => {
  test('Shift+Tab prefers mode cycle over completion Tab', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'darwin',
    })

    const key = { tab: true, shift: true } as any

    expect(__shouldHandleUnifiedCompletionTabKeyForTests(key)).toBe(false)
    expect(
      __getPromptInputSpecialKeyActionForTests({
        inputChar: '',
        key,
        modeCycleShortcut: shortcut,
      }),
    ).toBe('modeCycle')
  })

  test('Tab (no shift) remains available for completion', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'darwin',
    })

    const key = { tab: true, shift: false } as any

    expect(__shouldHandleUnifiedCompletionTabKeyForTests(key)).toBe(true)
    expect(
      __getPromptInputSpecialKeyActionForTests({
        inputChar: '',
        key,
        modeCycleShortcut: shortcut,
      }),
    ).toBe(null)
  })

  test('On older Windows runtimes, Alt+M cycles mode (and blocks model switch)', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'win32',
      nodeVersion: '22.16.0',
    })

    const key = { meta: true } as any

    expect(
      __getPromptInputSpecialKeyActionForTests({
        inputChar: 'm',
        key,
        modeCycleShortcut: shortcut,
      }),
    ).toBe('modeCycle')
  })
})
