import { test, expect } from 'bun:test'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const utils = require('../../scripts/binary-utils.cjs') as {
  getPlatformArch: (platform: string, arch: string) => string
  getBinaryFilename: (platform: string) => string
  getCachedBinaryPath: (opts: {
    version: string
    platform: string
    arch: string
    baseDir: string
  }) => string
  getGithubReleaseBinaryUrl: (opts: {
    version: string
    platform: string
    arch: string
    owner?: string
    repo?: string
    tag?: string
    baseUrl?: string
  }) => string
}

test('binary-utils: platform/arch and filenames', () => {
  expect(utils.getPlatformArch('darwin', 'arm64')).toBe('darwin-arm64')
  expect(utils.getPlatformArch('win32', 'x64')).toBe('win32-x64')
  expect(utils.getBinaryFilename('darwin')).toBe('kode')
  expect(utils.getBinaryFilename('linux')).toBe('kode')
  expect(utils.getBinaryFilename('win32')).toBe('kode.exe')
})

test('binary-utils: cached binary path', () => {
  expect(
    utils.getCachedBinaryPath({
      version: '2.0.0',
      platform: 'darwin',
      arch: 'arm64',
      baseDir: '/tmp/kode-bin',
    }),
  ).toBe('/tmp/kode-bin/2.0.0/darwin-arm64/kode')

  expect(
    utils.getCachedBinaryPath({
      version: '2.0.0',
      platform: 'win32',
      arch: 'x64',
      baseDir: '/tmp/kode-bin',
    }),
  ).toBe('/tmp/kode-bin/2.0.0/win32-x64/kode.exe')
})

test('binary-utils: GitHub release URL', () => {
  expect(
    utils.getGithubReleaseBinaryUrl({
      version: '2.0.0',
      platform: 'darwin',
      arch: 'arm64',
      owner: 'shareAI-lab',
      repo: 'kode',
      tag: 'v2.0.0',
    }),
  ).toBe(
    'https://github.com/shareAI-lab/kode/releases/download/v2.0.0/kode-darwin-arm64',
  )
})

test('binary-utils: base URL override', () => {
  const prev = process.env.KODE_BINARY_BASE_URL
  process.env.KODE_BINARY_BASE_URL = 'https://example.com/kode'
  try {
    expect(
      utils.getGithubReleaseBinaryUrl({
        version: '2.0.0',
        platform: 'linux',
        arch: 'x64',
      }),
    ).toBe('https://example.com/kode/kode-linux-x64')
  } finally {
    if (prev === undefined) delete process.env.KODE_BINARY_BASE_URL
    else process.env.KODE_BINARY_BASE_URL = prev
  }
})
