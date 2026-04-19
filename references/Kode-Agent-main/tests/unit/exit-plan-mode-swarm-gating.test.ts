import { describe, expect, test } from 'bun:test'
import { __getExitPlanModeOptionsForTests } from '@components/permissions/plan-mode-permission-request/ExitPlanModePermissionRequest'

describe('ExitPlanMode swarm option gating', () => {
  test('does not include launch swarm option when gated off', () => {
    const options = __getExitPlanModeOptionsForTests({
      bypassAvailable: true,
      launchSwarmAvailable: false,
      teammateCount: 3,
    })

    expect(options.map(o => o.value)).toEqual([
      'yes-bypass',
      'yes-default',
      'no',
    ])
  })

  test('includes launch swarm option when gated on', () => {
    const options = __getExitPlanModeOptionsForTests({
      bypassAvailable: true,
      launchSwarmAvailable: true,
      teammateCount: 4,
    })

    expect(options.map(o => o.value)).toEqual([
      'yes-bypass',
      'yes-launch-swarm',
      'yes-default',
      'no',
    ])
    expect(options[1]?.label).toContain('4')
  })
})
