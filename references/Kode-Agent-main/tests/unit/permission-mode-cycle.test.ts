import { beforeEach, describe, expect, test } from 'bun:test'
import { getNextPermissionMode } from '@kode-types/permissionMode'
import { __applyPermissionModeSideEffectsForTests } from '@context/PermissionContext'
import {
  __resetPermissionModeStateForTests,
  getPermissionModeForConversationKey,
} from '@utils/permissions/permissionModeState'
import { getGlobalConfig, saveGlobalConfig } from '@utils/config'
import {
  getPlanModeSystemPromptAdditions,
  isPlanModeEnabled,
} from '@utils/plan/planMode'

describe('permission mode cycle parity (Reference CLI aB9 + side effects)', () => {
  beforeEach(() => {
    __resetPermissionModeStateForTests()
  })

  test('getNextPermissionMode matches reference CLI aB9 ordering', () => {
    expect(getNextPermissionMode('default', true)).toBe('acceptEdits')
    expect(getNextPermissionMode('acceptEdits', true)).toBe('plan')
    expect(getNextPermissionMode('plan', true)).toBe('bypassPermissions')
    expect(getNextPermissionMode('plan', false)).toBe('default')
    expect(getNextPermissionMode('bypassPermissions', true)).toBe('default')
    expect(getNextPermissionMode('dontAsk', true)).toBe('default')
  })

  test('cycle into plan records lastPlanModeUse + enables plan mode', () => {
    const messageLogName = 'perm-cycle-plan'
    const forkNumber = 0
    const conversationKey = `${messageLogName}:${forkNumber}`

    saveGlobalConfig({ ...(getGlobalConfig() as any), lastPlanModeUse: 0 })

    __applyPermissionModeSideEffectsForTests({
      conversationKey,
      previousMode: 'acceptEdits',
      nextMode: 'plan',
      recordPlanModeUse: true,
      now: () => 12345,
    })

    expect(
      getPermissionModeForConversationKey({
        conversationKey,
        isBypassPermissionsModeAvailable: true,
      }),
    ).toBe('plan')
    expect(
      isPlanModeEnabled({ options: { messageLogName, forkNumber } } as any),
    ).toBe(true)
    expect((getGlobalConfig() as any).lastPlanModeUse).toBe(12345)
  })

  test('setMode into plan does NOT record lastPlanModeUse (only shortcut cycle does)', () => {
    const messageLogName = 'perm-set-plan'
    const forkNumber = 0
    const conversationKey = `${messageLogName}:${forkNumber}`

    saveGlobalConfig({ ...(getGlobalConfig() as any), lastPlanModeUse: 0 })

    __applyPermissionModeSideEffectsForTests({
      conversationKey,
      previousMode: 'acceptEdits',
      nextMode: 'plan',
      recordPlanModeUse: false,
      now: () => 999,
    })

    expect(
      isPlanModeEnabled({ options: { messageLogName, forkNumber } } as any),
    ).toBe(true)
    expect((getGlobalConfig() as any).lastPlanModeUse).toBe(0)
  })

  test('leaving plan sets plan_mode_exit attachment flags (one-shot reminder)', () => {
    const messageLogName = 'perm-exit-plan'
    const forkNumber = 0
    const conversationKey = `${messageLogName}:${forkNumber}`
    const ctx = { options: { messageLogName, forkNumber } } as any

    __applyPermissionModeSideEffectsForTests({
      conversationKey,
      previousMode: 'acceptEdits',
      nextMode: 'plan',
      recordPlanModeUse: false,
    })

    expect(isPlanModeEnabled(ctx)).toBe(true)

    __applyPermissionModeSideEffectsForTests({
      conversationKey,
      previousMode: 'plan',
      nextMode: 'default',
      recordPlanModeUse: false,
    })

    expect(isPlanModeEnabled(ctx)).toBe(false)

    const first = getPlanModeSystemPromptAdditions([], ctx)
    expect(first.length).toBeGreaterThan(0)
    expect(first.join('\n')).toContain('Exited Plan Mode')

    const second = getPlanModeSystemPromptAdditions([], ctx)
    expect(second).toEqual([])
  })
})
