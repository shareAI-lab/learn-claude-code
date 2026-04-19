import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import type { Tool, ToolUseContext } from '@tool'
import { getAbsolutePath } from '@utils/fs/file'
import { hasReadPermission } from '@utils/permissions/filesystem'
import { getCwd } from '@utils/state'
import { existsSync, readFileSync, statSync } from 'fs'
import { Box, Text } from 'ink'
import { createRequire } from 'node:module'
import { extname, join, relative } from 'path'
import React from 'react'
import { pathToFileURL } from 'url'
import { z } from 'zod'
import { DESCRIPTION, PROMPT, TOOL_NAME_FOR_PROMPT } from './prompt'
import { maybeTruncateVerboseToolOutput } from '@utils/tooling/toolOutputDisplay'

type TypeScriptModule = typeof import('typescript')

type Operation =
  | 'goToDefinition'
  | 'findReferences'
  | 'hover'
  | 'documentSymbol'
  | 'workspaceSymbol'
  | 'goToImplementation'
  | 'prepareCallHierarchy'
  | 'incomingCalls'
  | 'outgoingCalls'

const inputSchema = z.strictObject({
  operation: z
    .enum([
      'goToDefinition',
      'findReferences',
      'hover',
      'documentSymbol',
      'workspaceSymbol',
      'goToImplementation',
      'prepareCallHierarchy',
      'incomingCalls',
      'outgoingCalls',
    ])
    .describe('The LSP operation to perform'),
  filePath: z.string().describe('The absolute or relative path to the file'),
  line: z
    .number()
    .int()
    .positive()
    .describe('The line number (1-based, as shown in editors)'),
  character: z
    .number()
    .int()
    .positive()
    .describe('The character offset (1-based, as shown in editors)'),
})

const outputSchema = z.object({
  operation: z
    .enum([
      'goToDefinition',
      'findReferences',
      'hover',
      'documentSymbol',
      'workspaceSymbol',
      'goToImplementation',
      'prepareCallHierarchy',
      'incomingCalls',
      'outgoingCalls',
    ])
    .describe('The LSP operation that was performed'),
  result: z.string().describe('The formatted result of the LSP operation'),
  filePath: z.string().describe('The file path the operation was performed on'),
  resultCount: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe('Number of results (definitions, references, symbols)'),
  fileCount: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe('Number of files containing results'),
})

type Input = z.infer<typeof inputSchema>
type Output = z.infer<typeof outputSchema>

const OPERATION_LABELS: Record<
  Operation,
  { singular: string; plural: string; special?: string }
> = {
  goToDefinition: { singular: 'definition', plural: 'definitions' },
  findReferences: { singular: 'reference', plural: 'references' },
  documentSymbol: { singular: 'symbol', plural: 'symbols' },
  workspaceSymbol: { singular: 'symbol', plural: 'symbols' },
  hover: { singular: 'hover info', plural: 'hover info', special: 'available' },
  goToImplementation: { singular: 'implementation', plural: 'implementations' },
  prepareCallHierarchy: { singular: 'call item', plural: 'call items' },
  incomingCalls: { singular: 'caller', plural: 'callers' },
  outgoingCalls: { singular: 'callee', plural: 'callees' },
}

function extractSymbolAtPosition(
  lines: string[],
  zeroBasedLine: number,
  zeroBasedCharacter: number,
): string | null {
  try {
    if (zeroBasedLine < 0 || zeroBasedLine >= lines.length) return null
    const line = lines[zeroBasedLine]
    if (zeroBasedCharacter < 0 || zeroBasedCharacter >= line.length) return null
    const tokenRe = /[\w$'!]+|[+\-*/%&|^~<>=]+/g
    let match: RegExpExecArray | null
    while ((match = tokenRe.exec(line)) !== null) {
      const start = match.index
      const end = start + match[0].length
      if (zeroBasedCharacter >= start && zeroBasedCharacter < end) {
        const token = match[0]
        return token.length > 30 ? `${token.slice(0, 27)}...` : token
      }
    }
    return null
  } catch {
    return null
  }
}

function toProjectRelativeIfPossible(filePath: string): string {
  const cwd = getCwd()
  try {
    const rel = relative(cwd, filePath)
    if (!rel || rel === '') return filePath
    if (rel.startsWith('..')) return filePath
    return rel
  } catch {
    return filePath
  }
}

function formatLocation(
  fileName: string,
  line0: number,
  character0: number,
): string {
  return `${toProjectRelativeIfPossible(fileName)}:${line0 + 1}:${character0 + 1}`
}

function formatGoToDefinitionResult(
  locations: Array<{
    fileName: string
    line0: number
    character0: number
  }> | null,
): { formatted: string; resultCount: number; fileCount: number } {
  if (!locations || locations.length === 0) {
    return {
      formatted:
        'No definition found. This may occur if the cursor is not on a symbol, or if the definition is in an external library not indexed by the LSP server.',
      resultCount: 0,
      fileCount: 0,
    }
  }
  const fileCount = new Set(locations.map(l => l.fileName)).size
  if (locations.length === 1) {
    const loc = locations[0]
    return {
      formatted: `Defined in ${formatLocation(loc.fileName, loc.line0, loc.character0)}`,
      resultCount: 1,
      fileCount,
    }
  }
  return {
    formatted: `Found ${locations.length} definitions:\n${locations
      .map(
        loc => `  ${formatLocation(loc.fileName, loc.line0, loc.character0)}`,
      )
      .join('\n')}`,
    resultCount: locations.length,
    fileCount,
  }
}

function groupLocationsByFile<T extends { fileName: string }>(
  items: T[],
): Map<string, T[]> {
  const grouped = new Map<string, T[]>()
  for (const item of items) {
    const key = toProjectRelativeIfPossible(item.fileName)
    const existing = grouped.get(key)
    if (existing) existing.push(item)
    else grouped.set(key, [item])
  }
  return grouped
}

function formatFindReferencesResult(
  references: Array<{
    fileName: string
    line0: number
    character0: number
  }> | null,
): { formatted: string; resultCount: number; fileCount: number } {
  if (!references || references.length === 0) {
    return {
      formatted:
        'No references found. This may occur if the symbol has no usages, or if the LSP server has not fully indexed the workspace.',
      resultCount: 0,
      fileCount: 0,
    }
  }
  if (references.length === 1) {
    const ref = references[0]
    return {
      formatted: `Found 1 reference:\n  ${formatLocation(ref.fileName, ref.line0, ref.character0)}`,
      resultCount: 1,
      fileCount: 1,
    }
  }

  const grouped = groupLocationsByFile(references)
  const lines: string[] = [
    `Found ${references.length} references across ${grouped.size} files:`,
  ]
  for (const [file, refs] of grouped) {
    lines.push(`\n${file}:`)
    for (const ref of refs) {
      lines.push(`  Line ${ref.line0 + 1}:${ref.character0 + 1}`)
    }
  }
  return {
    formatted: lines.join('\n'),
    resultCount: references.length,
    fileCount: grouped.size,
  }
}

function formatHoverResult(
  hoverText: string | null,
  line0: number,
  character0: number,
) {
  if (!hoverText || hoverText.trim() === '') {
    return {
      formatted:
        'No hover information available. This may occur if the cursor is not on a symbol, or if the LSP server has not fully indexed the file.',
      resultCount: 0,
      fileCount: 0,
    }
  }
  return {
    formatted: `Hover info at ${line0 + 1}:${character0 + 1}:\n\n${hoverText}`,
    resultCount: 1,
    fileCount: 1,
  }
}

function formatDocumentSymbolsResult(lines: string[], symbolCount: number) {
  if (symbolCount === 0) {
    return {
      formatted:
        'No symbols found in document. This may occur if the file is empty, not supported by the LSP server, or if the server has not fully indexed the file.',
      resultCount: 0,
      fileCount: 0,
    }
  }
  return {
    formatted: ['Document symbols:', ...lines].join('\n'),
    resultCount: symbolCount,
    fileCount: 1,
  }
}

let cachedTypeScript: { cwd: string; module: TypeScriptModule | null } | null =
  null

function tryLoadTypeScriptModule(projectCwd: string): TypeScriptModule | null {
  if (cachedTypeScript?.cwd === projectCwd) return cachedTypeScript.module

  try {
    const requireFromCwd = createRequire(
      pathToFileURL(join(projectCwd, '__kode_lsp__.js')),
    )
    const mod = requireFromCwd('typescript') as TypeScriptModule
    cachedTypeScript = { cwd: projectCwd, module: mod }
    return mod
  } catch {
    cachedTypeScript = { cwd: projectCwd, module: null }
    return null
  }
}

type TsProjectState = {
  ts: TypeScriptModule
  cwd: string
  rootFiles: Set<string>
  compilerOptions: any
  languageService: any
  versions: Map<string, string>
}

const projectCache = new Map<string, TsProjectState>()

function getOrCreateTsProject(projectCwd: string): TsProjectState | null {
  const ts = tryLoadTypeScriptModule(projectCwd)
  if (!ts) return null

  const existing = projectCache.get(projectCwd)
  if (existing) return existing

  let compilerOptions: any = {
    allowJs: true,
    checkJs: false,
    jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ESNext,
    module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeNext,
  }

  let rootFileNames: string[] = []
  try {
    const configPath = ts.findConfigFile(
      projectCwd,
      ts.sys.fileExists,
      'tsconfig.json',
    )
    if (configPath) {
      const configFile = ts.readConfigFile(configPath, ts.sys.readFile)
      if (!configFile.error) {
        const parsed = ts.parseJsonConfigFileContent(
          configFile.config,
          ts.sys,
          projectCwd,
        )
        compilerOptions = { ...compilerOptions, ...parsed.options }
        rootFileNames = parsed.fileNames
      }
    }
  } catch {
  }

  const rootFiles = new Set(rootFileNames)
  const versions = new Map<string, string>()

  const host: any = {
    getCompilationSettings: () => compilerOptions,
    getScriptFileNames: () => Array.from(rootFiles),
    getScriptVersion: (fileName: string) => {
      try {
        const stat = statSync(fileName)
        const version = String(stat.mtimeMs ?? Date.now())
        versions.set(fileName, version)
        return version
      } catch {
        return versions.get(fileName) ?? '0'
      }
    },
    getScriptSnapshot: (fileName: string) => {
      try {
        if (!ts.sys.fileExists(fileName)) return undefined
        const content = ts.sys.readFile(fileName)
        if (content === undefined) return undefined
        const stat = statSync(fileName)
        versions.set(fileName, String(stat.mtimeMs ?? Date.now()))
        return ts.ScriptSnapshot.fromString(content)
      } catch {
        return undefined
      }
    },
    getCurrentDirectory: () => projectCwd,
    getDefaultLibFileName: (options: any) => ts.getDefaultLibFilePath(options),
    fileExists: ts.sys.fileExists,
    readFile: ts.sys.readFile,
    readDirectory: ts.sys.readDirectory,
    directoryExists: ts.sys.directoryExists,
    getDirectories: ts.sys.getDirectories,
    useCaseSensitiveFileNames: () => ts.sys.useCaseSensitiveFileNames,
    getCanonicalFileName: (fileName: string) =>
      ts.sys.useCaseSensitiveFileNames ? fileName : fileName.toLowerCase(),
    getNewLine: () => ts.sys.newLine,
  }

  const languageService = ts.createLanguageService(
    host,
    ts.createDocumentRegistry(),
  )

  const state: TsProjectState = {
    ts,
    cwd: projectCwd,
    rootFiles,
    compilerOptions,
    languageService,
    versions,
  }
  projectCache.set(projectCwd, state)
  return state
}

function isFileTypeSupportedByTypescriptBackend(filePath: string): boolean {
  const ext = extname(filePath).toLowerCase()
  return (
    ext === '.ts' ||
    ext === '.tsx' ||
    ext === '.js' ||
    ext === '.jsx' ||
    ext === '.mts' ||
    ext === '.cts' ||
    ext === '.mjs' ||
    ext === '.cjs'
  )
}

function summarizeToolResult(
  operation: Operation,
  resultCount: number,
  fileCount: number,
) {
  const label = OPERATION_LABELS[operation] ?? {
    singular: 'result',
    plural: 'results',
  }
  const noun = resultCount === 1 ? label.singular : label.plural
  if (operation === 'hover' && resultCount > 0 && label.special) {
    return <Text>Hover info {label.special}</Text>
  }
  return (
    <Text>
      Found <Text bold>{resultCount}</Text> {noun}
      {fileCount > 1 ? (
        <>
          {' '}
          across <Text bold>{fileCount}</Text> files
        </>
      ) : null}
    </Text>
  )
}

export const LspTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return PROMPT
  },
  inputSchema,
  userFacingName() {
    return 'LSP'
  },
  async isEnabled() {
    return tryLoadTypeScriptModule(getCwd()) !== null
  },
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  needsPermissions({ filePath }: Input) {
    const abs = getAbsolutePath(filePath) ?? filePath
    return !hasReadPermission(abs || getCwd())
  },
  async validateInput(input: Input) {
    const parsed = inputSchema.safeParse(input)
    if (!parsed.success) {
      return {
        result: false,
        message: `Invalid input: ${parsed.error.message}`,
        errorCode: 3,
      }
    }

    const absPath = getAbsolutePath(input.filePath) ?? input.filePath
    if (!existsSync(absPath)) {
      return {
        result: false,
        message: `File does not exist: ${input.filePath}`,
        errorCode: 1,
      }
    }
    try {
      if (!statSync(absPath).isFile()) {
        return {
          result: false,
          message: `Path is not a file: ${input.filePath}`,
          errorCode: 2,
        }
      }
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err))
      return {
        result: false,
        message: `Cannot access file: ${input.filePath}. ${e.message}`,
        errorCode: 4,
      }
    }

    return { result: true }
  },
  renderToolUseMessage(input: Input, { verbose }: { verbose: boolean }) {
    const abs = getAbsolutePath(input.filePath) ?? input.filePath
    const filePathForDisplay = verbose ? abs : toProjectRelativeIfPossible(abs)
    const parts: string[] = []

    if (
      (input.operation === 'goToDefinition' ||
        input.operation === 'findReferences' ||
        input.operation === 'hover' ||
        input.operation === 'goToImplementation') &&
      input.filePath &&
      input.line !== undefined &&
      input.character !== undefined
    ) {
      try {
        const content = readFileSync(abs, 'utf8')
        const symbol = extractSymbolAtPosition(
          content.split('\n'),
          input.line - 1,
          input.character - 1,
        )
        if (symbol) {
          parts.push(`operation: "${input.operation}"`)
          parts.push(`symbol: "${symbol}"`)
          parts.push(`in: "${filePathForDisplay}"`)
          return parts.join(', ')
        }
      } catch {
      }

      parts.push(`operation: "${input.operation}"`)
      parts.push(`file: "${filePathForDisplay}"`)
      parts.push(`position: ${input.line}:${input.character}`)
      return parts.join(', ')
    }

    parts.push(`operation: "${input.operation}"`)
    if (input.filePath) parts.push(`file: "${filePathForDisplay}"`)
    return parts.join(', ')
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output, { verbose }: { verbose: boolean }) {
    if (output.resultCount !== undefined && output.fileCount !== undefined) {
      const display = verbose
        ? maybeTruncateVerboseToolOutput(output.result, {
            maxLines: 120,
            maxChars: 20_000,
          })
        : null
      return (
        <Box flexDirection="column">
          <Box flexDirection="row">
            <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
            {summarizeToolResult(
              output.operation,
              output.resultCount,
              output.fileCount,
            )}
          </Box>
          {display ? (
            <Box marginLeft={5}>
              <Text>{display.text}</Text>
            </Box>
          ) : null}
        </Box>
      )
    }

    return (
      <Box justifyContent="space-between" width="100%">
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
          <Text>{output.result}</Text>
        </Box>
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    return output.result
  },
  async *call(input: Input, _context: ToolUseContext) {
    const absPath = getAbsolutePath(input.filePath) ?? input.filePath

    if (!isFileTypeSupportedByTypescriptBackend(absPath)) {
      const ext = extname(absPath)
      const out: Output = {
        operation: input.operation,
        result: `No LSP server available for file type: ${ext}`,
        filePath: input.filePath,
        resultCount: 0,
        fileCount: 0,
      }
      yield { type: 'result', data: out, resultForAssistant: out.result }
      return
    }

    const project = getOrCreateTsProject(getCwd())
    if (!project) {
      const out: Output = {
        operation: input.operation,
        result:
          'LSP server manager not initialized. This may indicate a startup issue.',
        filePath: input.filePath,
        resultCount: 0,
        fileCount: 0,
      }
      yield { type: 'result', data: out, resultForAssistant: out.result }
      return
    }

    project.rootFiles.add(absPath)

    const ts = project.ts
    const service = project.languageService
    const program = service.getProgram?.()
    if (!program) {
      const out: Output = {
        operation: input.operation,
        result: `Error performing ${input.operation}: TypeScript program not available`,
        filePath: input.filePath,
        resultCount: 0,
        fileCount: 0,
      }
      yield { type: 'result', data: out, resultForAssistant: out.result }
      return
    }

    const sourceFile = program.getSourceFile(absPath)
    if (!sourceFile) {
      const out: Output = {
        operation: input.operation,
        result: `Error performing ${input.operation}: File is not part of the TypeScript program`,
        filePath: input.filePath,
        resultCount: 0,
        fileCount: 0,
      }
      yield { type: 'result', data: out, resultForAssistant: out.result }
      return
    }

    const pos = ts.getPositionOfLineAndCharacter(
      sourceFile,
      input.line - 1,
      input.character - 1,
    )

    try {
      let formatted: string
      let resultCount = 0
      let fileCount = 0

      switch (input.operation) {
        case 'goToDefinition': {
          const defs = service.getDefinitionAtPosition?.(absPath, pos) ?? []
          const locations = defs
            .map((d: any) => {
              const defSourceFile = program.getSourceFile(d.fileName)
              if (!defSourceFile) return null
              const lc = ts.getLineAndCharacterOfPosition(
                defSourceFile,
                d.textSpan.start,
              )
              return {
                fileName: d.fileName,
                line0: lc.line,
                character0: lc.character,
              }
            })
            .filter(Boolean) as Array<{
            fileName: string
            line0: number
            character0: number
          }>
          const res = formatGoToDefinitionResult(locations)
          formatted = res.formatted
          resultCount = res.resultCount
          fileCount = res.fileCount
          break
        }
        case 'goToImplementation': {
          const impls =
            service.getImplementationAtPosition?.(absPath, pos) ?? []
          const locations = impls
            .map((d: any) => {
              const defSourceFile = program.getSourceFile(d.fileName)
              if (!defSourceFile) return null
              const lc = ts.getLineAndCharacterOfPosition(
                defSourceFile,
                d.textSpan.start,
              )
              return {
                fileName: d.fileName,
                line0: lc.line,
                character0: lc.character,
              }
            })
            .filter(Boolean) as Array<{
            fileName: string
            line0: number
            character0: number
          }>
          const res = formatGoToDefinitionResult(locations)
          formatted = res.formatted
          resultCount = res.resultCount
          fileCount = res.fileCount
          break
        }
        case 'findReferences': {
          const referencedSymbols = service.findReferences?.(absPath, pos) ?? []
          const refs: Array<{
            fileName: string
            line0: number
            character0: number
          }> = []
          for (const sym of referencedSymbols) {
            for (const ref of sym.references ?? []) {
              const refSource = program.getSourceFile(ref.fileName)
              if (!refSource) continue
              const lc = ts.getLineAndCharacterOfPosition(
                refSource,
                ref.textSpan.start,
              )
              refs.push({
                fileName: ref.fileName,
                line0: lc.line,
                character0: lc.character,
              })
            }
          }
          const res = formatFindReferencesResult(refs)
          formatted = res.formatted
          resultCount = res.resultCount
          fileCount = res.fileCount
          break
        }
        case 'hover': {
          const info = service.getQuickInfoAtPosition?.(absPath, pos)
          let text: string | null = null
          let hoverLine0 = input.line - 1
          let hoverCharacter0 = input.character - 1
          if (info) {
            const parts: string[] = []
            const signature = ts.displayPartsToString(info.displayParts ?? [])
            if (signature) parts.push(signature)
            const doc = ts.displayPartsToString(info.documentation ?? [])
            if (doc) parts.push(doc)
            if (info.tags && info.tags.length > 0) {
              for (const tag of info.tags) {
                const tagText = ts.displayPartsToString(tag.text ?? [])
                parts.push(`@${tag.name}${tagText ? ` ${tagText}` : ''}`)
              }
            }
            text = parts.filter(Boolean).join('\n\n')
            const lc = ts.getLineAndCharacterOfPosition(
              sourceFile,
              info.textSpan.start,
            )
            hoverLine0 = lc.line
            hoverCharacter0 = lc.character
          }
          const res = formatHoverResult(text, hoverLine0, hoverCharacter0)
          formatted = res.formatted
          resultCount = res.resultCount
          fileCount = res.fileCount
          break
        }
        case 'documentSymbol': {
          const tree = service.getNavigationTree?.(absPath)
          const lines: string[] = []
          let count = 0

          const kindLabel = (kind: string) => {
            const m = {
              class: 'Class',
              interface: 'Interface',
              enum: 'Enum',
              function: 'Function',
              method: 'Method',
              property: 'Property',
              var: 'Variable',
              let: 'Variable',
              const: 'Constant',
              module: 'Module',
              alias: 'Alias',
              type: 'Type',
            } as Record<string, string>
            return (
              m[kind] ??
              (kind ? kind[0].toUpperCase() + kind.slice(1) : 'Unknown')
            )
          }

          const walk = (node: any, depth: number) => {
            const children: any[] = node?.childItems ?? []
            for (const child of children) {
              const span = child.spans?.[0]
              if (!span) continue
              const lc = ts.getLineAndCharacterOfPosition(
                sourceFile,
                span.start,
              )
              const indent = '  '.repeat(depth)
              const label = kindLabel(child.kind)
              const detail = child.kindModifiers
                ? ` ${child.kindModifiers}`
                : ''
              lines.push(
                `${indent}${child.text} (${label})${detail} - Line ${lc.line + 1}`,
              )
              count += 1
              if (child.childItems && child.childItems.length > 0) {
                walk(child, depth + 1)
              }
            }
          }
          walk(tree, 0)

          const res = formatDocumentSymbolsResult(lines, count)
          formatted = res.formatted
          resultCount = res.resultCount
          fileCount = res.fileCount
          break
        }
        case 'workspaceSymbol': {
          const items =
            service.getNavigateToItems?.('', 100, undefined, true, true) ?? []
          if (!items || items.length === 0) {
            formatted =
              'No symbols found in workspace. This may occur if the workspace is empty, or if the LSP server has not finished indexing the project.'
            resultCount = 0
            fileCount = 0
            break
          }

          const lines: string[] = [
            `Found ${items.length} symbol${items.length === 1 ? '' : 's'} in workspace:`,
          ]
          const grouped = groupLocationsByFile(
            items.map((it: any) => ({
              fileName: it.fileName,
              item: it,
            })),
          )
          for (const [file, itemsInFile] of grouped) {
            lines.push(`\n${file}:`)
            for (const wrapper of itemsInFile) {
              const it: any = (wrapper as any).item
              const sf = program.getSourceFile(it.fileName)
              if (!sf) continue
              const span = it.textSpan
              const lc = span
                ? ts.getLineAndCharacterOfPosition(sf, span.start)
                : { line: 0, character: 0 }
              const label = it.kind
                ? String(it.kind)[0].toUpperCase() + String(it.kind).slice(1)
                : 'Symbol'
              let line = `  ${it.name} (${label}) - Line ${lc.line + 1}`
              if (it.containerName) line += ` in ${it.containerName}`
              lines.push(line)
            }
          }
          formatted = lines.join('\n')
          resultCount = items.length
          fileCount = grouped.size
          break
        }
        case 'prepareCallHierarchy':
        case 'incomingCalls':
        case 'outgoingCalls': {
          const opLabel = input.operation
          formatted = `Error performing ${opLabel}: Call hierarchy is not supported by the TypeScript backend`
          resultCount = 0
          fileCount = 0
          break
        }
        default: {
          formatted = `Error performing ${input.operation}: Unsupported operation`
          resultCount = 0
          fileCount = 0
        }
      }

      const out: Output = {
        operation: input.operation,
        result: formatted,
        filePath: input.filePath,
        resultCount,
        fileCount,
      }
      yield { type: 'result', data: out, resultForAssistant: out.result }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      const out: Output = {
        operation: input.operation,
        result: `Error performing ${input.operation}: ${message}`,
        filePath: input.filePath,
      }
      yield { type: 'result', data: out, resultForAssistant: out.result }
    }
  },
} satisfies Tool<typeof inputSchema, Output>
