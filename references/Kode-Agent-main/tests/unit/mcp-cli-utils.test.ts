import { describe, expect, test } from 'bun:test'
import {
  looksLikeMcpUrl,
  normalizeMcpScopeForCli,
  normalizeMcpTransport,
  parseMcpHeaders,
} from '@services/mcpCliUtils'

describe('mcpCliUtils', () => {
  test('looksLikeMcpUrl detects common MCP URL patterns', () => {
    expect(looksLikeMcpUrl('http://127.0.0.1:3333/mcp')).toBe(true)
    expect(looksLikeMcpUrl('https://example.com/mcp')).toBe(true)
    expect(looksLikeMcpUrl('localhost:3333/mcp')).toBe(true)
    expect(looksLikeMcpUrl('127.0.0.1:3333/mcp')).toBe(true)
    expect(looksLikeMcpUrl('wss://example.com/mcp')).toBe(true)
    expect(looksLikeMcpUrl('http://example.com/sse')).toBe(true)
    expect(looksLikeMcpUrl('npx -y my-mcp-server')).toBe(false)
  })

  test('parseMcpHeaders parses Header: value format', () => {
    expect(parseMcpHeaders(undefined)).toBeUndefined()
    expect(parseMcpHeaders([])).toBeUndefined()

    const headers = parseMcpHeaders(['X-Api-Key: abc123', ' X-Test :  ok '])
    expect(headers).toEqual({ 'X-Api-Key': 'abc123', 'X-Test': 'ok' })
  })

  test('parseMcpHeaders rejects invalid formats', () => {
    expect(() => parseMcpHeaders(['NoColonHere'])).toThrow(
      'Invalid header format',
    )
    expect(() => parseMcpHeaders([': value'])).toThrow(
      'Header name cannot be empty',
    )
  })

  test('normalizeMcpScopeForCli maps local/user/project to internal scopes', () => {
    expect(normalizeMcpScopeForCli(undefined)).toEqual({
      scope: 'project',
      display: 'local',
    })
    expect(normalizeMcpScopeForCli('local')).toEqual({
      scope: 'project',
      display: 'local',
    })
    expect(normalizeMcpScopeForCli('user')).toEqual({
      scope: 'global',
      display: 'user',
    })
    expect(normalizeMcpScopeForCli('project')).toEqual({
      scope: 'mcpjson',
      display: 'project',
    })
  })

  test('normalizeMcpTransport defaults to stdio and validates explicit values', () => {
    expect(normalizeMcpTransport(undefined)).toEqual({
      transport: 'stdio',
      explicit: false,
    })
    expect(normalizeMcpTransport('stdio')).toEqual({
      transport: 'stdio',
      explicit: true,
    })
    expect(normalizeMcpTransport('sse')).toEqual({
      transport: 'sse',
      explicit: true,
    })
    expect(normalizeMcpTransport('http')).toEqual({
      transport: 'http',
      explicit: true,
    })
    expect(() => normalizeMcpTransport('ws')).toThrow('Invalid transport type')
  })
})
