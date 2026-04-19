import semver from 'semver'
import type { Key } from 'ink'

export type InputShortcut = {
  displayText: string
  check: (input: string, key: Key) => boolean
}

type RuntimeInfo = {
  platform: string
  bunVersion?: string
  nodeVersion?: string
}

function supportsShiftTabOnWindows(runtime: RuntimeInfo): boolean {
  if (runtime.platform !== 'win32') return true

  try {
    const bunVersion = runtime.bunVersion
    if (bunVersion) {
      return semver.satisfies(bunVersion, '>=1.2.23')
    }

    const nodeVersion = runtime.nodeVersion
    if (!nodeVersion) return false

    return semver.satisfies(nodeVersion, '>=22.17.0 <23.0.0 || >=24.2.0')
  } catch {
    return false
  }
}

function getRuntimeInfo(): RuntimeInfo {
  return {
    platform: process.platform,
    bunVersion: process.versions?.bun,
    nodeVersion: process.versions?.node,
  }
}

export function __getPermissionModeCycleShortcutForTests(
  runtime: RuntimeInfo,
): InputShortcut {
  if (!supportsShiftTabOnWindows(runtime)) {
    return {
      displayText: 'alt+m',
      check: (input, key) =>
        Boolean(key.meta) && (input === 'm' || input === 'M'),
    }
  }

  return {
    displayText: 'shift+tab',
    check: (_input, key) => Boolean(key.tab) && Boolean(key.shift),
  }
}

export function getPermissionModeCycleShortcut(): InputShortcut {
  return __getPermissionModeCycleShortcutForTests(getRuntimeInfo())
}
