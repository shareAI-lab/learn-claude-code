export function normalizeLineEndings(text: string): string {
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
}

export function countLineBreaks(text: string): number {
  return (text.match(/\r\n|\r|\n/g) || []).length
}

export const SPECIAL_PASTE_CHAR_THRESHOLD = 800

export function getSpecialPasteNewlineThreshold(terminalRows: number): number {
  return Math.min(terminalRows - 10, 2)
}

export type SpecialPasteOptions = {
  terminalRows?: number
  charThreshold?: number
}

export function shouldTreatAsSpecialPaste(
  text: string,
  options: SpecialPasteOptions = {},
): boolean {
  const normalized = normalizeLineEndings(text)

  const terminalRows = options.terminalRows ?? process.stdout?.rows ?? 24
  const charThreshold = options.charThreshold ?? SPECIAL_PASTE_CHAR_THRESHOLD
  const newlineThreshold = getSpecialPasteNewlineThreshold(terminalRows)

  const newlineCount = countLineBreaks(normalized)
  return normalized.length > charThreshold || newlineCount > newlineThreshold
}

export function shouldAggregatePasteChunk(
  input: string,
  hasPendingTimeout: boolean,
): boolean {
  if (hasPendingTimeout) return true
  if (input.length > SPECIAL_PASTE_CHAR_THRESHOLD) return true

  if (input === '\x1b\r' || input === '\x1b\n') return false

  if (input.length > 1 && (input.includes('\n') || input.includes('\r')))
    return true

  return false
}
