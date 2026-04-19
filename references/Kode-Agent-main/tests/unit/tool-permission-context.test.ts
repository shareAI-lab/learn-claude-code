import { describe, expect, test } from 'bun:test'
import {
  applyToolPermissionContextUpdate,
  applyToolPermissionContextUpdates,
  canUserModifyToolPermissionUpdate,
  createDefaultToolPermissionContext,
  isPersistableToolPermissionDestination,
} from '@kode-types/toolPermissionContext'

describe('toolPermissionContext (Reference CLI xC + mW parity)', () => {
  test('createDefaultToolPermissionContext matches reference CLI xC defaults', () => {
    const ctx = createDefaultToolPermissionContext()
    expect(ctx.mode).toBe('default')
    expect(ctx.isBypassPermissionsModeAvailable).toBe(false)
    expect(ctx.additionalWorkingDirectories).toBeInstanceOf(Map)
    expect(ctx.additionalWorkingDirectories.size).toBe(0)
    expect(ctx.alwaysAllowRules).toEqual({})
    expect(ctx.alwaysDenyRules).toEqual({})
    expect(ctx.alwaysAskRules).toEqual({})
  })

  test('applyToolPermissionContextUpdate supports setMode', () => {
    const ctx = createDefaultToolPermissionContext()
    const next = applyToolPermissionContextUpdate(ctx, {
      type: 'setMode',
      mode: 'plan',
      destination: 'session',
    })
    expect(next.mode).toBe('plan')
  })

  test('applyToolPermissionContextUpdate supports addRules/replaceRules/removeRules across behaviors', () => {
    const ctx = createDefaultToolPermissionContext()
    const withAllow = applyToolPermissionContextUpdate(ctx, {
      type: 'addRules',
      destination: 'session',
      behavior: 'allow',
      rules: ['Bash(ls:*)'],
    })
    expect(withAllow.alwaysAllowRules.session).toEqual(['Bash(ls:*)'])

    const withReplace = applyToolPermissionContextUpdate(withAllow, {
      type: 'replaceRules',
      destination: 'session',
      behavior: 'allow',
      rules: ['Bash(git:*)'],
    })
    expect(withReplace.alwaysAllowRules.session).toEqual(['Bash(git:*)'])

    const withDeny = applyToolPermissionContextUpdate(withReplace, {
      type: 'addRules',
      destination: 'projectSettings',
      behavior: 'deny',
      rules: ['WebFetch(domain:example.com)'],
    })
    expect(withDeny.alwaysDenyRules.projectSettings).toEqual([
      'WebFetch(domain:example.com)',
    ])

    const withAsk = applyToolPermissionContextUpdate(withDeny, {
      type: 'addRules',
      destination: 'userSettings',
      behavior: 'ask',
      rules: ['Read'],
    })
    expect(withAsk.alwaysAskRules.userSettings).toEqual(['Read'])

    const removed = applyToolPermissionContextUpdate(withAsk, {
      type: 'removeRules',
      destination: 'session',
      behavior: 'allow',
      rules: ['Bash(git:*)'],
    })
    expect(removed.alwaysAllowRules.session).toEqual([])
  })

  test('applyToolPermissionContextUpdate supports addDirectories/removeDirectories', () => {
    const ctx = createDefaultToolPermissionContext()
    const withDirs = applyToolPermissionContextUpdate(ctx, {
      type: 'addDirectories',
      destination: 'session',
      directories: ['/tmp/a', '/tmp/b'],
    })
    expect(withDirs.additionalWorkingDirectories.size).toBe(2)
    expect(withDirs.additionalWorkingDirectories.get('/tmp/a')).toEqual({
      path: '/tmp/a',
      source: 'session',
    })

    const withoutOne = applyToolPermissionContextUpdate(withDirs, {
      type: 'removeDirectories',
      destination: 'session',
      directories: ['/tmp/a'],
    })
    expect(withoutOne.additionalWorkingDirectories.size).toBe(1)
    expect(
      withoutOne.additionalWorkingDirectories.get('/tmp/a'),
    ).toBeUndefined()
  })

  test('applyToolPermissionContextUpdates applies updates in order', () => {
    const ctx = createDefaultToolPermissionContext()
    const out = applyToolPermissionContextUpdates(ctx, [
      { type: 'setMode', mode: 'acceptEdits', destination: 'session' },
      {
        type: 'addRules',
        destination: 'session',
        behavior: 'allow',
        rules: ['Bash(ls:*)'],
      },
    ])
    expect(out.mode).toBe('acceptEdits')
    expect(out.alwaysAllowRules.session).toEqual(['Bash(ls:*)'])
  })

  test('isPersistableToolPermissionDestination matches reference CLI TvA', () => {
    expect(isPersistableToolPermissionDestination('localSettings')).toBe(true)
    expect(isPersistableToolPermissionDestination('userSettings')).toBe(true)
    expect(isPersistableToolPermissionDestination('projectSettings')).toBe(true)
    expect(isPersistableToolPermissionDestination('session')).toBe(false)
    expect(isPersistableToolPermissionDestination('policySettings')).toBe(false)
  })

  test('canUserModifyToolPermissionUpdate blocks deletes/overwrites for policySettings', () => {
    expect(
      canUserModifyToolPermissionUpdate({
        type: 'replaceRules',
        destination: 'policySettings',
        behavior: 'allow',
        rules: ['Read'],
      }),
    ).toBe(false)

    expect(
      canUserModifyToolPermissionUpdate({
        type: 'removeRules',
        destination: 'policySettings',
        behavior: 'deny',
        rules: ['Read'],
      }),
    ).toBe(false)

    expect(
      canUserModifyToolPermissionUpdate({
        type: 'removeDirectories',
        destination: 'policySettings',
        directories: ['/tmp'],
      }),
    ).toBe(false)

    expect(
      canUserModifyToolPermissionUpdate({
        type: 'addRules',
        destination: 'policySettings',
        behavior: 'allow',
        rules: ['Read'],
      }),
    ).toBe(true)
  })
})
