import { ensureConfigScope } from './discovery'

export type McpCliTransport = 'stdio' | 'sse' | 'http'

export function looksLikeMcpUrl(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) return false

  if (/^(https?|wss?):\/\//i.test(trimmed)) return true
  if (/^localhost(?::\d+)?(\/|$)/i.test(trimmed)) return true
  if (/^\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(\/|$)/.test(trimmed)) return true
  return trimmed.endsWith('/sse') || trimmed.endsWith('/mcp')
}

export function parseMcpHeaders(
  raw: string[] | undefined,
): Record<string, string> | undefined {
  if (!raw || raw.length === 0) return undefined
  const headers: Record<string, string> = {}
  for (const item of raw) {
    const idx = item.indexOf(':')
    if (idx === -1) {
      throw new Error(
        `Invalid header format: "${item}". Expected format: "Header-Name: value"`,
      )
    }
    const key = item.slice(0, idx).trim()
    const value = item.slice(idx + 1).trim()
    if (!key) {
      throw new Error(`Invalid header: "${item}". Header name cannot be empty.`)
    }
    headers[key] = value
  }
  return headers
}

export function normalizeMcpScopeForCli(scope: string | undefined): {
  scope: ReturnType<typeof ensureConfigScope>
  display: string
} {
  const raw = (scope ?? 'local').trim() || 'local'

  if (raw === 'local')
    return { scope: ensureConfigScope('project'), display: 'local' }
  if (raw === 'user')
    return { scope: ensureConfigScope('global'), display: 'user' }
  if (raw === 'project')
    return { scope: ensureConfigScope('mcpjson'), display: 'project' }

  if (raw === 'global')
    return { scope: ensureConfigScope('global'), display: 'user' }
  if (raw === 'projectConfig' || raw === 'project-config') {
    return { scope: ensureConfigScope('project'), display: 'local' }
  }

  return { scope: ensureConfigScope(raw), display: raw }
}

export function normalizeMcpTransport(transport: string | undefined): {
  transport: McpCliTransport
  explicit: boolean
} {
  if (!transport) return { transport: 'stdio', explicit: false }
  const normalized = transport.trim()
  if (normalized === 'stdio' || normalized === 'sse' || normalized === 'http') {
    return { transport: normalized, explicit: true }
  }
  throw new Error(
    `Invalid transport type: ${transport}. Must be one of: stdio, sse, http`,
  )
}
