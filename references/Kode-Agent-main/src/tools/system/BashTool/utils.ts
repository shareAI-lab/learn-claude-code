import { queryQuick } from '@services/llmLazy'
import { extractTag } from '@utils/messages'
import { MAX_OUTPUT_LENGTH } from './prompt'

export function formatOutput(content: string): {
  totalLines: number
  truncatedContent: string
} {
  if (content.length <= MAX_OUTPUT_LENGTH) {
    return {
      totalLines: content.split('\n').length,
      truncatedContent: content,
    }
  }
  const halfLength = MAX_OUTPUT_LENGTH / 2
  const start = content.slice(0, halfLength)
  const end = content.slice(-halfLength)
  const truncated = `${start}\n\n... [${content.slice(halfLength, -halfLength).split('\n').length} lines truncated] ...\n\n${end}`

  return {
    totalLines: content.split('\n').length,
    truncatedContent: truncated,
  }
}

export async function getCommandFilePaths(
  command: string,
  output: string,
): Promise<string[]> {
  const response = await queryQuick({
    systemPrompt: [
      `Extract any file paths that this command reads or modifies. For commands like "git diff" and "cat", include the paths of files being shown. Use paths verbatim -- don't add any slashes or try to resolve them. Do not try to infer paths that were not explicitly listed in the command output.
Format your response as:
<filepaths>
path/to/file1
path/to/file2
</filepaths>

If no files are read or modified, return empty filepaths tags:
<filepaths>
</filepaths>

Do not include any other text in your response.`,
    ],
    userPrompt: `Command: ${command}\nOutput: ${output}`,
    enablePromptCaching: true,
  })
  const content = response.message.content
    .filter(_ => _.type === 'text')
    .map(_ => _.text)
    .join('')

  return (
    extractTag(content, 'filepaths')?.trim().split('\n').filter(Boolean) || []
  )
}
