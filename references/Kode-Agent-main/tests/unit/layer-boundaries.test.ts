import { describe, expect, test } from 'bun:test'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'

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

function listPathsRecursive(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const st = statSync(fullPath)
    out.push(fullPath)
    if (st.isDirectory()) {
      out.push(...listPathsRecursive(fullPath))
    }
  }
  return out
}

function readText(filePath: string): string {
  return readFileSync(filePath, 'utf8')
}

function findForbiddenNeedles(
  dir: string,
  forbiddenNeedles: string[],
): Array<{ file: string; match: string }> {
  const files = listFilesRecursive(dir).filter(
    p => p.endsWith('.ts') || p.endsWith('.tsx'),
  )
  const violations: Array<{ file: string; match: string }> = []

  for (const file of files) {
    const text = readText(file)
    for (const needle of forbiddenNeedles) {
      if (text.includes(needle)) {
        violations.push({ file, match: needle })
      }
    }
  }

  return violations
}

describe('Layer boundaries', () => {
  test('services layer must not import ui layer', () => {
    const servicesDir = join(process.cwd(), 'src', 'services')
    const forbidden = [
      '@components',
      '@screens',
      '@hooks',
      "from '../ui/",
      'from "../ui/',
      "from '../ui'",
      'from "../ui"',
      "from './ui/",
      'from "./ui/',
      "from './ui'",
      'from "./ui"',
      "from '@ui/",
      'from "@ui/',
      "from '@ui'",
      'from "@ui"',
    ]
    expect(findForbiddenNeedles(servicesDir, forbidden)).toEqual([])
  })

  test('core layer must not import ui layer', () => {
    const coreDir = join(process.cwd(), 'src', 'core')
    const forbidden = [
      '@components',
      '@screens',
      '@hooks',
      "from '../ui/",
      'from "../ui/',
      "from '../ui'",
      'from "../ui"',
      "from './ui/",
      'from "./ui/',
      "from './ui'",
      'from "./ui"',
      "from '@ui/",
      'from "@ui/',
      "from '@ui'",
      'from "@ui"',
    ]
    expect(findForbiddenNeedles(coreDir, forbidden)).toEqual([])
  })

  test('src/ root must contain only lowercase directories', () => {
    const srcDir = join(process.cwd(), 'src')
    const entries = readdirSync(srcDir, { withFileTypes: true })

    const violations: Array<{ entry: string; reason: string }> = []
    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue
      if (!entry.isDirectory()) {
        violations.push({ entry: entry.name, reason: 'not a directory' })
        continue
      }
      if (entry.name !== entry.name.toLowerCase()) {
        violations.push({ entry: entry.name, reason: 'not lowercase' })
      }
    }

    expect(violations).toEqual([])
  })

  test('src/ tree must not have case-insensitive path collisions', () => {
    const srcDir = join(process.cwd(), 'src')
    const allPaths = listPathsRecursive(srcDir)

    const collisions: Array<{ a: string; b: string }> = []
    const seen = new Map<string, string>()

    for (const fullPath of allPaths) {
      const rel = relative(srcDir, fullPath)
      if (!rel || rel.startsWith('.')) continue

      const normalized = rel.split(sep).join('/')
      const key = normalized.toLowerCase()
      const prior = seen.get(key)

      if (!prior) {
        seen.set(key, normalized)
        continue
      }

      if (prior !== normalized) {
        collisions.push({ a: prior, b: normalized })
      }
    }

    expect(collisions).toEqual([])
  })
})
