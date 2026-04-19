import type { McpServerConfig } from '@utils/config'
import {
  getCurrentProjectConfig,
  getGlobalConfig,
  getProjectMcpServerDefinitions,
} from '@utils/config'
import { existsSync, readFileSync } from 'fs'
import { resolve } from 'path'
import { getCwd } from '@utils/state'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import { WebSocketClientTransport } from '@modelcontextprotocol/sdk/client/websocket.js'
import { memoize, pickBy } from 'lodash-es'
import { logMCPError } from '@utils/log'
import { PRODUCT_COMMAND } from '@constants/product'
import { parseJsonOrJsonc } from './internal/jsonc'
import { getMcprcServerStatus, listPluginMCPServers } from './discovery'

function getMcpServerConnectionBatchSize(): number {
  const raw = process.env.MCP_SERVER_CONNECTION_BATCH_SIZE
  const parsed = raw ? Number.parseInt(raw, 10) : NaN
  if (Number.isFinite(parsed) && parsed > 0 && parsed <= 50) return parsed
  return 3
}

async function connectToServer(
  name: string,
  serverRef: McpServerConfig,
): Promise<Client> {
  type Candidate = { transport: unknown; kind: 'stdio' | 'sse' | 'http' | 'ws' }

  const ensureWebSocketGlobal = async () => {
    if (typeof (globalThis as any).WebSocket === 'function') return
    try {
      const undici = await import('undici')
      if (typeof (undici as any).WebSocket === 'function') {
        ;(globalThis as any).WebSocket = (undici as any).WebSocket
      }
    } catch {}
  }

  const candidates: Candidate[] = await (async () => {
    switch (serverRef.type) {
      case 'sse': {
        const ref = serverRef
        return [
          {
            kind: 'sse',
            transport: new SSEClientTransport(new URL(ref.url), {
              ...(ref.headers ? { requestInit: { headers: ref.headers } } : {}),
            }),
          },
          {
            kind: 'http',
            transport: new StreamableHTTPClientTransport(new URL(ref.url), {
              ...(ref.headers ? { requestInit: { headers: ref.headers } } : {}),
            }),
          },
        ]
      }
      case 'sse-ide': {
        const ref = serverRef
        return [
          {
            kind: 'sse',
            transport: new SSEClientTransport(new URL(ref.url), {
              ...(ref.headers ? { requestInit: { headers: ref.headers } } : {}),
            }),
          },
        ]
      }
      case 'http': {
        const ref = serverRef
        return [
          {
            kind: 'http',
            transport: new StreamableHTTPClientTransport(new URL(ref.url), {
              ...(ref.headers ? { requestInit: { headers: ref.headers } } : {}),
            }),
          },
          {
            kind: 'sse',
            transport: new SSEClientTransport(new URL(ref.url), {
              ...(ref.headers ? { requestInit: { headers: ref.headers } } : {}),
            }),
          },
        ]
      }
      case 'ws': {
        const ref = serverRef
        await ensureWebSocketGlobal()
        return [
          {
            kind: 'ws',
            transport: new WebSocketClientTransport(new URL(ref.url)),
          },
        ]
      }
      case 'ws-ide': {
        const ref = serverRef

        let url = ref.url
        if (ref.authToken) {
          try {
            const parsed = new URL(url)
            if (!parsed.searchParams.has('authToken')) {
              parsed.searchParams.set('authToken', ref.authToken)
              url = parsed.toString()
            }
          } catch {}
        }

        await ensureWebSocketGlobal()
        return [
          {
            kind: 'ws',
            transport: new WebSocketClientTransport(new URL(url)),
          },
        ]
      }
      case 'stdio':
      default: {
        const ref = serverRef
        return [
          {
            kind: 'stdio',
            transport: new StdioClientTransport({
              command: ref.command,
              args: ref.args,
              env: {
                ...process.env,
                ...ref.env,
              } as Record<string, string>,
              stderr: 'pipe',
            }),
          },
        ]
      }
    }
  })()

  const rawTimeout = process.env.MCP_CONNECTION_TIMEOUT_MS
  const parsedTimeout = rawTimeout ? Number.parseInt(rawTimeout, 10) : NaN
  const CONNECTION_TIMEOUT_MS = Number.isFinite(parsedTimeout)
    ? parsedTimeout
    : 30_000

  let lastError: unknown

  for (const candidate of candidates) {
    const client = new Client(
      {
        name: PRODUCT_COMMAND,
        version: '0.1.0',
      },
      {
        capabilities: {},
      },
    )

    try {
      const connectPromise = client.connect(candidate.transport as any)
      if (CONNECTION_TIMEOUT_MS > 0) {
        const timeoutPromise = new Promise<never>((_, reject) => {
          const timeoutId = setTimeout(() => {
            reject(
              new Error(
                `Connection to MCP server "${name}" timed out after ${CONNECTION_TIMEOUT_MS}ms`,
              ),
            )
          }, CONNECTION_TIMEOUT_MS)

          connectPromise.then(
            () => clearTimeout(timeoutId),
            () => clearTimeout(timeoutId),
          )
        })

        await Promise.race([connectPromise, timeoutPromise])
      } else {
        await connectPromise
      }

      if (candidate.kind === 'stdio') {
        ;(candidate.transport as StdioClientTransport).stderr?.on(
          'data',
          (data: Buffer) => {
            const errorText = data.toString().trim()
            if (errorText) {
              logMCPError(name, `Server stderr: ${errorText}`)
            }
          },
        )
      }

      if (candidates.length > 1 && candidate !== candidates[0]) {
        logMCPError(
          name,
          `Connected using fallback transport "${candidate.kind}". Consider setting the server type explicitly in your MCP config.`,
        )
      }

      return client
    } catch (error) {
      lastError = error
      try {
        await client.close()
      } catch {}
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error(`Failed to connect to MCP server "${name}"`)
}

type ConnectedClient = {
  client: Client
  capabilities?: Record<string, unknown> | null
  name: string
  type: 'connected'
}
type FailedClient = {
  name: string
  type: 'failed'
}
export type WrappedClient = ConnectedClient | FailedClient

export const getClients = memoize(async (): Promise<WrappedClient[]> => {
  if (process.env.CI && process.env.NODE_ENV !== 'test') {
    return []
  }

  const pluginServers = listPluginMCPServers()
  const globalServers = getGlobalConfig().mcpServers ?? {}
  const projectFileServers = getProjectMcpServerDefinitions().servers
  const projectServers = getCurrentProjectConfig().mcpServers ?? {}

  const approvedProjectFileServers = pickBy(
    projectFileServers,
    (_, name) => getMcprcServerStatus(name) === 'approved',
  )

  const allServers = {
    ...pluginServers,
    ...globalServers,
    ...approvedProjectFileServers,
    ...projectServers,
  }

  const batchSize = getMcpServerConnectionBatchSize()
  const entries = Object.entries(allServers)
  const results: WrappedClient[] = []

  for (let i = 0; i < entries.length; i += batchSize) {
    const batch = entries.slice(i, i + batchSize)
    const batchResults = await Promise.all(
      batch.map(async ([name, serverRef]) => {
        try {
          const client = await connectToServer(name, serverRef as McpServerConfig)
          let capabilities: Record<string, unknown> | null = null
          try {
            capabilities = client.getServerCapabilities() as any
          } catch {
            capabilities = null
          }
          return { name, client, capabilities, type: 'connected' as const }
        } catch (error) {
          logMCPError(
            name,
            `Connection failed: ${error instanceof Error ? error.message : String(error)}`,
          )
          return { name, type: 'failed' as const }
        }
      }),
    )
    results.push(...batchResults)
  }

  return results
})

function parseMcpServersFromCliConfigEntries(options: {
  entries: string[]
  projectDir: string
}): Record<string, McpServerConfig> {
  const out: Record<string, McpServerConfig> = {}

  for (const rawEntry of options.entries) {
    const entry = String(rawEntry ?? '').trim()
    if (!entry) continue

    const resolvedPath = resolve(options.projectDir, entry)
    const payload = existsSync(resolvedPath)
      ? readFileSync(resolvedPath, 'utf8')
      : existsSync(entry)
        ? readFileSync(entry, 'utf8')
        : entry

    const parsed = parseJsonOrJsonc(payload)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) continue

    const rawServers =
      (parsed as any).mcpServers &&
      typeof (parsed as any).mcpServers === 'object' &&
      !Array.isArray((parsed as any).mcpServers)
        ? (parsed as any).mcpServers
        : parsed

    if (!rawServers || typeof rawServers !== 'object' || Array.isArray(rawServers))
      continue

    for (const [name, cfg] of Object.entries(rawServers as any)) {
      if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) continue
      out[name] = cfg as McpServerConfig
    }
  }

  return out
}

export async function getClientsForCliMcpConfig(options: {
  mcpConfig?: string[]
  strictMcpConfig?: boolean
  projectDir?: string
}): Promise<WrappedClient[]> {
  const projectDir = options.projectDir ?? getCwd()
  const entries =
    Array.isArray(options.mcpConfig) && options.mcpConfig.length > 0
      ? options.mcpConfig
      : []
  const strict = options.strictMcpConfig === true

  if (entries.length === 0 && !strict) {
    return getClients()
  }

  const cliServers = parseMcpServersFromCliConfigEntries({
    entries,
    projectDir,
  })

  const pluginServers = strict ? {} : listPluginMCPServers()
  const globalServers = strict ? {} : (getGlobalConfig().mcpServers ?? {})
  const projectFileServers = strict ? {} : getProjectMcpServerDefinitions().servers
  const projectServers = strict ? {} : (getCurrentProjectConfig().mcpServers ?? {})

  const approvedProjectFileServers = strict
    ? {}
    : pickBy(projectFileServers, (_, name) => getMcprcServerStatus(name) === 'approved')

  const allServers = {
    ...(pluginServers ?? {}),
    ...(globalServers ?? {}),
    ...(approvedProjectFileServers ?? {}),
    ...(projectServers ?? {}),
    ...(cliServers ?? {}),
  }

  const batchSize = getMcpServerConnectionBatchSize()
  const entriesToConnect = Object.entries(allServers)
  const results: WrappedClient[] = []

  for (let i = 0; i < entriesToConnect.length; i += batchSize) {
    const batch = entriesToConnect.slice(i, i + batchSize)
    const batchResults = await Promise.all(
      batch.map(async ([name, serverRef]) => {
        try {
          const client = await connectToServer(name, serverRef as McpServerConfig)
          let capabilities: Record<string, unknown> | null = null
          try {
            capabilities = client.getServerCapabilities() as any
          } catch {
            capabilities = null
          }
          return { name, client, capabilities, type: 'connected' as const }
        } catch (error) {
          logMCPError(
            name,
            `Connection failed: ${error instanceof Error ? error.message : String(error)}`,
          )
          return { name, type: 'failed' as const }
        }
      }),
    )
    results.push(...batchResults)
  }

  return results
}
