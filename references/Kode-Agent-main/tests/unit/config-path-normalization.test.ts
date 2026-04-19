import { describe, expect, test } from 'bun:test'
import { normalizeProjectPathForComparison } from '../../src/core/config/loader'

describe('config path normalization', () => {
  test('expands ~ and normalizes posix paths', () => {
    const homeDir = '/Users/alice'
    const baseDir = '/Users/alice/work/repo'

    expect(
      normalizeProjectPathForComparison('~/work/repo', baseDir, {
        platform: 'darwin',
        homeDir,
      }),
    ).toBe('/Users/alice/work/repo')

    expect(
      normalizeProjectPathForComparison('~/work/repo/', baseDir, {
        platform: 'darwin',
        homeDir,
      }),
    ).toBe('/Users/alice/work/repo')
  })

  test('normalizes win32 drive letters, separators, and case', () => {
    const homeDir = 'C:\\Users\\Alice'
    const baseDir = 'C:\\Users\\Alice\\work\\repo'
    const expected = 'c:\\users\\alice\\work\\repo'

    expect(
      normalizeProjectPathForComparison('C:\\Users\\Alice\\work\\repo', baseDir, {
        platform: 'win32',
        homeDir,
      }),
    ).toBe(expected)

    expect(
      normalizeProjectPathForComparison('c:/Users/Alice/work/repo/', baseDir, {
        platform: 'win32',
        homeDir,
      }),
    ).toBe(expected)

    expect(
      normalizeProjectPathForComparison('~\\work\\repo', baseDir, {
        platform: 'win32',
        homeDir,
      }),
    ).toBe(expected)

    expect(
      normalizeProjectPathForComparison('~/work/repo', baseDir, {
        platform: 'win32',
        homeDir,
      }),
    ).toBe(expected)
  })

  test('returns empty string for empty/whitespace input', () => {
    expect(normalizeProjectPathForComparison('', '/', { platform: 'darwin' })).toBe(
      '',
    )
    expect(
      normalizeProjectPathForComparison('   ', '/', { platform: 'darwin' }),
    ).toBe('')
  })
})

