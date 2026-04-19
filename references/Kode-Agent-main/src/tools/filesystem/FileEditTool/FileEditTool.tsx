import { Hunk } from 'diff'
import { mkdirSync, readFileSync, statSync } from 'fs'
import { Box, Text } from 'ink'
import { dirname, isAbsolute, relative, resolve, sep } from 'path'
import * as React from 'react'
import { z } from 'zod'
import { FileEditToolUpdatedMessage } from '@components/FileEditToolUpdatedMessage'
import { StructuredDiff } from '@components/StructuredDiff'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool, ValidationResult } from '@tool'
import { intersperse } from '@utils/text/array'
import {
  addLineNumbers,
  detectFileEncoding,
  detectLineEndings,
  findSimilarFile,
  writeTextContent,
} from '@utils/fs/file'
import { readFileBun, fileExistsBun } from '@utils/bun/file'
import { logError } from '@utils/log'
import { getCwd } from '@utils/state'
import { getTheme } from '@utils/theme'
import { emitReminderEvent } from '@services/systemReminder'
import { recordFileEdit } from '@services/fileFreshness'
import { NotebookEditTool } from '@tools/NotebookEditTool/NotebookEditTool'
import { DESCRIPTION } from './prompt'
import { applyEdit } from './utils'
import { hasWritePermission } from '@utils/permissions/filesystem'
import { PROJECT_FILE } from '@constants/product'
import { normalizeLineEndings } from '@utils/terminal/paste'
import { getPatch } from '@utils/text/diff'

const inputSchema = z.strictObject({
  file_path: z.string().describe('The absolute path to the file to modify'),
  old_string: z.string().describe('The text to replace'),
  new_string: z.string().describe('The text to replace it with'),
  replace_all: z
    .boolean()
    .optional()
    .describe('Replace all occurences of old_string (default false)'),
})

export type In = typeof inputSchema

const N_LINES_SNIPPET = 4

export const FileEditTool = {
  name: 'Edit',
  async description() {
    return 'A tool for editing files'
  },
  async prompt() {
    return DESCRIPTION
  },
  inputSchema,
  userFacingName() {
    return 'Edit'
  },
  async isEnabled() {
    return true
  },
  isReadOnly() {
    return false
  },
  isConcurrencySafe() {
    return false
  },
  needsPermissions({ file_path }) {
    return !hasWritePermission(file_path)
  },
  renderToolUseMessage(input, { verbose }) {
    return `file_path: ${verbose ? input.file_path : relative(getCwd(), input.file_path)}`
  },
  renderToolResultMessage({ filePath, structuredPatch }) {
    const verbose = false
    return (
      <FileEditToolUpdatedMessage
        filePath={filePath}
        structuredPatch={structuredPatch}
        verbose={verbose}
      />
    )
  },
  renderToolUseRejectedMessage(
    { file_path, old_string, new_string, replace_all }: any = {},
    { columns, verbose }: any = {},
  ) {
    try {
      if (!file_path) {
        return <FallbackToolUseRejectedMessage />
      }
      const fullFilePath = isAbsolute(file_path)
        ? file_path
        : resolve(getCwd(), file_path)

      let originalFile = ''
      let updatedFile = ''
      if (old_string === '') {
        originalFile = ''
        updatedFile = normalizeLineEndings(new_string)
      } else {
        const enc = detectFileEncoding(fullFilePath)
        const fileContent = readFileSync(fullFilePath, enc)
        originalFile = normalizeLineEndings(fileContent ?? '')

        const normalizedOldString = normalizeLineEndings(old_string)
        const normalizedNewString = normalizeLineEndings(new_string)
        const oldStringForReplace =
          normalizedNewString === '' &&
          !normalizedOldString.endsWith('\n') &&
          originalFile.includes(normalizedOldString + '\n')
            ? normalizedOldString + '\n'
            : normalizedOldString

        updatedFile = Boolean(replace_all)
          ? originalFile.split(oldStringForReplace).join(normalizedNewString)
          : originalFile.replace(oldStringForReplace, () => normalizedNewString)

        if (updatedFile === originalFile) {
          throw new Error(
            'Original and edited file match exactly. Failed to apply edit.',
          )
        }
      }

      const patch = getPatch({
        filePath: file_path,
        fileContents: originalFile,
        oldStr: originalFile,
        newStr: updatedFile,
      })
      return (
        <Box flexDirection="column">
          <Text>
            {'  '}⎿{' '}
            <Text color={getTheme().error}>
              User rejected {old_string === '' ? 'write' : 'update'} to{' '}
            </Text>
            <Text bold>
              {verbose ? file_path : relative(getCwd(), file_path)}
            </Text>
          </Text>
          {intersperse(
            patch.map(patch => (
              <Box flexDirection="column" paddingLeft={5} key={patch.newStart}>
                <StructuredDiff patch={patch} dim={true} width={columns - 12} />
              </Box>
            )),
            i => (
              <Box paddingLeft={5} key={`ellipsis-${i}`}>
                <Text color={getTheme().secondaryText}>...</Text>
              </Box>
            ),
          )}
        </Box>
      )
    } catch (e) {
      logError(e)
      return (
        <Box flexDirection="column">
          <Text>{'  '}⎿ (No changes)</Text>
        </Box>
      )
    }
  },
  async validateInput(
    { file_path, old_string, new_string, replace_all },
    { readFileTimestamps },
  ) {
    if (old_string === new_string) {
      return {
        result: false,
        message:
          'No changes to make: old_string and new_string are exactly the same.',
        meta: {
          old_string,
        },
      } as ValidationResult
    }

    const fullFilePath = isAbsolute(file_path)
      ? file_path
      : resolve(getCwd(), file_path)

    if (old_string === '') {
      if (!fileExistsBun(fullFilePath)) return { result: true }
      const existingContent = await readFileBun(fullFilePath)
      if (normalizeLineEndings(existingContent ?? '').trim() !== '') {
        return {
          result: false,
          message: 'Cannot create new file - file already exists.',
        }
      }
      return { result: true }
    }

    if (!fileExistsBun(fullFilePath)) {
      const similarFilename = findSimilarFile(fullFilePath)
      let message = 'File does not exist.'

      if (similarFilename) {
        message += ` Did you mean ${similarFilename}?`
      }

      return {
        result: false,
        message,
      }
    }

    if (fullFilePath.endsWith('.ipynb')) {
      return {
        result: false,
        message: `File is a Jupyter Notebook. Use the ${NotebookEditTool.name} to edit this file.`,
      }
    }

    const readTimestamp = readFileTimestamps[fullFilePath]
    if (!readTimestamp) {
      return {
        result: false,
        message:
          'File has not been read yet. Read it first before writing to it.',
        meta: {
          isFilePathAbsolute: String(isAbsolute(file_path)),
        },
      }
    }

    const stats = statSync(fullFilePath)
    const lastWriteTime = stats.mtimeMs
    if (lastWriteTime > readTimestamp) {
      return {
        result: false,
        message:
          'File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.',
      }
    }

    const file = await readFileBun(fullFilePath)
    const normalizedFile = normalizeLineEndings(file ?? '')
    const normalizedOldString = normalizeLineEndings(old_string)
    if (!file) {
      return {
        result: false,
        message: 'Could not read file.',
        meta: {
          isFilePathAbsolute: String(isAbsolute(file_path)),
        },
      }
    }
    if (!normalizedFile.includes(normalizedOldString)) {
      return {
        result: false,
        message: `String to replace not found in file.\nString: ${old_string}`,
        meta: {
          isFilePathAbsolute: String(isAbsolute(file_path)),
        },
      }
    }

    const matches = normalizedFile.split(normalizedOldString).length - 1
    if (matches > 1 && !replace_all) {
      return {
        result: false,
        message: `Found ${matches} matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.\nString: ${old_string}`,
        meta: {
          isFilePathAbsolute: String(isAbsolute(file_path)),
        },
      }
    }

    return { result: true }
  },
  async *call(
    { file_path, old_string, new_string, replace_all },
    { readFileTimestamps },
  ) {
    const fullFilePath = isAbsolute(file_path)
      ? file_path
      : resolve(getCwd(), file_path)

    if (fileExistsBun(fullFilePath)) {
      const readTimestamp = readFileTimestamps[fullFilePath]
      const lastWriteTime = statSync(fullFilePath).mtimeMs
      if (!readTimestamp || lastWriteTime > readTimestamp) {
        throw new Error(
          'File has been unexpectedly modified. Read it again before attempting to write it.',
        )
      }
    }

    const { patch, updatedFile } = await applyEdit(
      file_path,
      old_string,
      new_string,
      replace_all ?? false,
    )

    const dir = dirname(fullFilePath)
    mkdirSync(dir, { recursive: true })
    const enc = fileExistsBun(fullFilePath)
      ? detectFileEncoding(fullFilePath)
      : 'utf8'
    const endings = fileExistsBun(fullFilePath)
      ? detectLineEndings(fullFilePath)
      : 'LF'
    const originalFile = fileExistsBun(fullFilePath)
      ? normalizeLineEndings((await readFileBun(fullFilePath)) ?? '')
      : ''
    writeTextContent(fullFilePath, updatedFile, enc, endings)

    recordFileEdit(fullFilePath, updatedFile)

    readFileTimestamps[fullFilePath] = statSync(fullFilePath).mtimeMs

    emitReminderEvent('file:edited', {
      filePath: fullFilePath,
      oldString: old_string,
      newString: new_string,
      timestamp: Date.now(),
      operation:
        old_string === '' ? 'create' : new_string === '' ? 'delete' : 'update',
    })

    const data = {
      filePath: file_path,
      oldString: old_string,
      newString: new_string,
      originalFile,
      structuredPatch: patch,
    }
    yield {
      type: 'result',
      data,
      resultForAssistant: this.renderResultForAssistant(data),
    }
  },
  renderResultForAssistant({ filePath, originalFile, oldString, newString }) {
    const { snippet, startLine } = getSnippet(
      normalizeLineEndings(originalFile || ''),
      normalizeLineEndings(oldString),
      normalizeLineEndings(newString),
    )
    return `The file ${filePath} has been updated. Here's the result of running \`cat -n\` on a snippet of the edited file:
${addLineNumbers({
  content: snippet,
  startLine,
})}`
  },
} satisfies Tool<
  typeof inputSchema,
  {
    filePath: string
    oldString: string
    newString: string
    originalFile: string
    structuredPatch: Hunk[]
  }
>

export function getSnippet(
  initialText: string,
  oldStr: string,
  newStr: string,
): { snippet: string; startLine: number } {
  const before = initialText.split(oldStr)[0] ?? ''
  const replacementLine = before.split(/\r?\n/).length - 1
  const newFileLines = initialText.replace(oldStr, newStr).split(/\r?\n/)
  const startLine = Math.max(0, replacementLine - N_LINES_SNIPPET)
  const endLine =
    replacementLine + N_LINES_SNIPPET + newStr.split(/\r?\n/).length
  const snippetLines = newFileLines.slice(startLine, endLine + 1)
  const snippet = snippetLines.join('\n')
  return { snippet, startLine: startLine + 1 }
}
