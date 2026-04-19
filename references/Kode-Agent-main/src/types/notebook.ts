
export type NotebookCellType = 'code' | 'markdown'

export interface NotebookOutputImage {
  image_data: string
  media_type: 'image/png' | 'image/jpeg'
}

export interface NotebookCellSourceOutput {
  output_type: 'stream' | 'execute_result' | 'display_data' | 'error'
  text?: string
  image?: NotebookOutputImage
}

export interface NotebookCellSource {
  cell: number
  cellType: NotebookCellType
  source: string
  language: string
  execution_count?: number | null
  outputs?: NotebookCellSourceOutput[]
}

export interface NotebookCellOutput {
  output_type: 'stream' | 'execute_result' | 'display_data' | 'error'
  name?: string
  text?: string | string[]
  data?: Record<string, unknown>
  execution_count?: number | null
  metadata?: Record<string, unknown>
  ename?: string
  evalue?: string
  traceback?: string[]
}

export interface NotebookCell {
  cell_type: NotebookCellType
  source: string | string[]
  metadata: Record<string, unknown>
  execution_count?: number | null
  outputs?: NotebookCellOutput[]
  id?: string
}

export interface NotebookContent {
  cells: NotebookCell[]
  metadata: {
    kernelspec?: {
      display_name?: string
      language?: string
      name?: string
    }
    language_info?: {
      name?: string
      version?: string
      mimetype?: string
      file_extension?: string
    }
    [key: string]: unknown
  }
  nbformat: number
  nbformat_minor: number
}
