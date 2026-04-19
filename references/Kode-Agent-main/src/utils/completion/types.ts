export interface UnifiedSuggestion {
  value: string
  displayValue: string
  type: 'command' | 'agent' | 'file' | 'ask'
  icon?: string
  score: number
  metadata?: any
  isSmartMatch?: boolean
  originalContext?: 'mention' | 'file' | 'command'
}

export interface CompletionContext {
  type: 'command' | 'agent' | 'file' | null
  prefix: string
  startPos: number
  endPos: number
}
