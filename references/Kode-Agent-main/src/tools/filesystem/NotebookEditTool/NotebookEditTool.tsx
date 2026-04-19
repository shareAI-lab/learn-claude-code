import { Box, Text } from 'ink'
import { randomUUID } from 'crypto'
import { extname, isAbsolute, relative, resolve } from 'path'
import * as React from 'react'
import { z } from 'zod'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { HighlightedCode } from '@components/HighlightedCode'
import type { Tool } from '@tool'
import { NotebookCellType, NotebookContent } from '@kode-types/notebook'
import {
  detectFileEncoding,
  detectLineEndings,
  writeTextContent,
} from '@utils/fs/file'
import { readFileBun, fileExistsBun } from '@utils/bun/file'
import { safeParseJSON } from '@utils/text/json'
import { getCwd } from '@utils/state'
import { DESCRIPTION, PROMPT } from './prompt'
import { hasWritePermission } from '@utils/permissions/filesystem'
import { emitReminderEvent } from '@services/systemReminder'
import { recordFileEdit } from '@services/fileFreshness'

function getDerivedCellId(index: number): string {
  return `cell-${index}`
}

function getCellId(
  cell: NotebookContent['cells'][number],
  index: number,
): string {
  return cell.id ?? getDerivedCellId(index)
}

function parseCellIdAsIndex(cellId: string): number | undefined {
  const trimmed = cellId.trim()
  if (/^\d+$/.test(trimmed)) return Number(trimmed)
  const match = trimmed.match(/^cell-(\d+)$/)
  if (match) return Number(match[1])
  return undefined
}

function findCellIndex(
  notebook: NotebookContent,
  cellId: string,
): number | null {
  const numericIndex = parseCellIdAsIndex(cellId)
  if (numericIndex !== undefined) return numericIndex

  const index = notebook.cells.findIndex(
    (cell, idx) => getCellId(cell, idx) === cellId,
  )
  return index >= 0 ? index : null
}

const inputSchema = z.strictObject({
  notebook_path: z
    .string()
    .describe(
      'The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)',
    ),
  cell_id: z
    .string()
    .optional()
    .describe(
      'The ID of the cell to edit. When inserting a new cell, the new cell will be inserted after the cell with this ID, or at the beginning if not specified.',
    ),
  new_source: z.string().describe('The new source for the cell'),
  cell_type: z
    .enum(['code', 'markdown'])
    .optional()
    .describe(
      'The type of the cell (code or markdown). If not specified, it defaults to the current cell type. If using edit_mode=insert, this is required.',
    ),
  edit_mode: z
    .enum(['replace', 'insert', 'delete'])
    .optional()
    .describe(
      'The type of edit to make (replace, insert, delete). Defaults to replace.',
    ),
})

export const NotebookEditTool = {
  name: 'NotebookEdit',
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return PROMPT
  },
  inputSchema,
  userFacingName() {
    return 'Edit Notebook'
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
  needsPermissions({ notebook_path }) {
    return !hasWritePermission(notebook_path)
  },
  renderResultForAssistant({ cell_id, edit_mode, new_source, error }) {
    if (error) {
      return error
    }
    switch (edit_mode) {
      case 'replace':
        return `Updated cell ${cell_id} with ${new_source}`
      case 'insert':
        return `Inserted cell after ${cell_id ?? 'beginning'} with ${new_source}`
      case 'delete':
        return `Deleted cell ${cell_id}`
    }
  },
  renderToolUseMessage(input, { verbose }) {
    const cellRef = input.cell_id ?? '(none)'
    return `notebook_path: ${verbose ? input.notebook_path : relative(getCwd(), input.notebook_path)}, cell_id: ${cellRef}, content: ${input.new_source.slice(0, 30)}…, cell_type: ${input.cell_type}, edit_mode: ${input.edit_mode ?? 'replace'}`
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage({ cell_id, new_source, language, error }) {
    if (error) {
      return (
        <Box flexDirection="column">
          <Text color="red">{error}</Text>
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        <Text>Updated cell {cell_id}:</Text>
        <Box marginLeft={2}>
          <HighlightedCode code={new_source} language={language} />
        </Box>
      </Box>
    )
  },
  async validateInput({
    notebook_path,
    cell_id,
    cell_type,
    edit_mode = 'replace',
  }) {
    const fullPath = isAbsolute(notebook_path)
      ? notebook_path
      : resolve(getCwd(), notebook_path)

    if (!fileExistsBun(fullPath)) {
      return {
        result: false,
        message: 'Notebook file does not exist.',
      }
    }

    if (extname(fullPath) !== '.ipynb') {
      return {
        result: false,
        message:
          'File must be a Jupyter notebook (.ipynb file). For editing other file types, use the FileEdit tool.',
      }
    }

    if (edit_mode === 'insert' && !cell_type) {
      return {
        result: false,
        message: 'Cell type is required when using edit_mode=insert.',
      }
    }

    const content = await readFileBun(fullPath)
    if (!content) {
      return {
        result: false,
        message: 'Could not read notebook file.',
      }
    }
    const notebook = safeParseJSON(content) as NotebookContent | null
    if (!notebook) {
      return {
        result: false,
        message: 'Notebook is not valid JSON.',
      }
    }

    if ((edit_mode === 'replace' || edit_mode === 'delete') && !cell_id) {
      return {
        result: false,
        message: 'cell_id is required for replace/delete edits.',
      }
    }

    if (cell_id) {
      const index = findCellIndex(notebook, cell_id)
      if (index === null || index < 0 || index >= notebook.cells.length) {
        return {
          result: false,
          message: `Cell ID is out of bounds or not found. Notebook has ${notebook.cells.length} cells.`,
        }
      }
    }

    return { result: true }
  },
  async *call({ notebook_path, cell_id, new_source, cell_type, edit_mode }) {
    const fullPath = isAbsolute(notebook_path)
      ? notebook_path
      : resolve(getCwd(), notebook_path)
    const mode = edit_mode ?? 'replace'
    let editedCellId: string | undefined = cell_id

    try {
      const enc = detectFileEncoding(fullPath)
      const content = await readFileBun(fullPath)
      if (!content) {
        throw new Error('Could not read notebook file')
      }
      const notebook = JSON.parse(content) as NotebookContent
      const language = notebook.metadata.language_info?.name ?? 'python'

      const resolveIndexOrThrow = (): number => {
        if (!cell_id) {
          throw new Error('cell_id is required for this edit')
        }
        const idx = findCellIndex(notebook, cell_id)
        if (idx === null || idx < 0 || idx >= notebook.cells.length) {
          throw new Error(`Cell not found: ${cell_id}`)
        }
        return idx
      }

      if (mode === 'delete') {
        const idx = resolveIndexOrThrow()
        editedCellId = getCellId(notebook.cells[idx]!, idx)
        notebook.cells.splice(idx, 1)
      } else if (mode === 'insert') {
        if (!cell_type) {
          throw new Error('cell_type is required for insert edits')
        }

        const afterIndex =
          cell_id === undefined ? -1 : findCellIndex(notebook, cell_id)
        if (afterIndex === null) {
          throw new Error(`Cell not found: ${cell_id}`)
        }

        const insertIndex = afterIndex === -1 ? 0 : afterIndex + 1

        const newCell: NotebookContent['cells'][number] = {
          cell_type,
          source: new_source,
          metadata: {},
          ...(cell_type === 'code' ? { outputs: [] } : {}),
        }

        if (notebook.nbformat === 4 && notebook.nbformat_minor >= 5) {
          newCell.id = randomUUID()
        }

        notebook.cells.splice(insertIndex, 0, newCell)
        editedCellId = newCell.id ?? getDerivedCellId(insertIndex)
      } else {
        const idx = resolveIndexOrThrow()
        const targetCell = notebook.cells[idx]!
        targetCell.source = new_source
        targetCell.execution_count = undefined
        targetCell.outputs = []
        if (cell_type && cell_type !== targetCell.cell_type) {
          targetCell.cell_type = cell_type
        }
        editedCellId = getCellId(targetCell, idx)
      }
      const endings = detectLineEndings(fullPath)
      const updatedNotebook = JSON.stringify(notebook, null, 1)
      writeTextContent(fullPath, updatedNotebook, enc, endings!)

      recordFileEdit(fullPath, updatedNotebook)

      emitReminderEvent('file:edited', {
        filePath: fullPath,
        cellId: editedCellId,
        newSource: new_source,
        cellType: cell_type,
        editMode: mode,
        timestamp: Date.now(),
        operation: 'notebook_edit',
      })
      const data = {
        cell_id: editedCellId,
        new_source,
        cell_type: cell_type ?? 'code',
        language,
        edit_mode: mode,
        error: '',
      }
      yield {
        type: 'result',
        data,
        resultForAssistant: this.renderResultForAssistant(data),
      }
    } catch (error) {
      if (error instanceof Error) {
        const data = {
          cell_id,
          new_source,
          cell_type: cell_type ?? 'code',
          language: 'python',
          edit_mode: mode,
          error: error.message,
        }
        yield {
          type: 'result',
          data,
          resultForAssistant: this.renderResultForAssistant(data),
        }
        return
      }
      const data = {
        cell_id,
        new_source,
        cell_type: cell_type ?? 'code',
        language: 'python',
        edit_mode: mode,
        error: 'Unknown error occurred while editing notebook',
      }
      yield {
        type: 'result',
        data,
        resultForAssistant: this.renderResultForAssistant(data),
      }
    }
  },
} satisfies Tool<
  typeof inputSchema,
  {
    cell_id?: string
    new_source: string
    cell_type: NotebookCellType
    language: string
    edit_mode: string
    error?: string
  }
>
