type PartialJsonToken =
  | { type: 'brace'; value: '{' | '}' }
  | { type: 'paren'; value: '[' | ']' }
  | { type: 'separator'; value: ':' }
  | { type: 'delimiter'; value: ',' }
  | { type: 'string'; value: string }
  | { type: 'number'; value: string }
  | { type: 'name'; value: 'true' | 'false' | 'null' }

function tokenizePartialJson(input: string): PartialJsonToken[] {
  let index = 0
  const tokens: PartialJsonToken[] = []

  while (index < input.length) {
    let ch = input[index]

    if (ch === '\\') {
      index++
      continue
    }

    if (ch === '{') {
      tokens.push({ type: 'brace', value: '{' })
      index++
      continue
    }
    if (ch === '}') {
      tokens.push({ type: 'brace', value: '}' })
      index++
      continue
    }
    if (ch === '[') {
      tokens.push({ type: 'paren', value: '[' })
      index++
      continue
    }
    if (ch === ']') {
      tokens.push({ type: 'paren', value: ']' })
      index++
      continue
    }
    if (ch === ':') {
      tokens.push({ type: 'separator', value: ':' })
      index++
      continue
    }
    if (ch === ',') {
      tokens.push({ type: 'delimiter', value: ',' })
      index++
      continue
    }

    if (ch === '"') {
      let value = ''
      let incomplete = false

      ch = input[++index]
      while (ch !== '"') {
        if (index === input.length) {
          incomplete = true
          break
        }
        if (ch === '\\') {
          if (++index === input.length) {
            incomplete = true
            break
          }
          value += ch + input[index]
          ch = input[++index]
        } else {
          value += ch
          ch = input[++index]
        }
      }

      ch = input[++index]
      if (!incomplete) tokens.push({ type: 'string', value })
      continue
    }

    if (ch && /\s/.test(ch)) {
      index++
      continue
    }

    const digit = /[0-9]/
    if ((ch && digit.test(ch)) || ch === '-' || ch === '.') {
      let value = ''
      if (ch === '-') {
        value += ch
        ch = input[++index]
      }
      while ((ch && digit.test(ch)) || ch === '.') {
        value += ch
        ch = input[++index]
      }
      tokens.push({ type: 'number', value })
      continue
    }

    const alpha = /[a-z]/i
    if (ch && alpha.test(ch)) {
      let value = ''
      while (ch && alpha.test(ch)) {
        if (index === input.length) break
        value += ch
        ch = input[++index]
      }

      if (value === 'true' || value === 'false' || value === 'null') {
        tokens.push({ type: 'name', value })
      } else {
        index++
      }
      continue
    }

    index++
  }

  return tokens
}

function trimTrailingIncompleteTokens(
  tokens: PartialJsonToken[],
): PartialJsonToken[] {
  if (tokens.length === 0) return tokens
  const last = tokens[tokens.length - 1]!

  if (last.type === 'separator') {
    return trimTrailingIncompleteTokens(tokens.slice(0, -1))
  }

  if (last.type === 'number') {
    const lastChar = last.value[last.value.length - 1]
    if (lastChar === '.' || lastChar === '-') {
      return trimTrailingIncompleteTokens(tokens.slice(0, -1))
    }
  }

  if (last.type === 'string' || last.type === 'number') {
    const previous = tokens[tokens.length - 2]
    if (previous?.type === 'delimiter') {
      return trimTrailingIncompleteTokens(tokens.slice(0, -1))
    }
    if (previous?.type === 'brace' && previous.value === '{') {
      return trimTrailingIncompleteTokens(tokens.slice(0, -1))
    }
  }

  if (last.type === 'delimiter') {
    return trimTrailingIncompleteTokens(tokens.slice(0, -1))
  }

  return tokens
}

function closeOpenBrackets(tokens: PartialJsonToken[]): PartialJsonToken[] {
  const missingClosers: Array<'}' | ']'> = []

  for (const token of tokens) {
    if (token.type === 'brace') {
      if (token.value === '{') missingClosers.push('}')
      else missingClosers.splice(missingClosers.lastIndexOf('}'), 1)
      continue
    }

    if (token.type === 'paren') {
      if (token.value === '[') missingClosers.push(']')
      else missingClosers.splice(missingClosers.lastIndexOf(']'), 1)
    }
  }

  if (missingClosers.length > 0) {
    missingClosers.reverse()
    for (const closer of missingClosers) {
      if (closer === '}') tokens.push({ type: 'brace', value: '}' })
      else tokens.push({ type: 'paren', value: ']' })
    }
  }

  return tokens
}

function tokensToJson(tokens: PartialJsonToken[]): string {
  let out = ''
  for (const token of tokens) {
    if (token.type === 'string') out += `"${token.value}"`
    else out += token.value
  }
  return out
}

export function parseToolUsePartialJson(input: string): unknown {
  const tokens = tokenizePartialJson(input)
  const trimmed = trimTrailingIncompleteTokens(tokens)
  const completed = closeOpenBrackets(trimmed)
  return JSON.parse(tokensToJson(completed))
}

export function parseToolUsePartialJsonOrThrow(input: string): unknown {
  try {
    return parseToolUsePartialJson(input)
  } catch (error) {
    throw new Error(
      `Unable to parse tool parameter JSON from model. Please retry your request or adjust your prompt. Error: ${String(error)}. JSON: ${input}`,
    )
  }
}
