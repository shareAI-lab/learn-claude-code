import { readTextContent } from '@utils/fs/file'
import { fileFreshnessService } from '@services/fileFreshness'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

const MAX_FILES_TO_RECOVER = 5
const MAX_TOKENS_PER_FILE = 10_000
const MAX_TOTAL_FILE_TOKENS = 50_000

export async function selectAndReadFiles(): Promise<
  Array<{
    path: string
    content: string
    tokens: number
    truncated: boolean
  }>
> {
  const importantFiles =
    fileFreshnessService.getImportantFiles(MAX_FILES_TO_RECOVER)
  const results = []
  let totalTokens = 0

  for (const fileInfo of importantFiles) {
    try {
      const { content } = readTextContent(fileInfo.path)
      const estimatedTokens = Math.ceil(content.length * 0.25)

      let finalContent = content
      let truncated = false

      if (estimatedTokens > MAX_TOKENS_PER_FILE) {
        const maxChars = Math.floor(MAX_TOKENS_PER_FILE / 0.25)
        finalContent = content.substring(0, maxChars)
        truncated = true
      }

      const finalTokens = Math.min(estimatedTokens, MAX_TOKENS_PER_FILE)

      if (totalTokens + finalTokens > MAX_TOTAL_FILE_TOKENS) {
        break
      }

      totalTokens += finalTokens
      results.push({
        path: fileInfo.path,
        content: finalContent,
        tokens: finalTokens,
        truncated,
      })
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_RECOVERY_READ_FAILED', {
        path: fileInfo.path,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  return results
}
