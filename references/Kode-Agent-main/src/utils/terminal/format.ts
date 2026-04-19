export function wrapText(text: string, width: number): string[] {
  const lines: string[] = []
  let currentLine = ''

  for (const char of text) {
    if ([...currentLine].length < width) {
      currentLine += char
    } else {
      lines.push(currentLine)
      currentLine = char
    }
  }

  if (currentLine) lines.push(currentLine)
  return lines
}

export function formatDuration(ms: number): string {
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`
  }

  const hours = Math.floor(ms / 3600000)
  const minutes = Math.floor((ms % 3600000) / 60000)
  const seconds = ((ms % 60000) / 1000).toFixed(1)

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}

export function formatNumber(number: number): string {
  return new Intl.NumberFormat('en', {
    notation: 'compact',
    maximumFractionDigits: 1,
  })
    .format(number)
    .toLowerCase()
}
