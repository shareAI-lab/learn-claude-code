import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { getBashDestructiveCommandBlock } from '@utils/sandbox/destructiveCommandGuard'

describe('destructiveCommandGuard (BashTool)', () => {
  const ENV_ALLOW = 'KODE_ALLOW_DESTRUCTIVE_RM'
  const originalEnv = process.env[ENV_ALLOW]

  beforeEach(() => {
    delete process.env[ENV_ALLOW]
  })

  afterEach(() => {
    if (originalEnv === undefined) delete process.env[ENV_ALLOW]
    else process.env[ENV_ALLOW] = originalEnv
  })

  test('does not apply to user_bash_mode', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf /',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'user_bash_mode',
    })
    expect(block).toBeNull()
  })

  test('blocks rm targeting filesystem root', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf /',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
    })
    expect(block?.message).toContain('critical directory')
    expect(block?.resolvedTarget).toBe('/')
  })

  test('blocks rm targeting home directory via ~', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf ~',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
    })
    expect(block?.message).toContain('critical directory')
    expect(block?.resolvedTarget).toBe('/Users/alice')
  })

  test('blocks rm targeting original working directory via .', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf .',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
    })
    expect(block?.resolvedTarget).toBe('/Users/alice/project')
  })

  test('blocks rm targeting top-level system directories', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'sudo rm -rf /usr',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
    })
    expect(block?.resolvedTarget).toBe('/usr')
  })

  test('blocks shell-expanded targets', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf $HOME',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
    })
    expect(block?.message).toContain('shell expansion')
  })

  test('allows non-critical removals inside project', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf node_modules',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
    })
    expect(block).toBeNull()
  })

  test('allows when override flag is passed', () => {
    const block = getBashDestructiveCommandBlock({
      command: 'rm -rf /',
      cwd: '/Users/alice/project',
      originalCwd: '/Users/alice/project',
      homeDir: '/Users/alice',
      platform: 'darwin',
      commandSource: 'agent_call',
      allowOverride: true,
    })
    expect(block).toBeNull()
  })
})
