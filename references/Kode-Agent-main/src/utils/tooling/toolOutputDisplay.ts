function isTruthyEnv(value: string | undefined): boolean {
  if (!value) return false
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function isPackagedRuntime(): boolean {
  if (isTruthyEnv(process.env.KODE_PACKAGED)) return true

  try {
    const exec = (process.execPath || '').split(/[\\/]/).pop()?.toLowerCase()
    if (!exec) return false
    if (exec === 'bun' || exec === 'bun.exe') return false
    if (exec === 'node' || exec === 'node.exe') return false
    return true
  } catch {
    return false
  }
}

export type TruncateResult = {
  text: string
  truncated: boolean
  omittedLines: number
  omittedChars: number
}

export function truncateTextForDisplay(
  text: string,
  options?: { maxLines?: number; maxChars?: number },
): TruncateResult {
  const maxLines = options?.maxLines ?? 120
  const maxChars = options?.maxChars ?? 12_000

  const normalized = String(text ?? '')
  const lines = normalized.split(/\r?\n/)

  let workingLines = lines
  let omittedLines = 0
  if (maxLines > 0 && lines.length > maxLines) {
    workingLines = lines.slice(0, maxLines)
    omittedLines = lines.length - maxLines
  }

  let workingText = workingLines.join('\n')
  let omittedChars = 0
  if (maxChars > 0 && workingText.length > maxChars) {
    omittedChars = workingText.length - maxChars
    workingText = workingText.slice(0, maxChars)
  }

  const truncated = omittedLines > 0 || omittedChars > 0
  if (!truncated) {
    return {
      text: workingText,
      truncated: false,
      omittedLines: 0,
      omittedChars: 0,
    }
  }

  const suffixParts: string[] = []
  if (omittedLines > 0) {
    suffixParts.push(`${omittedLines} lines`)
  }
  if (omittedChars > 0) {
    suffixParts.push(`${omittedChars} chars`)
  }

  const suffix = `\n\n... [truncated ${suffixParts.join(' · ')}] ...`
  return {
    text: workingText + suffix,
    truncated: true,
    omittedLines,
    omittedChars,
  }
}

export function maybeTruncateVerboseToolOutput(
  text: string,
  options?: { maxLines?: number; maxChars?: number },
): { text: string; truncated: boolean } {
  const maxLinesEnv = Number(process.env.KODE_TOOL_OUTPUT_MAX_LINES ?? '')
  const maxCharsEnv = Number(process.env.KODE_TOOL_OUTPUT_MAX_CHARS ?? '')
  const envOverrides = {
    maxLines:
      Number.isFinite(maxLinesEnv) && maxLinesEnv > 0 ? maxLinesEnv : undefined,
    maxChars:
      Number.isFinite(maxCharsEnv) && maxCharsEnv > 0 ? maxCharsEnv : undefined,
  }

  const effective = {
    maxLines: envOverrides.maxLines ?? options?.maxLines,
    maxChars: envOverrides.maxChars ?? options?.maxChars,
  }

  const fullAllowed = isTruthyEnv(process.env.KODE_TOOL_OUTPUT_FULL)
  if (!isPackagedRuntime() || fullAllowed) {
    return { text: String(text ?? ''), truncated: false }
  }

  const result = truncateTextForDisplay(String(text ?? ''), effective)
  return { text: result.text, truncated: result.truncated }
}
