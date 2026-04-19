import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { dirname, join } from 'path'
import { __resetKodeHooksCacheForTests, runStopHooks } from '@utils/session/kodeHooks'
import { setCwd } from '@utils/state'

function writeJson(path: string, value: unknown) {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, JSON.stringify(value, null, 2) + '\n', 'utf8')
}

describe('Hooks: Stop JSON decision semantics', () => {
  const runnerCwd = process.cwd()

  let projectDir: string

  beforeEach(async () => {
    __resetKodeHooksCacheForTests()
    projectDir = mkdtempSync(join(tmpdir(), 'kode-stop-hooks-project-'))
    await setCwd(projectDir)
  })

  afterEach(async () => {
    await setCwd(runnerCwd)
    __resetKodeHooksCacheForTests()
    rmSync(projectDir, { recursive: true, force: true })
  })

  test('decision:block prevents stop even when hook exits 0', async () => {
    const hookPath = join(projectDir, 'stop-hook.js')
    writeFileSync(
      hookPath,
      `
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let data = {};
try { data = JSON.parse(raw); } catch {}
if (data.hook_event_name !== 'Stop') { console.error('BAD hook_event_name'); process.exit(2); }
process.stdout.write(JSON.stringify({ decision: 'block', reason: 'NEED_MORE', systemMessage: 'NEED_MORE' }));
process.exit(0);
`,
      'utf8',
    )

    writeJson(join(projectDir, '.claude', 'settings.json'), {
      hooks: {
        Stop: [
          {
            matcher: '*',
            hooks: [{ type: 'command', command: `bun \"${hookPath}\"` }],
          },
        ],
      },
    })

    const outcome = await runStopHooks({
      hookEvent: 'Stop',
      reason: 'end_turn',
      cwd: projectDir,
    })

    expect(outcome.decision).toBe('block')
    if (outcome.decision === 'block') {
      expect(outcome.message).toContain('NEED_MORE')
    }
  })

  test('empty JSON approves stop', async () => {
    const hookPath = join(projectDir, 'stop-hook-approve.js')
    writeFileSync(
      hookPath,
      `
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let data = {};
try { data = JSON.parse(raw); } catch {}
if (data.hook_event_name !== 'Stop') { console.error('BAD hook_event_name'); process.exit(2); }
process.stdout.write(JSON.stringify({}));
process.exit(0);
`,
      'utf8',
    )

    writeJson(join(projectDir, '.claude', 'settings.json'), {
      hooks: {
        Stop: [
          {
            matcher: '*',
            hooks: [{ type: 'command', command: `bun \"${hookPath}\"` }],
          },
        ],
      },
    })

    const outcome = await runStopHooks({
      hookEvent: 'Stop',
      reason: 'end_turn',
      cwd: projectDir,
    })

    expect(outcome.decision).toBe('approve')
  })
})
