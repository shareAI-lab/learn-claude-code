import { Box, Text } from 'ink'
import React from 'react'
import { existsSync } from 'fs'
import { stat as statAsync } from 'fs/promises'
import { z } from 'zod'
import { Cost } from '@components/Cost'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool } from '@tool'
import { getCwd } from '@utils/state'
import { getAbsoluteAndRelativePaths, getAbsolutePath } from '@utils/fs/file'
import { ripGrep } from '@utils/system/ripgrep'
import { getBunShellSandboxPlan } from '@utils/sandbox/bunShellSandboxPlan'
import { DESCRIPTION, TOOL_NAME_FOR_PROMPT } from './prompt'
import { hasReadPermission } from '@utils/permissions/filesystem'
import { isAbsolute, relative } from 'path'

const inputSchema = z.strictObject({
  pattern: z
    .string()
    .describe('The regular expression pattern to search for in file contents'),
  path: z
    .string()
    .optional()
    .describe(
      'File or directory to search in (rg PATH). Defaults to current working directory.',
    ),
  glob: z
    .string()
    .optional()
    .describe(
      'Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") - maps to rg --glob',
    ),
  output_mode: z
    .enum(['content', 'files_with_matches', 'count'])
    .optional()
    .describe(
      'Output mode: "content" shows matching lines (supports -A/-B/-C context, -n line numbers, head_limit), "files_with_matches" shows file paths (supports head_limit), "count" shows match counts (supports head_limit). Defaults to "files_with_matches".',
    ),
  '-B': z
    .number()
    .optional()
    .describe(
      'Number of lines to show before each match (rg -B). Requires output_mode: "content", ignored otherwise.',
    ),
  '-A': z
    .number()
    .optional()
    .describe(
      'Number of lines to show after each match (rg -A). Requires output_mode: "content", ignored otherwise.',
    ),
  '-C': z
    .number()
    .optional()
    .describe(
      'Number of lines to show before and after each match (rg -C). Requires output_mode: "content", ignored otherwise.',
    ),
  '-n': z
    .boolean()
    .optional()
    .describe(
      'Show line numbers in output (rg -n). Requires output_mode: "content", ignored otherwise. Defaults to true.',
    ),
  '-i': z.boolean().optional().describe('Case insensitive search (rg -i)'),
  type: z
    .string()
    .optional()
    .describe(
      'File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types.',
    ),
  head_limit: z
    .number()
    .optional()
    .describe(
      'Limit output to first N lines/entries, equivalent to "| head -N". Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count (limits count entries). Defaults based on "cap" experiment value: 0 (unlimited), 20, or 100.',
    ),
  offset: z
    .number()
    .optional()
    .describe(
      'Skip first N lines/entries before applying head_limit, equivalent to "| tail -n +N | head -N". Works across all output modes. Defaults to 0.',
    ),
  multiline: z
    .boolean()
    .optional()
    .describe(
      'Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false.',
    ),
})

const MAX_RESULT_CHARS = 20_000
const EXCLUDED_DIRS = ['.git', '.svn', '.hg', '.bzr']

type Input = typeof inputSchema
type Output = {
  numFiles: number
  filenames: string[]
  mode?: 'content' | 'files_with_matches' | 'count'
  content?: string
  numLines?: number
  numMatches?: number
  appliedLimit?: number
  appliedOffset?: number
  durationMs: number
}

function paginate<T>(
  items: T[],
  limit: number | undefined,
  offset: number,
): T[] {
  if (offset > 0) {
    items = items.slice(offset)
  }
  if (limit === undefined || limit === 0) {
    return items
  }
  return items.slice(0, limit)
}

function truncateToCharBudget(text: string): string {
  if (text.length <= MAX_RESULT_CHARS) return text
  const head = text.slice(0, MAX_RESULT_CHARS)
  const truncatedLines = text.slice(MAX_RESULT_CHARS).split('\n').length
  return `${head}\n\n... [${truncatedLines} lines truncated] ...`
}

function toProjectRelativeIfPossible(p: string): string {
  const projectRoot = getCwd()
  const rel = relative(projectRoot, p)
  if (!rel || rel === '') return p
  if (rel.startsWith('..')) return p
  if (isAbsolute(rel)) return p
  return rel
}

function formatPagination(
  limit: number | undefined,
  offset: number | undefined,
): string {
  if (!limit && !offset) return ''
  return `limit: ${limit}, offset: ${offset ?? 0}`
}

function parseGlobString(glob: string): string[] {
  const parts = glob.split(/\s+/).filter(Boolean)
  const expanded: string[] = []
  for (const part of parts) {
    if (part.includes('{') && part.includes('}')) {
      expanded.push(part)
      continue
    }
    expanded.push(...part.split(',').filter(Boolean))
  }
  return expanded
}

export const GrepTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description() {
    return DESCRIPTION
  },
  userFacingName() {
    return 'Search'
  },
  inputSchema,
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  async isEnabled() {
    return true
  },
  needsPermissions({ path }) {
    return !hasReadPermission(path || getCwd())
  },
  async prompt() {
    return DESCRIPTION
  },
  renderToolUseMessage(input: any, { verbose }: { verbose: boolean }) {
    const {
      pattern,
      path,
      glob,
      type,
      output_mode = 'files_with_matches',
      head_limit,
    } = input
    if (!pattern) return null as any
    const parts = [`pattern: "${pattern}"`]
    if (path) {
      const { absolutePath, relativePath } = getAbsoluteAndRelativePaths(path)
      parts.push(`path: "${verbose ? absolutePath : relativePath}"`)
    }
    if (glob) parts.push(`glob: "${glob}"`)
    if (type) parts.push(`type: "${type}"`)
    if (output_mode !== 'files_with_matches') {
      parts.push(`output_mode: "${output_mode}"`)
    }
    if (head_limit !== undefined) parts.push(`head_limit: ${head_limit}`)
    return parts.join(', ')
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output) {
    if (typeof output === 'string') {
      output = output as unknown as Output
    }

    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;Found </Text>
          <Text bold>
            {output.mode === 'content'
              ? (output.numLines ?? 0)
              : output.mode === 'count'
                ? (output.numMatches ?? 0)
                : output.numFiles}{' '}
          </Text>
          <Text>
            {output.mode === 'content'
              ? (output.numLines ?? 0) === 1
                ? 'line'
                : 'lines'
              : output.mode === 'count'
                ? (output.numMatches ?? 0) === 1
                  ? 'match'
                  : 'matches'
                : output.numFiles === 1
                  ? 'file'
                  : 'files'}
          </Text>
        </Box>
        <Cost costUSD={0} durationMs={output.durationMs} debug={false} />
      </Box>
    )
  },
  renderResultForAssistant(result: Output) {
    const pagination = formatPagination(
      result.appliedLimit,
      result.appliedOffset,
    )

    if (result.mode === 'content') {
      const base = truncateToCharBudget(result.content || 'No matches found')
      return pagination
        ? `${base}\n\n[Showing results with pagination = ${pagination}]`
        : base
    }

    if (result.mode === 'count') {
      const base = truncateToCharBudget(result.content || 'No matches found')
      const numMatches = result.numMatches ?? 0
      const numFiles = result.numFiles ?? 0
      return (
        base +
        `\n\nFound ${numMatches} total ${numMatches === 1 ? 'occurrence' : 'occurrences'} across ${numFiles} ${numFiles === 1 ? 'file' : 'files'}.` +
        (pagination ? ` with pagination = ${pagination}` : '')
      )
    }

    if (result.numFiles === 0) return 'No files found'
    const header = `Found ${result.numFiles} file${result.numFiles === 1 ? '' : 's'}${pagination ? ` ${pagination}` : ''}\n${result.filenames.join('\n')}`
    return truncateToCharBudget(header)
  },
  async validateInput({ path }: any) {
    if (path) {
      const abs = getAbsolutePath(path)
      if (!abs || !existsSync(abs)) {
        return {
          result: false,
          message: `Path does not exist: ${path}`,
          errorCode: 1,
        }
      }
    }
    return { result: true }
  },
  async *call(
    {
      pattern,
      path,
      glob,
      type,
      output_mode = 'files_with_matches',
      '-B': before,
      '-A': after,
      '-C': context,
      '-n': lineNumbers = true,
      '-i': caseInsensitive = false,
      head_limit,
      offset = 0,
      multiline = false,
    }: any,
    toolUseContext: any,
  ) {
    const { abortController } = toolUseContext
    const start = Date.now()
    const absolutePath = getAbsolutePath(path) || getCwd()

    const baseArgs: string[] = ['--hidden']
    for (const dir of EXCLUDED_DIRS) {
      baseArgs.push('--glob', `!${dir}`)
    }
    baseArgs.push('--max-columns', '500')
    if (multiline) {
      baseArgs.push('-U', '--multiline-dotall')
    }
    if (caseInsensitive) {
      baseArgs.push('-i')
    }
    if (type) {
      baseArgs.push('--type', type)
    }

    const appliedLimit = head_limit !== undefined ? head_limit : undefined
    const appliedOffset = offset || 0

    if (glob) {
      for (const g of parseGlobString(glob)) {
        baseArgs.push('--glob', g)
      }
    }

    const args: string[] = [...baseArgs]
    if (output_mode === 'files_with_matches') args.push('-l')
    else if (output_mode === 'count') args.push('-c')

    if (lineNumbers && output_mode === 'content') args.push('-n')

    if (context !== undefined && output_mode === 'content') {
      args.push('-C', String(context))
    } else if (output_mode === 'content') {
      if (before !== undefined) args.push('-B', String(before))
      if (after !== undefined) args.push('-A', String(after))
    }

    if (String(pattern).startsWith('-')) args.push('-e', String(pattern))
    else args.push(String(pattern))

    const sandboxPlan = getBunShellSandboxPlan({
      command: 'rg',
      toolUseContext,
    })
    const lines = await ripGrep(args, absolutePath, abortController.signal, {
      sandbox: sandboxPlan.settings.enabled
        ? sandboxPlan.bunShellSandboxOptions
        : undefined,
    })

    if (output_mode === 'content') {
      const rewritten = lines.map(line => {
        const idx = line.indexOf(':')
        if (idx > 0) {
          const filePart = line.slice(0, idx)
          const rest = line.slice(idx)
          return toProjectRelativeIfPossible(filePart) + rest
        }
        return line
      })

      const window = paginate(rewritten, appliedLimit, appliedOffset)
      const output: Output = {
        mode: 'content',
        numFiles: 0,
        filenames: [],
        content: window.join('\n'),
        numLines: window.length,
        ...(appliedLimit !== undefined ? { appliedLimit } : {}),
        ...(appliedOffset > 0 ? { appliedOffset } : {}),
        durationMs: Date.now() - start,
      }
      yield {
        type: 'result',
        data: output,
        resultForAssistant: this.renderResultForAssistant(output),
      }
      return
    }

    if (output_mode === 'count') {
      const rewritten = lines.map(line => {
        const idx = line.lastIndexOf(':')
        if (idx > 0) {
          const filePart = line.slice(0, idx)
          const rest = line.slice(idx)
          return toProjectRelativeIfPossible(filePart) + rest
        }
        return line
      })

      const window = paginate(rewritten, appliedLimit, appliedOffset)
      let numMatches = 0
      let numFiles = 0
      for (const entry of window) {
        const idx = entry.lastIndexOf(':')
        if (idx > 0) {
          const countStr = entry.slice(idx + 1)
          const count = Number.parseInt(countStr, 10)
          if (!Number.isNaN(count)) {
            numMatches += count
            numFiles += 1
          }
        }
      }

      const output: Output = {
        mode: 'count',
        numFiles,
        filenames: [],
        content: window.join('\n'),
        numMatches,
        ...(appliedLimit !== undefined ? { appliedLimit } : {}),
        ...(appliedOffset > 0 ? { appliedOffset } : {}),
        durationMs: Date.now() - start,
      }
      yield {
        type: 'result',
        data: output,
        resultForAssistant: this.renderResultForAssistant(output),
      }
      return
    }

    const stats = await Promise.all(
      lines.map(async filePath => {
        try {
          return await statAsync(filePath)
        } catch {
          return null
        }
      }),
    )

    const sorted = lines
      .map((filePath, i) => [filePath, stats[i]] as const)
      .sort((a, b) => {
        const diff = (b[1]?.mtimeMs ?? 0) - (a[1]?.mtimeMs ?? 0)
        if (diff !== 0) return diff
        return a[0].localeCompare(b[0])
      })
      .map(([filePath]) => filePath)

    const window = paginate(sorted, appliedLimit, appliedOffset).map(
      toProjectRelativeIfPossible,
    )
    const output: Output = {
      mode: 'files_with_matches',
      filenames: window,
      numFiles: window.length,
      ...(appliedLimit !== undefined ? { appliedLimit } : {}),
      ...(appliedOffset > 0 ? { appliedOffset } : {}),
      durationMs: Date.now() - start,
    }
    yield {
      type: 'result',
      data: output,
      resultForAssistant: this.renderResultForAssistant(output),
    }
  },
} satisfies Tool<Input, Output>
