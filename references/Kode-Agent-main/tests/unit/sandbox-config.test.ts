import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import type { KodeSettingsFile } from '@utils/sandbox/sandboxConfig'
import {
  getLinuxSandboxGlobPatternWarnings,
  normalizeSandboxRuntimeConfigFromSettings,
} from '@utils/sandbox/sandboxConfig'

describe('sandbox config (Reference CLI parity: YC1 + z34)', () => {
  let projectDir: string
  let homeDir: string

  beforeEach(() => {
    projectDir = mkdtempSync(join(tmpdir(), 'kode-sandbox-project-'))
    homeDir = mkdtempSync(join(tmpdir(), 'kode-sandbox-home-'))
  })

  afterEach(() => {
    rmSync(projectDir, { recursive: true, force: true })
    rmSync(homeDir, { recursive: true, force: true })
  })

  test('normalizes network + filesystem config from settings + permissions rules', () => {
    const settings: KodeSettingsFile = {
      permissions: {
        allow: ['WebFetch(domain:api.example.com)', 'Edit(src/**)'],
        deny: [
          'WebFetch(domain:blocked.example.com)',
          'Read(secrets/**)',
          'Edit(vendor/**)',
        ],
      },
      sandbox: {
        network: {
          allowedDomains: ['example.org'],
          allowUnixSockets: ['/var/run/docker.sock'],
          allowAllUnixSockets: false,
          allowLocalBinding: true,
          httpProxyPort: 3128,
          socksProxyPort: 1080,
        },
        ignoreViolations: true,
        enableWeakerNestedSandbox: false,
        excludedCommands: ['git'],
        ripgrep: { command: 'rg-custom', args: ['--hidden'] },
      },
    }

    const runtime = normalizeSandboxRuntimeConfigFromSettings(settings, {
      projectDir,
      homeDir,
      defaultRipgrep: { command: 'rg', args: ['--smart-case'] },
    })

    expect(runtime.network.allowedDomains).toEqual([
      'example.org',
      'api.example.com',
    ])
    expect(runtime.network.deniedDomains).toEqual(['blocked.example.com'])
    expect(runtime.network.allowUnixSockets).toEqual(['/var/run/docker.sock'])
    expect(runtime.network.allowAllUnixSockets).toBe(false)
    expect(runtime.network.allowLocalBinding).toBe(true)
    expect(runtime.network.httpProxyPort).toBe(3128)
    expect(runtime.network.socksProxyPort).toBe(1080)

    expect(runtime.filesystem.allowWrite).toEqual(['.', 'src/**'])
    expect(runtime.filesystem.denyRead).toEqual(['secrets/**'])
    expect(runtime.filesystem.denyWrite).toContain(
      join(homeDir, '.kode', 'settings.json'),
    )
    expect(runtime.filesystem.denyWrite).toContain(
      join(projectDir, '.kode', 'settings.json'),
    )
    expect(runtime.filesystem.denyWrite).toContain(
      join(projectDir, '.kode', 'settings.local.json'),
    )
    expect(runtime.filesystem.denyWrite).toContain(
      join(homeDir, '.claude', 'settings.json'),
    )
    expect(runtime.filesystem.denyWrite).toContain(
      join(projectDir, '.claude', 'settings.json'),
    )
    expect(runtime.filesystem.denyWrite).toContain(
      join(projectDir, '.claude', 'settings.local.json'),
    )
    expect(runtime.filesystem.denyWrite).toContain('vendor/**')

    expect(runtime.ignoreViolations).toBe(true)
    expect(runtime.enableWeakerNestedSandbox).toBe(false)
    expect(runtime.excludedCommands).toEqual(['git'])
    expect(runtime.ripgrep).toEqual({
      command: 'rg-custom',
      args: ['--hidden'],
    })
  })

  test('normalizes ripgrep to default when not specified', () => {
    const settings: KodeSettingsFile = {
      permissions: { allow: [], deny: [] },
      sandbox: { network: { allowedDomains: [] } },
    }

    const runtime = normalizeSandboxRuntimeConfigFromSettings(settings, {
      projectDir,
      homeDir,
      defaultRipgrep: { command: 'rg', args: ['--no-heading'] },
    })

    expect(runtime.ripgrep).toEqual({ command: 'rg', args: ['--no-heading'] })
  })

  test('Linux glob warnings: only when sandbox.enabled === true and platform is linux', () => {
    const settings: KodeSettingsFile = {
      permissions: {
        allow: ['Edit(src/*)', 'Read(~/**)', 'Bash(ls)'],
        deny: ['Read(secrets/*)', 'Edit(docs/**)'],
      },
      sandbox: { enabled: true },
    }

    expect(
      getLinuxSandboxGlobPatternWarnings(settings, { platform: 'darwin' }),
    ).toEqual([])
    expect(
      getLinuxSandboxGlobPatternWarnings(
        { ...settings, sandbox: { enabled: false } },
        { platform: 'linux' },
      ),
    ).toEqual([])

    expect(
      getLinuxSandboxGlobPatternWarnings(settings, { platform: 'linux' }),
    ).toEqual(['Edit(src/*)', 'Read(secrets/*)'])
  })
})
