import { describe, expect, test } from 'bun:test'
import { __getPermissionModeCycleShortcutForTests } from '@utils/terminal/permissionModeCycleShortcut'

describe('permission mode cycle shortcut', () => {
  test('non-Windows defaults to shift+tab', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'darwin',
      bunVersion: '1.2.0',
      nodeVersion: '22.0.0',
    })

    expect(shortcut.displayText).toBe('shift+tab')
    expect(shortcut.check('', { tab: true, shift: true } as any)).toBe(true)
    expect(shortcut.check('m', { meta: true } as any)).toBe(false)
  })

  test('Windows: Bun <1.2.23 falls back to alt+m', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'win32',
      bunVersion: '1.2.22',
    })

    expect(shortcut.displayText).toBe('alt+m')
    expect(shortcut.check('m', { meta: true } as any)).toBe(true)
    expect(shortcut.check('M', { meta: true } as any)).toBe(true)
    expect(shortcut.check('', { tab: true, shift: true } as any)).toBe(false)
  })

  test('Windows: Bun >=1.2.23 uses shift+tab', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'win32',
      bunVersion: '1.2.23',
    })

    expect(shortcut.displayText).toBe('shift+tab')
    expect(shortcut.check('', { tab: true, shift: true } as any)).toBe(true)
    expect(shortcut.check('m', { meta: true } as any)).toBe(false)
  })

  test('Windows: Node >=22.17.0 <23.0.0 uses shift+tab', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'win32',
      nodeVersion: '22.17.0',
    })

    expect(shortcut.displayText).toBe('shift+tab')
  })

  test('Windows: invalid version strings fall back to alt+m', () => {
    const shortcut = __getPermissionModeCycleShortcutForTests({
      platform: 'win32',
      bunVersion: 'not-a-version',
    })

    expect(shortcut.displayText).toBe('alt+m')
  })
})
