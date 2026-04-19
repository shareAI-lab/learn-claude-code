import { existsSync, readdirSync, statSync } from 'fs'
import { basename, dirname, join, resolve } from 'path'
import type { UnifiedSuggestion } from './types'

export function generateFileSuggestions(args: {
  prefix: string
  cwd: string
}): UnifiedSuggestion[] {
  const { prefix, cwd } = args

  try {
    const userPath = prefix || '.'
    const isAbsolutePath = userPath.startsWith('/')
    const isHomePath = userPath.startsWith('~')

    let searchPath: string
    if (isHomePath) {
      searchPath = userPath.replace('~', process.env.HOME || '')
    } else if (isAbsolutePath) {
      searchPath = userPath
    } else {
      searchPath = resolve(cwd, userPath)
    }

    const endsWithSlash = userPath.endsWith('/')
    const searchStat = existsSync(searchPath) ? statSync(searchPath) : null

    let searchDir: string
    let nameFilter: string

    if (endsWithSlash || searchStat?.isDirectory()) {
      searchDir = searchPath
      nameFilter = ''
    } else {
      searchDir = dirname(searchPath)
      nameFilter = basename(searchPath)
    }

    if (!existsSync(searchDir)) return []

    const showHidden = nameFilter.startsWith('.') || userPath.includes('/.')
    const entries = readdirSync(searchDir)
      .filter(entry => {
        if (!showHidden && entry.startsWith('.')) return false
        if (
          nameFilter &&
          !entry.toLowerCase().startsWith(nameFilter.toLowerCase())
        )
          return false
        return true
      })
      .sort((a, b) => {
        const aPath = join(searchDir, a)
        const bPath = join(searchDir, b)
        const aIsDir = statSync(aPath).isDirectory()
        const bIsDir = statSync(bPath).isDirectory()

        if (aIsDir && !bIsDir) return -1
        if (!aIsDir && bIsDir) return 1

        return a.toLowerCase().localeCompare(b.toLowerCase())
      })
      .slice(0, 25)

    return entries.map(entry => {
      const entryPath = join(searchDir, entry)
      const isDir = statSync(entryPath).isDirectory()
      const icon = isDir ? '📁' : '📄'

      let value: string

      if (userPath.includes('/')) {
        if (endsWithSlash) {
          value = userPath + entry + (isDir ? '/' : '')
        } else if (searchStat?.isDirectory()) {
          value = userPath + '/' + entry + (isDir ? '/' : '')
        } else {
          const userDir = userPath.includes('/')
            ? userPath.substring(0, userPath.lastIndexOf('/'))
            : ''
          value = userDir
            ? userDir + '/' + entry + (isDir ? '/' : '')
            : entry + (isDir ? '/' : '')
        }
      } else {
        if (searchStat?.isDirectory()) {
          value = userPath + '/' + entry + (isDir ? '/' : '')
        } else {
          value = entry + (isDir ? '/' : '')
        }
      }

      return {
        value,
        displayValue: `${icon} ${entry}${isDir ? '/' : ''}`,
        type: 'file' as const,
        score: isDir ? 80 : 70,
      }
    })
  } catch {
    return []
  }
}
