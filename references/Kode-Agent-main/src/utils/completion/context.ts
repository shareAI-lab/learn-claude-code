import type { CompletionContext } from './types'

export function getCompletionContext(args: {
  input: string
  cursorOffset: number
  disableSlashCommands?: boolean
}): CompletionContext | null {
  const { input, cursorOffset } = args
  const disableSlashCommands = args.disableSlashCommands === true
  if (!input) return null

  let start = cursorOffset

  while (start > 0) {
    const char = input[start - 1]
    if (/\\s/.test(char)) break

    if (char === '@' && start < cursorOffset) {
      start--
      break
    }

    if (char === '/') {
      const collectedSoFar = input.slice(start, cursorOffset)

      if (collectedSoFar.includes('/') || collectedSoFar.includes('.')) {
        start--
        continue
      }

      if (start > 1) {
        const prevChar = input[start - 2]
        if (prevChar === '.' || prevChar === '~') {
          start--
          continue
        }
      }

      if (start === 1 || (start > 1 && /\\s/.test(input[start - 2]))) {
        start--
        break
      }

      start--
      continue
    }

    if (char === '.' && start > 0) {
      const nextChar = start < input.length ? input[start] : ''
      if (nextChar === '/' || nextChar === '.') {
        start--
        continue
      }
    }

    start--
  }

  const word = input.slice(start, cursorOffset)
  if (!word) return null

  if (word.startsWith('/')) {
    const beforeWord = input.slice(0, start).trim()
    const isCommand =
      beforeWord === '' && !word.includes('/', 1) && !disableSlashCommands
    return {
      type: isCommand ? 'command' : 'file',
      prefix: isCommand ? word.slice(1) : word,
      startPos: start,
      endPos: cursorOffset,
    }
  }

  if (word.startsWith('@')) {
    const content = word.slice(1)
    if (word.includes('@', 1)) return null
    return {
      type: 'agent',
      prefix: content,
      startPos: start,
      endPos: cursorOffset,
    }
  }

  return { type: 'file', prefix: word, startPos: start, endPos: cursorOffset }
}
