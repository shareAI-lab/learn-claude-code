import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { Cost } from '@components/Cost'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool } from '@tool'
import { getCwd } from '@utils/state'
import { ripGrep } from '@utils/system/ripgrep'
import { DESCRIPTION, TOOL_NAME_FOR_PROMPT } from './prompt'
import { existsSync, statSync } from 'fs'
import { isAbsolute, join, relative, resolve } from 'path'
import { hasReadPermission } from '@utils/permissions/filesystem'

const inputSchema = z.strictObject({
  pattern: z.string().describe('The glob pattern to match files against'),
  path: z
    .string()
    .optional()
    .describe(
      'The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter "undefined" or "null" - simply omit it for the default behavior. Must be a valid directory path if provided.',
    ),
})

type Output = {
  durationMs: number
  numFiles: number
  filenames: string[]
  truncated: boolean
}

const DEFAULT_LIMIT = 100

export const GlobTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description() {
    return DESCRIPTION
  },
  userFacingName() {
    return 'Search'
  },
  inputSchema,
  async isEnabled() {
    return true
  },
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  needsPermissions({ path }) {
    return !hasReadPermission(path || getCwd())
  },
  async prompt() {
    return DESCRIPTION
  },
  async validateInput({ path }) {
    if (!path) return { result: true }
    const absolute = isAbsolute(path) ? path : resolve(getCwd(), path)
    if (!existsSync(absolute)) {
      return {
        result: false,
        message: `Directory does not exist: ${path}`,
        errorCode: 1,
      }
    }
    if (!statSync(absolute).isDirectory()) {
      return {
        result: false,
        message: `Path is not a directory: ${path}`,
        errorCode: 2,
      }
    }
    return { result: true }
  },
  renderToolUseMessage({ pattern, path }, { verbose }) {
    const absolutePath = path
      ? isAbsolute(path)
        ? path
        : resolve(getCwd(), path)
      : undefined
    const relativePath = absolutePath
      ? relative(getCwd(), absolutePath)
      : undefined
    return `pattern: "${pattern}"${relativePath || verbose ? `, path: "${verbose ? absolutePath : relativePath}"` : ''}`
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output) {
    if (typeof output === 'string') {
      output = JSON.parse(output) as Output
    }

    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;Found </Text>
          <Text bold>{output.numFiles} </Text>
          <Text>
            {output.numFiles === 0 || output.numFiles > 1 ? 'files' : 'file'}
          </Text>
        </Box>
        <Cost costUSD={0} durationMs={output.durationMs} debug={false} />
      </Box>
    )
  },
  async *call({ pattern, path }, { abortController }) {
    const start = Date.now()
    const searchPath = path
      ? isAbsolute(path)
        ? path
        : resolve(getCwd(), path)
      : getCwd()

    const raw = await ripGrep(
      [
        '--files',
        '--no-ignore',
        '--hidden',
        '--sort=modified',
        '--glob',
        pattern,
      ],
      searchPath,
      abortController.signal,
    )

    const files = raw.map(p => (isAbsolute(p) ? p : join(searchPath, p)))
    const truncated = files.length > DEFAULT_LIMIT
    const limitedFiles = files.slice(0, DEFAULT_LIMIT)
    const output: Output = {
      filenames: limitedFiles,
      durationMs: Date.now() - start,
      numFiles: limitedFiles.length,
      truncated,
    }
    yield {
      type: 'result',
      resultForAssistant: this.renderResultForAssistant(output),
      data: output,
    }
  },
  renderResultForAssistant(output) {
    let result = output.filenames.join('\n')
    if (output.filenames.length === 0) {
      result = 'No files found'
    }
    else if (output.truncated) {
      result +=
        '\n(Results are truncated. Consider using a more specific path or pattern.)'
    }
    return result
  },
} satisfies Tool<typeof inputSchema, Output>
