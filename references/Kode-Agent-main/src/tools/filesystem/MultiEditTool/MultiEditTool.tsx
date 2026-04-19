import { mkdirSync, statSync } from 'fs'
import { Box, Text } from 'ink'
import { dirname, isAbsolute, relative, resolve, sep } from 'path'
import * as React from 'react'
import { z } from 'zod'
import { FileEditToolUpdatedMessage } from '@components/FileEditToolUpdatedMessage'
import { StructuredDiff } from '@components/StructuredDiff'
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
import { NotebookEditTool } from '@tools/NotebookEditTool/NotebookEditTool'
function applyContentEdit(
  content: string,
  oldString: string,
  newString: string,
  replaceAll: boolean = false,
): { newContent: string; occurrences: number } {
  if (replaceAll) {
    const regex = new RegExp(
      oldString.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
      'g',
    )
    const matches = content.match(regex)
    const occurrences = matches ? matches.length : 0
    const newContent = content.replace(regex, newString)
    return { newContent, occurrences }
  } else {
    if (content.includes(oldString)) {
      const newContent = content.replace(oldString, newString)
      return { newContent, occurrences: 1 }
    } else {
      throw new Error(`String not found: ${oldString.substring(0, 50)}...`)
    }
  }
}
import { hasWritePermission } from '@utils/permissions/filesystem'
import { PROJECT_FILE } from '@constants/product'
import { DESCRIPTION, PROMPT } from './prompt'
import { emitReminderEvent } from '@services/systemReminder'
import { recordFileEdit } from '@services/fileFreshness'
import { getPatch } from '@utils/text/diff'

const EditSchema = z.object({
  old_string: z.string().describe('The text to replace'),
  new_string: z.string().describe('The text to replace it with'),
  replace_all: z
    .boolean()
    .optional()
    .default(false)
    .describe('Replace all occurences of old_string (default false)'),
})

const inputSchema = z.strictObject({
  file_path: z.string().describe('The absolute path to the file to modify'),
  edits: z
    .array(EditSchema)
    .min(1)
    .describe('Array of edit operations to perform sequentially on the file'),
})

export type In = typeof inputSchema

const N_LINES_SNIPPET = 4

export const MultiEditTool = {
  name: 'MultiEdit',
  async description() {
    return 'A tool for making multiple edits to a single file atomically'
  },
  async prompt() {
    return PROMPT
  },
  inputSchema,
  userFacingName() {
    return 'Multi-Edit'
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
  needsPermissions(input?: z.infer<typeof inputSchema>) {
    if (!input) return true
    return !hasWritePermission(input.file_path)
  },
  renderResultForAssistant(content) {
    return content
  },
  renderToolUseMessage(input, { verbose }) {
    const { file_path, edits } = input
    const workingDir = getCwd()
    const relativePath = isAbsolute(file_path)
      ? relative(workingDir, file_path)
      : file_path

    if (verbose) {
      const editSummary = edits
        .map(
          (edit, index) =>
            `${index + 1}. Replace "${edit.old_string.substring(0, 50)}${edit.old_string.length > 50 ? '...' : ''}" with "${edit.new_string.substring(0, 50)}${edit.new_string.length > 50 ? '...' : ''}"`,
        )
        .join('\n')
      return `Multiple edits to ${relativePath}:\n${editSummary}`
    }

    return `Making ${edits.length} edits to ${relativePath}`
  },
  renderToolUseRejectedMessage() {
    return (
      <Box>
        <Text color={getTheme().error}>⚠ Edit request rejected</Text>
      </Box>
    )
  },
  renderToolResultMessage(output) {
    if (typeof output === 'string') {
      const isError = output.includes('Error:')
      return (
        <Box flexDirection="column">
          <Text color={isError ? getTheme().error : getTheme().success}>
            {output}
          </Text>
        </Box>
      )
    }

    return (
      <FileEditToolUpdatedMessage
        filePath={output.filePath}
        structuredPatch={output.structuredPatch}
        verbose={false}
      />
    )
  },
  async validateInput(
    { file_path, edits }: z.infer<typeof inputSchema>,
    context?: { readFileTimestamps?: Record<string, number> },
  ): Promise<ValidationResult> {
    const workingDir = getCwd()
    const normalizedPath = isAbsolute(file_path)
      ? resolve(file_path)
      : resolve(workingDir, file_path)

    if (normalizedPath.endsWith('.ipynb')) {
      return {
        result: false,
        errorCode: 1,
        message: `For Jupyter notebooks (.ipynb files), use the ${NotebookEditTool.name} tool instead.`,
      }
    }

    if (!fileExistsBun(normalizedPath)) {
      const parentDir = dirname(normalizedPath)
      if (!fileExistsBun(parentDir)) {
        return {
          result: false,
          errorCode: 2,
          message: `Parent directory does not exist: ${parentDir}`,
        }
      }

      if (edits.length === 0 || edits[0].old_string !== '') {
        return {
          result: false,
          errorCode: 6,
          message:
            'For new files, the first edit must have an empty old_string to create the file content.',
        }
      }
    } else {
      const readFileTimestamps = context?.readFileTimestamps || {}
      const readTimestamp = readFileTimestamps[normalizedPath]

      if (!readTimestamp) {
        return {
          result: false,
          errorCode: 7,
          message:
            'File has not been read yet. Read it first before editing it.',
          meta: {
            filePath: normalizedPath,
            isFilePathAbsolute: String(isAbsolute(file_path)),
          },
        }
      }

      const stats = statSync(normalizedPath)
      const lastWriteTime = stats.mtimeMs
      if (lastWriteTime > readTimestamp) {
        return {
          result: false,
          errorCode: 8,
          message:
            'File has been modified since read, either by the user or by a linter. Read it again before attempting to edit it.',
          meta: {
            filePath: normalizedPath,
            lastWriteTime,
            readTimestamp,
          },
        }
      }

      const encoding = detectFileEncoding(normalizedPath)
      if (encoding === 'binary') {
        return {
          result: false,
          errorCode: 9,
          message: 'Cannot edit binary files.',
        }
      }

      const currentContent = await readFileBun(normalizedPath)
      if (!currentContent) {
        return {
          result: false,
          errorCode: 11,
          message: 'Could not read file.',
        }
      }
      for (let i = 0; i < edits.length; i++) {
        const edit = edits[i]
        if (
          edit.old_string !== '' &&
          !currentContent.includes(edit.old_string)
        ) {
          return {
            result: false,
            errorCode: 10,
            message: `Edit ${i + 1}: String to replace not found in file: "${edit.old_string.substring(0, 100)}${edit.old_string.length > 100 ? '...' : ''}"`,
            meta: {
              editIndex: i + 1,
              oldString: edit.old_string.substring(0, 200),
            },
          }
        }
      }
    }

    for (let i = 0; i < edits.length; i++) {
      const edit = edits[i]
      if (edit.old_string === edit.new_string) {
        return {
          result: false,
          errorCode: 3,
          message: `Edit ${i + 1}: old_string and new_string cannot be the same`,
        }
      }
    }

    return { result: true }
  },
  async *call({ file_path, edits }, { readFileTimestamps }) {
    const startTime = Date.now()
    const workingDir = getCwd()
    const filePath = isAbsolute(file_path)
      ? resolve(file_path)
      : resolve(workingDir, file_path)

    try {
      let currentContent = ''
      let fileExists = fileExistsBun(filePath)

      if (fileExists) {
        const encoding = detectFileEncoding(filePath)
        if (encoding === 'binary') {
          yield {
            type: 'result',
            data: 'Error: Cannot edit binary files',
            resultForAssistant: 'Error: Cannot edit binary files',
          }
          return
        }
        const content = await readFileBun(filePath)
        if (!content) {
          yield {
            type: 'result',
            data: 'Error: Could not read file',
            resultForAssistant: 'Error: Could not read file',
          }
          return
        }
        currentContent = content
      } else {
        const parentDir = dirname(filePath)
        if (!fileExistsBun(parentDir)) {
          mkdirSync(parentDir, { recursive: true })
        }
      }

      let modifiedContent = currentContent
      const appliedEdits = []

      for (let i = 0; i < edits.length; i++) {
        const edit = edits[i]
        const { old_string, new_string, replace_all } = edit

        try {
          const result = applyContentEdit(
            modifiedContent,
            old_string,
            new_string,
            replace_all,
          )
          modifiedContent = result.newContent
          appliedEdits.push({
            editIndex: i + 1,
            success: true,
            old_string: old_string.substring(0, 100),
            new_string: new_string.substring(0, 100),
            occurrences: result.occurrences,
          })
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Unknown error'
          yield {
            type: 'result',
            data: `Error in edit ${i + 1}: ${errorMessage}`,
            resultForAssistant: `Error in edit ${i + 1}: ${errorMessage}`,
          }
          return
        }
      }

      const lineEndings = fileExists ? detectLineEndings(currentContent) : 'LF'
      const encoding = fileExists ? detectFileEncoding(filePath) : 'utf8'
      writeTextContent(filePath, modifiedContent, encoding, lineEndings)

      recordFileEdit(filePath, modifiedContent)

      readFileTimestamps[filePath] = Date.now()

      emitReminderEvent('file:edited', {
        filePath,
        edits: edits.map(e => ({
          oldString: e.old_string,
          newString: e.new_string,
        })),
        originalContent: currentContent,
        newContent: modifiedContent,
        timestamp: Date.now(),
        operation: fileExists ? 'update' : 'create',
      })

      const relativePath = relative(workingDir, filePath)
      const summary = `Successfully applied ${edits.length} edits to ${relativePath}`

      const structuredPatch = getPatch({
        filePath: file_path,
        fileContents: currentContent,
        oldStr: currentContent,
        newStr: modifiedContent,
      })

      const resultData = {
        filePath: file_path,
        wasNewFile: !fileExists,
        editsApplied: appliedEdits,
        totalEdits: edits.length,
        summary,
        structuredPatch,
      }


      yield {
        type: 'result',
        data: resultData,
        resultForAssistant: summary,
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred'
      const errorResult = `Error applying multi-edit: ${errorMessage}`

      logError(error)

      yield {
        type: 'result',
        data: errorResult,
        resultForAssistant: errorResult,
      }
    }
  },
} satisfies Tool<typeof inputSchema, any>
