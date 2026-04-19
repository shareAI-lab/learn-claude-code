import { describe, expect, test } from 'bun:test'
import { readdirSync, statSync } from 'node:fs'
import { basename, join } from 'node:path'

function listFilesRecursive(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const st = statSync(fullPath)
    if (st.isDirectory()) {
      out.push(...listFilesRecursive(fullPath))
      continue
    }
    out.push(fullPath)
  }
  return out
}

function isTsLikeFile(filePath: string): boolean {
  return (
    filePath.endsWith('.ts') ||
    filePath.endsWith('.tsx') ||
    filePath.endsWith('.d.ts')
  )
}

describe('Naming conventions', () => {
  test('src/utils root must not contain loose ts/tsx files', () => {
    const utilsDir = join(process.cwd(), 'src', 'utils')
    const entries = readdirSync(utilsDir, { withFileTypes: true })

    const violations: string[] = []
    for (const entry of entries) {
      if (!entry.isFile()) continue
      if (entry.name.startsWith('.')) continue
      if (isTsLikeFile(entry.name)) {
        violations.push(entry.name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/services root must not contain loose ts/tsx files', () => {
    const servicesDir = join(process.cwd(), 'src', 'services')
    const entries = readdirSync(servicesDir, { withFileTypes: true })

    const violations: string[] = []
    for (const entry of entries) {
      if (!entry.isFile()) continue
      if (entry.name.startsWith('.')) continue
      if (isTsLikeFile(entry.name)) {
        violations.push(entry.name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/utils file names must not start with uppercase letters', () => {
    const utilsDir = join(process.cwd(), 'src', 'utils')
    const files = listFilesRecursive(utilsDir).filter(isTsLikeFile)

    const violations: string[] = []
    for (const file of files) {
      const name = basename(file)
      if (/^[A-Z]/.test(name)) {
        violations.push(name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/types file names must not start with uppercase letters', () => {
    const typesDir = join(process.cwd(), 'src', 'types')
    const files = listFilesRecursive(typesDir).filter(isTsLikeFile)

    const violations: string[] = []
    for (const file of files) {
      const name = basename(file)
      if (/^[A-Z]/.test(name)) {
        violations.push(name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/ui/screens file names must start with uppercase letters', () => {
    const screensDir = join(process.cwd(), 'src', 'ui', 'screens')
    const files = listFilesRecursive(screensDir).filter(
      filePath => filePath.endsWith('.tsx') || filePath.endsWith('.ts'),
    )

    const violations: string[] = []
    for (const file of files) {
      const name = basename(file)
      if (!/^[A-Z]/.test(name)) {
        violations.push(name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/ui/components top-level directories must be lowercase', () => {
    const componentsDir = join(process.cwd(), 'src', 'ui', 'components')
    const entries = readdirSync(componentsDir, { withFileTypes: true })

    const violations: string[] = []
    for (const entry of entries) {
      if (!entry.isDirectory()) continue
      if (entry.name.startsWith('.')) continue
      if (entry.name !== entry.name.toLowerCase()) {
        violations.push(entry.name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/ui/components/messages subdirectories must be lowercase', () => {
    const messagesDir = join(process.cwd(), 'src', 'ui', 'components', 'messages')
    const entries = readdirSync(messagesDir, { withFileTypes: true })

    const violations: string[] = []
    for (const entry of entries) {
      if (!entry.isDirectory()) continue
      if (entry.name.startsWith('.')) continue
      if (entry.name !== entry.name.toLowerCase()) {
        violations.push(entry.name)
      }
    }

    expect(violations).toEqual([])
  })

  test('src/ui/components/permissions subdirectories must be lowercase', () => {
    const permissionsDir = join(
      process.cwd(),
      'src',
      'ui',
      'components',
      'permissions',
    )
    const entries = readdirSync(permissionsDir, { withFileTypes: true })

    const violations: string[] = []
    for (const entry of entries) {
      if (!entry.isDirectory()) continue
      if (entry.name.startsWith('.')) continue
      if (entry.name !== entry.name.toLowerCase()) {
        violations.push(entry.name)
      }
    }

    expect(violations).toEqual([])
  })
})
