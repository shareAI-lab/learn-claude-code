import { dirname, isAbsolute, resolve, relative } from 'path'
import { statSync } from 'fs'
import { getCwd, getOriginalCwd } from '@utils/state'
import { isMainPlanFilePathForActiveConversation } from '@utils/plan/planMode'

const readFileAllowedDirectories: Set<string> = new Set()
const writeFileAllowedDirectories: Set<string> = new Set()

export function toAbsolutePath(path: string): string {
  const abs = isAbsolute(path) ? resolve(path) : resolve(getCwd(), path)
  return normalizeForCompare(abs)
}

function normalizeForCompare(p: string): string {
  const norm = resolve(p)
  return process.platform === 'win32' ? norm.toLowerCase() : norm
}

function isSubpath(base: string, target: string): boolean {
  const rel = relative(base, target)
  if (!rel || rel === '') return true
  if (rel.startsWith('..')) return false
  if (isAbsolute(rel)) return false
  return true
}

function pathToPermissionDirectory(path: string): string {
  try {
    const stats = statSync(path)
    if (stats.isDirectory()) return path
  } catch {
  }
  return dirname(path)
}

export function pathInOriginalCwd(path: string): boolean {
  const absolutePath = toAbsolutePath(path)
  const base = toAbsolutePath(getOriginalCwd())
  return isSubpath(base, absolutePath)
}

export function hasReadPermission(directory: string): boolean {
  if (isMainPlanFilePathForActiveConversation(directory)) return true
  const absolutePath = toAbsolutePath(directory)
  for (const allowedPath of readFileAllowedDirectories) {
    if (isSubpath(allowedPath, absolutePath)) return true
  }
  return false
}

export function hasWritePermission(directory: string): boolean {
  if (isMainPlanFilePathForActiveConversation(directory)) return true
  const absolutePath = toAbsolutePath(directory)
  for (const allowedPath of writeFileAllowedDirectories) {
    if (isSubpath(allowedPath, absolutePath)) return true
  }
  return false
}

function saveReadPermission(directory: string): void {
  const absolutePath = toAbsolutePath(directory)
  for (const allowedPath of Array.from(readFileAllowedDirectories)) {
    if (isSubpath(absolutePath, allowedPath)) {
      readFileAllowedDirectories.delete(allowedPath)
    }
  }
  readFileAllowedDirectories.add(absolutePath)
}

export const saveReadPermissionForTest = saveReadPermission

export function grantReadPermissionForOriginalDir(): void {
  const originalProjectDir = getOriginalCwd()
  saveReadPermission(originalProjectDir)
}

export function grantReadPermissionForPath(path: string): void {
  const absolutePath = toAbsolutePath(path)
  saveReadPermission(pathToPermissionDirectory(absolutePath))
}

function saveWritePermission(directory: string): void {
  const absolutePath = toAbsolutePath(directory)
  for (const allowedPath of Array.from(writeFileAllowedDirectories)) {
    if (isSubpath(absolutePath, allowedPath)) {
      writeFileAllowedDirectories.delete(allowedPath)
    }
  }
  writeFileAllowedDirectories.add(absolutePath)
}

export function grantWritePermissionForOriginalDir(): void {
  const originalProjectDir = getOriginalCwd()
  saveWritePermission(originalProjectDir)
}

export function grantWritePermissionForPath(path: string): void {
  const absolutePath = toAbsolutePath(path)
  saveWritePermission(pathToPermissionDirectory(absolutePath))
}

export function clearFilePermissions(): void {
  readFileAllowedDirectories.clear()
  writeFileAllowedDirectories.clear()
}
