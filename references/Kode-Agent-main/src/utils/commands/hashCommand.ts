import { join } from 'path'
import { readFileSync, writeFileSync } from 'fs'
import { logError } from '@utils/log'

export function handleHashCommand(interpreted: string): void {
  try {
    const cwd = process.cwd()
    const agentsPath = join(cwd, 'AGENTS.md')
    const legacyPath = join(cwd, 'CLAUDE.md')

    const filesToUpdate: Array<{ path: string; name: string }> = []

    filesToUpdate.push({ path: agentsPath, name: 'AGENTS.md' })

    try {
      readFileSync(legacyPath, 'utf-8')
      filesToUpdate.push({ path: legacyPath, name: 'CLAUDE.md' })
    } catch {
    }

    const now = new Date()
    const timezoneMatch = now.toString().match(/\(([A-Z]+)\)/)
    const timezone = timezoneMatch
      ? timezoneMatch[1]
      : now
          .toLocaleTimeString('en-us', { timeZoneName: 'short' })
          .split(' ')
          .pop()

    const timestamp = interpreted.includes(now.getFullYear().toString())
      ? ''
      : `\n\n_Added on ${now.toLocaleString()} ${timezone}_`

    const updatedFiles: string[] = []

    for (const file of filesToUpdate) {
      try {
        let existingContent = ''
        try {
          existingContent = readFileSync(file.path, 'utf-8').trim()
        } catch {
        }

        const separator = existingContent ? '\n\n' : ''
        const newContent = `${existingContent}${separator}${interpreted}${timestamp}`
        writeFileSync(file.path, newContent, 'utf-8')
        updatedFiles.push(file.name)
      } catch (error) {
        logError(error)
      }
    }
  } catch (e) {
    logError(e)
  }
}
