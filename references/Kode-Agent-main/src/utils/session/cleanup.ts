import { promises as fs } from 'fs'
import { join } from 'path'
import { logError, CACHE_PATHS } from '@utils/log'

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000

export type CleanupResult = {
  messages: number
  errors: number
}

export function convertFileNameToDate(filename: string): Date {
  const isoStr = filename
    .split('.')[0]!
    .replace(/T(\d{2})-(\d{2})-(\d{2})-(\d{3})Z/, 'T$1:$2:$3.$4Z')
  return new Date(isoStr)
}

export async function cleanupOldMessageFiles(): Promise<CleanupResult> {
  const messagePath = CACHE_PATHS.messages()
  const errorPath = CACHE_PATHS.errors()
  const thirtyDaysAgo = new Date(Date.now() - THIRTY_DAYS_MS)
  const deletedCounts: CleanupResult = { messages: 0, errors: 0 }

  for (const path of [messagePath, errorPath]) {
    try {
      const files = await fs.readdir(path)

      for (const file of files) {
        try {
          const timestamp = convertFileNameToDate(file)
          if (timestamp < thirtyDaysAgo) {
            await fs.unlink(join(path, file))
            if (path === messagePath) {
              deletedCounts.messages++
            } else {
              deletedCounts.errors++
            }
          }
        } catch (error: unknown) {
          logError(
            `Failed to process file ${file}: ${error instanceof Error ? error.message : String(error)}`,
          )
        }
      }
    } catch (error: unknown) {
      if (
        error instanceof Error &&
        'code' in error &&
        error.code !== 'ENOENT'
      ) {
        logError(
          `Failed to cleanup directory ${path}: ${error instanceof Error ? error.message : String(error)}`,
        )
      }
    }
  }

  return deletedCounts
}

export function cleanupOldMessageFilesInBackground(): void {
  const immediate = setImmediate(cleanupOldMessageFiles)

  immediate.unref()
}
