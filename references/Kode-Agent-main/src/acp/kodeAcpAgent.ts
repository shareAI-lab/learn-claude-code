import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { dirname, isAbsolute, join, resolve } from 'node:path'

import { nanoid } from 'nanoid'

import { JsonRpcError, JsonRpcPeer } from './jsonrpc'
import * as Protocol from './protocol'

import { MACRO } from '@constants/macros'
import { PRODUCT_COMMAND } from '@constants/product'
import { getContext } from '@context'
import { getCommands, type Command } from '@commands'
import { getTools } from '@tools'
import type { Tool, ToolUseContext } from '@tool'
import { query, type Message, type UserMessage, type AssistantMessage } from '@query'
import { hasPermissionsToUseTool } from '@permissions'
import { createAssistantMessage, createUserMessage } from '@utils/messages'
import { getSystemPrompt } from '@constants/prompts'
import { logError } from '@utils/log'
import { setCwd, setOriginalCwd } from '@utils/state'
import { grantReadPermissionForOriginalDir } from '@utils/permissions/filesystem'
import { getKodeBaseDir } from '@utils/config/env'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import {
  loadToolPermissionContextFromDisk,
  persistToolPermissionUpdateToDisk,
} from '@utils/permissions/toolPermissionSettings'
import { applyToolPermissionContextUpdates } from '@kode-types/toolPermissionContext'
import type { ToolPermissionContext } from '@kode-types/toolPermissionContext'
import type { CanUseToolFn } from '@kode-types/canUseTool'
import type { WrappedClient } from '@services/mcpClient'
import { getClients } from '@services/mcpClient'

type SessionState = {
  sessionId: string
  cwd: string
  mcpServers: Protocol.McpServer[]
  mcpClients: WrappedClient[]

  commands: Command[]
  tools: Tool[]

  systemPrompt: string[]
  context: Record<string, string>

  messages: Message[]
  toolPermissionContext: ToolPermissionContext
  readFileTimestamps: Record<string, number>
  responseState: ToolUseContext['responseState']

  currentModeId: Protocol.SessionModeId
  activeAbortController: AbortController | null

  toolCalls: Map<
    string,
    {
      title: string
      kind: Protocol.ToolKind
      status: Protocol.ToolCallStatus
      rawInput?: Protocol.JsonObject
      fileSnapshot?: {
        path: string
        content: string
      }
    }
  >
}

function asJsonObject(value: unknown): Protocol.JsonObject | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  try {
    JSON.stringify(value)
    return value as Protocol.JsonObject
  } catch {
    return undefined
  }
}

function toolKindForName(toolName: string): Protocol.ToolKind {
  switch (toolName) {
    case 'Read':
      return 'read'
    case 'Write':
    case 'Edit':
    case 'MultiEdit':
    case 'NotebookEdit':
      return 'edit'
    case 'Grep':
    case 'Glob':
      return 'search'
    case 'Bash':
    case 'TaskOutput':
    case 'KillShell':
      return 'execute'
    case 'SwitchModel':
      return 'switch_mode'
    default:
      return 'other'
  }
}

function titleForToolCall(toolName: string, input: Record<string, unknown>): string {
  if (toolName === 'Read' && typeof input.file_path === 'string') {
    return `Read ${input.file_path}`
  }
  if ((toolName === 'Write' || toolName === 'Edit' || toolName === 'MultiEdit') && typeof input.file_path === 'string') {
    return `${toolName} ${input.file_path}`
  }
  if (toolName === 'Bash' && typeof input.command === 'string') {
    const cmd = input.command.trim().replace(/\s+/g, ' ')
    const clipped = cmd.length > 120 ? `${cmd.slice(0, 117)}...` : cmd
    return `Run ${clipped}`
  }
  return toolName
}

function blocksToText(blocks: Protocol.ContentBlock[]): string {
  const parts: string[] = []

  for (const block of blocks) {
    if (!block || typeof block !== 'object') continue

    switch ((block as any).type) {
      case 'text': {
        const text = typeof (block as any).text === 'string' ? (block as any).text : ''
        if (text) parts.push(text)
        break
      }
      case 'resource': {
        const resource = (block as any).resource || {}
        const uri = typeof resource.uri === 'string' ? resource.uri : ''
        const mimeType =
          typeof resource.mimeType === 'string' && resource.mimeType ? resource.mimeType : 'text/plain'
        if (typeof resource.text === 'string') {
          parts.push(
            [
              '',
              `@resource ${uri} (${mimeType})`,
              '```',
              resource.text,
              '```',
            ].join('\n'),
          )
        } else if (typeof resource.blob === 'string') {
          parts.push(
            [
              '',
              `@resource ${uri} (${mimeType}) [base64]`,
              resource.blob,
            ].join('\n'),
          )
        } else if (uri) {
          parts.push(`@resource ${uri} (${mimeType})`)
        }
        break
      }
      case 'resource_link': {
        const uri = typeof (block as any).uri === 'string' ? (block as any).uri : ''
        const name = typeof (block as any).name === 'string' ? (block as any).name : ''
        const title = typeof (block as any).title === 'string' ? (block as any).title : ''
        const description =
          typeof (block as any).description === 'string' ? (block as any).description : ''

        parts.push(
          [
            '',
            `@resource_link ${name || uri}`,
            ...(title ? [title] : []),
            ...(description ? [description] : []),
            ...(uri ? [uri] : []),
          ].join('\n'),
        )
        break
      }
      case 'image':
      case 'audio': {
        break
      }
      default:
        break
    }
  }

  return parts.join('\n').trim()
}

function extractAssistantText(msg: AssistantMessage): string {
  const blocks: any[] = Array.isArray((msg as any)?.message?.content) ? ((msg as any).message.content as any[]) : []
  const texts: string[] = []
  for (const b of blocks) {
    if (!b || typeof b !== 'object') continue
    if (b.type === 'text' && typeof b.text === 'string') texts.push(b.text)
    if (b.type === 'thinking' && typeof (b as any).thinking === 'string') texts.push((b as any).thinking)
  }
  return texts.join('').trim()
}

function extractToolUses(msg: AssistantMessage): Array<{ id: string; name: string; input: Record<string, unknown> }> {
  const blocks: any[] = Array.isArray((msg as any)?.message?.content) ? ((msg as any).message.content as any[]) : []
  const out: Array<{ id: string; name: string; input: Record<string, unknown> }> = []
  for (const b of blocks) {
    if (!b || typeof b !== 'object') continue
    if (b.type !== 'tool_use') continue
    const id = typeof b.id === 'string' ? b.id : ''
    const name = typeof b.name === 'string' ? b.name : ''
    const input = b.input && typeof b.input === 'object' && !Array.isArray(b.input) ? (b.input as Record<string, unknown>) : {}
    if (id && name) out.push({ id, name, input })
  }
  return out
}

function extractToolResults(msg: UserMessage): Array<{ toolUseId: string; isError: boolean; content: string }> {
  const content = (msg as any)?.message?.content
  const blocks: any[] = Array.isArray(content) ? content : []
  const out: Array<{ toolUseId: string; isError: boolean; content: string }> = []

  for (const b of blocks) {
    if (!b || typeof b !== 'object') continue
    if (b.type !== 'tool_result') continue
    const toolUseId = typeof b.tool_use_id === 'string' ? b.tool_use_id : ''
    const isError = Boolean(b.is_error)
    const raw = b.content
    const text =
      typeof raw === 'string'
        ? raw
        : Array.isArray(raw)
          ? raw
              .filter(x => x && typeof x === 'object' && (x as any).type === 'text')
              .map(x => String((x as any).text ?? ''))
              .join('')
          : ''
    if (toolUseId) out.push({ toolUseId, isError, content: text })
  }

  return out
}

const ACP_SESSION_STORE_VERSION = 1
const MAX_DIFF_FILE_BYTES = 512_000
const MAX_DIFF_TEXT_CHARS = 400_000

type PersistedAcpSession = {
  version: number
  sessionId: string
  cwd: string
  mcpServers: Protocol.McpServer[]
  messages: Message[]
  toolPermissionContext: ToolPermissionContext
  readFileTimestamps: Record<string, number>
  responseState: ToolUseContext['responseState']
  currentModeId: Protocol.SessionModeId
}

function getProjectDirSlug(cwd: string): string {
  return cwd.replace(/[^a-zA-Z0-9]/g, '-')
}

function sanitizeSessionId(sessionId: string): string {
  return sessionId.replace(/[^a-zA-Z0-9_-]/g, '_')
}

function getAcpSessionDir(cwd: string): string {
  return join(getKodeBaseDir(), getProjectDirSlug(cwd), 'acp-sessions')
}

function getAcpSessionFilePath(cwd: string, sessionId: string): string {
  return join(getAcpSessionDir(cwd), `${sanitizeSessionId(sessionId)}.json`)
}

function readTextFileForDiff(filePath: string): string | null {
  try {
    const stats = statSync(filePath)
    if (!stats.isFile()) return null
    if (stats.size > MAX_DIFF_FILE_BYTES) return null
    return readFileSync(filePath, 'utf8')
  } catch {
    return null
  }
}

function truncateDiffText(text: string): string {
  if (text.length <= MAX_DIFF_TEXT_CHARS) return text
  return `${text.slice(0, MAX_DIFF_TEXT_CHARS)}\n\n[truncated ${text.length - MAX_DIFF_TEXT_CHARS} chars]`
}

function persistAcpSessionToDisk(session: SessionState): void {
  try {
    const dir = getAcpSessionDir(session.cwd)
    mkdirSync(dir, { recursive: true })

    const payload: PersistedAcpSession = {
      version: ACP_SESSION_STORE_VERSION,
      sessionId: session.sessionId,
      cwd: session.cwd,
      mcpServers: session.mcpServers,
      messages: session.messages,
      toolPermissionContext: session.toolPermissionContext,
      readFileTimestamps: session.readFileTimestamps,
      responseState: session.responseState,
      currentModeId: session.currentModeId,
    }

    const path = getAcpSessionFilePath(session.cwd, session.sessionId)
    writeFileSync(path, JSON.stringify(payload, null, 2), 'utf8')
  } catch (e) {
    logError(e)
  }
}

function loadAcpSessionFromDisk(cwd: string, sessionId: string): PersistedAcpSession | null {
  try {
    const path = getAcpSessionFilePath(cwd, sessionId)
    if (!existsSync(path)) return null
    const raw = readFileSync(path, 'utf8')
    const parsed = JSON.parse(raw) as PersistedAcpSession
    if (!parsed || typeof parsed !== 'object') return null
    if (parsed.sessionId !== sessionId) return null
    if (typeof parsed.cwd !== 'string' || parsed.cwd !== cwd) return null
    if (!Array.isArray(parsed.messages)) return null
    return parsed
  } catch {
    return null
  }
}

async function connectAcpMcpServers(mcpServers: Protocol.McpServer[]): Promise<WrappedClient[]> {
  if (!Array.isArray(mcpServers) || mcpServers.length === 0) return []

  const rawTimeout = process.env.MCP_CONNECTION_TIMEOUT_MS
  const parsedTimeout = rawTimeout ? Number.parseInt(rawTimeout, 10) : NaN
  const timeoutMs = Number.isFinite(parsedTimeout) ? parsedTimeout : 30_000

  const results: WrappedClient[] = []

  type Candidate = { kind: 'stdio' | 'http' | 'sse'; transport: unknown }

  const connectWithTimeout = async (client: Client, transport: unknown, name: string): Promise<void> => {
    const connectPromise = client.connect(transport as any)
    if (timeoutMs > 0) {
      const timeoutPromise = new Promise<never>((_, reject) => {
        const timeoutId = setTimeout(() => {
          reject(new Error(`Connection to MCP server "${name}" timed out after ${timeoutMs}ms`))
        }, timeoutMs)
        connectPromise.then(
          () => clearTimeout(timeoutId),
          () => clearTimeout(timeoutId),
        )
      })
      await Promise.race([connectPromise, timeoutPromise])
    } else {
      await connectPromise
    }
  }

  for (const server of mcpServers) {
    const serverType = typeof (server as any)?.type === 'string' ? String((server as any).type) : 'stdio'

    const name = typeof (server as any)?.name === 'string' ? String((server as any).name) : ''
    if (!name) {
      results.push({ name: '<invalid>', type: 'failed' })
      continue
    }

    const candidates: Candidate[] = []

	    if (serverType === 'http' || serverType === 'sse') {
	      const url = typeof (server as any)?.url === 'string' ? String((server as any).url) : ''
	      if (!url) {
	        results.push({ name, type: 'failed' })
	        continue
	      }
	
	      let parsedUrl: URL
	      try {
	        parsedUrl = new URL(url)
	      } catch (e) {
	        logError(e)
	        results.push({ name, type: 'failed' })
	        continue
	      }

	      const headerList = Array.isArray((server as any)?.headers) ? ((server as any).headers as unknown[]) : []
	      const headers: Record<string, string> = {}
	      for (const h of headerList) {
	        if (!h || typeof h !== 'object') continue
        const k = typeof (h as any).name === 'string' ? String((h as any).name) : ''
        const val = typeof (h as any).value === 'string' ? String((h as any).value) : ''
        if (k) headers[k] = val
      }

	      const requestInit = Object.keys(headers).length > 0 ? { requestInit: { headers } } : {}

	      if (serverType === 'http') {
	        candidates.push(
	          { kind: 'http', transport: new StreamableHTTPClientTransport(parsedUrl, requestInit as any) },
	          { kind: 'sse', transport: new SSEClientTransport(parsedUrl, requestInit as any) },
	        )
	      } else {
	        candidates.push(
	          { kind: 'sse', transport: new SSEClientTransport(parsedUrl, requestInit as any) },
	          { kind: 'http', transport: new StreamableHTTPClientTransport(parsedUrl, requestInit as any) },
	        )
	      }
	    } else {
      const command = typeof (server as any)?.command === 'string' ? String((server as any).command) : ''
      const args = Array.isArray((server as any)?.args) ? ((server as any).args as unknown[]).map(a => String(a)) : []
      const envList = Array.isArray((server as any)?.env) ? ((server as any).env as unknown[]) : []

      if (!command) {
        results.push({ name, type: 'failed' })
        continue
      }

      const envFromParams: Record<string, string> = {}
      for (const v of envList) {
        if (!v || typeof v !== 'object') continue
        const k = typeof (v as any).name === 'string' ? String((v as any).name) : ''
        const val = typeof (v as any).value === 'string' ? String((v as any).value) : ''
        if (k) envFromParams[k] = val
      }

      candidates.push({
        kind: 'stdio',
        transport: new StdioClientTransport({
          command,
          args,
          env: { ...process.env, ...envFromParams } as Record<string, string>,
          stderr: 'pipe',
        }),
      })
    }

    let lastError: unknown
    for (const candidate of candidates) {
      const client = new Client(
        { name: PRODUCT_COMMAND, version: MACRO.VERSION || '0.0.0' },
        { capabilities: {} },
      )

      try {
        await connectWithTimeout(client, candidate.transport, name)

        let capabilities: Record<string, unknown> | null = null
        try {
          capabilities = client.getServerCapabilities() as any
        } catch {
          capabilities = null
        }

        results.push({ name, client, capabilities, type: 'connected' as const })
        lastError = null
        break
      } catch (e) {
        lastError = e
        try {
          await client.close()
        } catch {}
      }
    }

    if (lastError) {
      logError(lastError)
      results.push({ name, type: 'failed' as const })
    }
  }

  return results
}

function mergeMcpClients(base: WrappedClient[], extra: WrappedClient[]): WrappedClient[] {
  const map = new Map<string, WrappedClient>()
  for (const c of base) map.set(c.name, c)
  for (const c of extra) map.set(c.name, c)
  return Array.from(map.values())
}

export class KodeAcpAgent {
  private clientCapabilities: Protocol.ClientCapabilities = {}
  private sessions = new Map<string, SessionState>()

  constructor(private readonly peer: JsonRpcPeer) {
    this.registerMethods()
  }

  private registerMethods(): void {
    this.peer.registerMethod('initialize', this.handleInitialize.bind(this))
    this.peer.registerMethod('authenticate', this.handleAuthenticate.bind(this))
    this.peer.registerMethod('session/new', this.handleSessionNew.bind(this))
    this.peer.registerMethod('session/load', this.handleSessionLoad.bind(this))
    this.peer.registerMethod('session/prompt', this.handleSessionPrompt.bind(this))
    this.peer.registerMethod('session/set_mode', this.handleSessionSetMode.bind(this))
    this.peer.registerMethod('session/cancel', this.handleSessionCancel.bind(this))
  }

  private async handleInitialize(params: unknown): Promise<Protocol.InitializeResponse> {
    const p = (params ?? {}) as Partial<Protocol.InitializeParams>
    const protocolVersion = typeof p.protocolVersion === 'number' ? p.protocolVersion : Protocol.ACP_PROTOCOL_VERSION

    this.clientCapabilities =
      p.clientCapabilities && typeof p.clientCapabilities === 'object' ? (p.clientCapabilities as Protocol.ClientCapabilities) : {}

    return {
      protocolVersion: Protocol.ACP_PROTOCOL_VERSION,
      agentCapabilities: {
        loadSession: true,
        promptCapabilities: {
          image: false,
          audio: false,
          embeddedContext: true,
          embeddedContent: true,
        },
        mcpCapabilities: {
          http: true,
          sse: true,
        },
      },
      agentInfo: {
        name: 'kode',
        title: 'Kode',
        version: MACRO.VERSION || '0.0.0',
      },
      authMethods: [],
    }
  }

  private async handleAuthenticate(_params: unknown): Promise<Protocol.AuthenticateResponse> {
    return {}
  }

  private async handleSessionNew(params: unknown): Promise<Protocol.NewSessionResponse> {
    const p = (params ?? {}) as Partial<Protocol.NewSessionParams>
    const cwd = typeof p.cwd === 'string' ? p.cwd : ''
    if (!cwd) {
      throw new JsonRpcError(-32602, 'Missing required param: cwd')
    }
    if (!isAbsolute(cwd)) {
      throw new JsonRpcError(-32602, `cwd must be an absolute path: ${cwd}`)
    }

    setOriginalCwd(cwd)
    await setCwd(cwd)
    grantReadPermissionForOriginalDir()

    const mcpServers = Array.isArray(p.mcpServers) ? (p.mcpServers as Protocol.McpServer[]) : []

    const [commands, tools, ctx, systemPrompt, configuredMcpClients] = await Promise.all([
      getCommands(),
      getTools(),
      getContext(),
      getSystemPrompt({ disableSlashCommands: false }),
      getClients().catch(() => [] as WrappedClient[]),
    ])
    const acpMcpClients = await connectAcpMcpServers(mcpServers)
    const mcpClients = mergeMcpClients(configuredMcpClients, acpMcpClients)

    const toolPermissionContext = loadToolPermissionContextFromDisk({
      projectDir: cwd,
      includeKodeProjectConfig: true,
      isBypassPermissionsModeAvailable: true,
    })

    const sessionId = `sess_${nanoid()}`

    const session: SessionState = {
      sessionId,
      cwd,
      mcpServers,
      mcpClients,
      commands,
      tools,
      systemPrompt,
      context: ctx,
      messages: [],
      toolPermissionContext,
      readFileTimestamps: {},
      responseState: {},
      currentModeId: toolPermissionContext.mode ?? 'default',
      activeAbortController: null,
      toolCalls: new Map(),
    }

    this.sessions.set(sessionId, session)

    this.sendAvailableCommands(session)
    this.sendCurrentMode(session)
    persistAcpSessionToDisk(session)

    return {
      sessionId,
      modes: this.getModeState(session),
    }
  }

  private async handleSessionLoad(params: unknown): Promise<Protocol.LoadSessionResponse> {
    const p = (params ?? {}) as Partial<Protocol.LoadSessionParams>
    const sessionId = typeof p.sessionId === 'string' ? p.sessionId : ''
    const cwd = typeof p.cwd === 'string' ? p.cwd : ''
    if (!sessionId) throw new JsonRpcError(-32602, 'Missing required param: sessionId')
    if (!cwd) throw new JsonRpcError(-32602, 'Missing required param: cwd')
    if (!isAbsolute(cwd)) {
      throw new JsonRpcError(-32602, `cwd must be an absolute path: ${cwd}`)
    }

    setOriginalCwd(cwd)
    await setCwd(cwd)
    grantReadPermissionForOriginalDir()

    const persisted = loadAcpSessionFromDisk(cwd, sessionId)
    if (!persisted) {
      throw new JsonRpcError(-32602, `Session not found: ${sessionId}`)
    }

    const mcpServers = Array.isArray(p.mcpServers) ? (p.mcpServers as Protocol.McpServer[]) : []

    const [commands, tools, ctx, systemPrompt, configuredMcpClients] = await Promise.all([
      getCommands(),
      getTools(),
      getContext(),
      getSystemPrompt({ disableSlashCommands: false }),
      getClients().catch(() => [] as WrappedClient[]),
    ])

    const acpMcpClients = await connectAcpMcpServers(mcpServers)
    const mcpClients = mergeMcpClients(configuredMcpClients, acpMcpClients)

    const toolPermissionContext = loadToolPermissionContextFromDisk({
      projectDir: cwd,
      includeKodeProjectConfig: true,
      isBypassPermissionsModeAvailable: true,
    })

    const currentModeId =
      typeof persisted.currentModeId === 'string' && persisted.currentModeId
        ? persisted.currentModeId
        : toolPermissionContext.mode ?? 'default'
    toolPermissionContext.mode = currentModeId as any

    const session: SessionState = {
      sessionId,
      cwd,
      mcpServers,
      mcpClients,
      commands,
      tools,
      systemPrompt,
      context: ctx,
      messages: Array.isArray(persisted.messages) ? persisted.messages : [],
      toolPermissionContext,
      readFileTimestamps:
        persisted.readFileTimestamps && typeof persisted.readFileTimestamps === 'object'
          ? (persisted.readFileTimestamps as Record<string, number>)
          : {},
      responseState:
        persisted.responseState && typeof persisted.responseState === 'object'
          ? (persisted.responseState as ToolUseContext['responseState'])
          : {},
      currentModeId,
      activeAbortController: null,
      toolCalls: new Map(),
    }

    this.sessions.set(sessionId, session)
    this.sendAvailableCommands(session)
    this.sendCurrentMode(session)
    this.replayConversation(session)

    return { modes: this.getModeState(session) }
  }

  private async handleSessionSetMode(params: unknown): Promise<Protocol.SetSessionModeResponse> {
    const p = (params ?? {}) as Partial<Protocol.SetSessionModeParams>
    const sessionId = typeof p.sessionId === 'string' ? p.sessionId : ''
    const modeId = typeof p.modeId === 'string' ? p.modeId : ''

    const session = this.sessions.get(sessionId)
    if (!session) throw new JsonRpcError(-32602, `Session not found: ${sessionId}`)

    const allowed = new Set(this.getModeState(session).availableModes.map(m => m.id))
    if (!allowed.has(modeId)) {
      throw new JsonRpcError(-32602, `Unknown modeId: ${modeId}`)
    }

    session.currentModeId = modeId
    session.toolPermissionContext.mode = modeId as any
    this.sendCurrentMode(session)
    persistAcpSessionToDisk(session)

    return {}
  }

  private async handleSessionCancel(params: unknown): Promise<void> {
    const p = (params ?? {}) as Partial<Protocol.SessionCancelParams>
    const sessionId = typeof p.sessionId === 'string' ? p.sessionId : ''
    const session = this.sessions.get(sessionId)
    if (!session) return
    session.activeAbortController?.abort()
  }

  private async handleSessionPrompt(params: unknown): Promise<Protocol.PromptResponse> {
    const p = (params ?? {}) as any
    const sessionId = typeof p.sessionId === 'string' ? p.sessionId : ''
    const blocks: Protocol.ContentBlock[] = Array.isArray(p.prompt)
      ? (p.prompt as Protocol.ContentBlock[])
      : Array.isArray(p.content)
        ? (p.content as Protocol.ContentBlock[])
        : []

    const session = this.sessions.get(sessionId)
    if (!session) throw new JsonRpcError(-32602, `Session not found: ${sessionId}`)

    if (session.activeAbortController) {
      throw new JsonRpcError(-32000, `Session already has an active prompt: ${sessionId}`)
    }

    setOriginalCwd(session.cwd)
    await setCwd(session.cwd)
    grantReadPermissionForOriginalDir()

    const promptText = blocksToText(blocks)
    const userMsg = createUserMessage(promptText)

    const baseMessages: Message[] = [...session.messages, userMsg]
    session.messages.push(userMsg)

    if (process.env.KODE_ACP_ECHO === '1') {
      await this.handleKodeMessage(session, createAssistantMessage(promptText))
      persistAcpSessionToDisk(session)
      return { stopReason: 'end_turn' }
    }

    const abortController = new AbortController()
    session.activeAbortController = abortController

    const canUseTool = this.createAcpCanUseTool(session)

    const options = {
      commands: session.commands,
      tools: session.tools,
      verbose: false,
      safeMode: false,
      forkNumber: 0,
      messageLogName: session.sessionId,
      maxThinkingTokens: 0,
      persistSession: false,
      toolPermissionContext: session.toolPermissionContext,
      mcpClients: session.mcpClients,
      shouldAvoidPermissionPrompts: false,
    }

    let stopReason: Protocol.StopReason = 'end_turn'
    try {
      for await (const m of query(baseMessages, session.systemPrompt, session.context, canUseTool, {
        options,
        abortController,
        messageId: undefined,
        readFileTimestamps: session.readFileTimestamps,
        setToolJSX: () => {},
        agentId: 'main',
        responseState: session.responseState,
      })) {
        if (abortController.signal.aborted) {
          stopReason = 'cancelled'
        }
        await this.handleKodeMessage(session, m)
      }
      if (abortController.signal.aborted) stopReason = 'cancelled'
    } catch (err) {
      if (abortController.signal.aborted) {
        stopReason = 'cancelled'
      } else {
        logError(err)
        const msg = err instanceof Error ? err.message : String(err)
        this.sendAgentMessage(session.sessionId, msg)
        stopReason = 'end_turn'
      }
    } finally {
      session.activeAbortController = null
      persistAcpSessionToDisk(session)
    }

    return { stopReason }
  }

  private async handleKodeMessage(session: SessionState, m: Message): Promise<void> {
    if (!m || typeof m !== 'object') return

    if (m.type === 'assistant') {
      session.messages.push(m)

      const blocks: any[] = Array.isArray((m as any).message?.content) ? ((m as any).message.content as any[]) : []
      for (const b of blocks) {
        if (!b || typeof b !== 'object') continue
        if (b.type === 'text' && typeof b.text === 'string') {
          this.sendAgentMessage(session.sessionId, b.text)
        } else if (b.type === 'thinking' && typeof (b as any).thinking === 'string') {
          this.sendAgentThought(session.sessionId, (b as any).thinking)
        } else if (b.type === 'tool_use') {
          const toolUseId = typeof b.id === 'string' ? b.id : ''
          const toolName = typeof b.name === 'string' ? b.name : ''
          const input = b.input && typeof b.input === 'object' && !Array.isArray(b.input) ? (b.input as Record<string, unknown>) : {}
          if (!toolUseId || !toolName) continue
          const kind = toolKindForName(toolName)
          const title = titleForToolCall(toolName, input)
          session.toolCalls.set(toolUseId, {
            title,
            kind,
            status: 'pending',
            rawInput: asJsonObject(input),
          })
          this.peer.sendNotification('session/update', {
            sessionId: session.sessionId,
            update: {
              sessionUpdate: 'tool_call',
              toolCallId: toolUseId,
              title,
              kind,
              status: 'pending',
              rawInput: asJsonObject(input),
            } satisfies Protocol.ToolCall,
          } satisfies Protocol.SessionUpdateNotification)
        }
      }
      return
    }

    if (m.type === 'progress') {
      const toolCallId = m.toolUseID
      const existing = session.toolCalls.get(toolCallId)
      const title = existing?.title ?? 'Tool'
      const kind = existing?.kind ?? 'other'

      if (!existing || existing.status === 'pending') {
        session.toolCalls.set(toolCallId, {
          title,
          kind,
          status: 'in_progress',
          rawInput: existing?.rawInput,
        })
        this.sendToolCallUpdate(session.sessionId, {
          toolCallId,
          status: 'in_progress',
        })
      }

      const text = extractAssistantText(m.content)
      if (text) {
        this.sendToolCallUpdate(session.sessionId, {
          toolCallId,
          content: [
            {
              type: 'content',
              content: { type: 'text', text },
            },
          ],
        })
      }
      return
    }

    if (m.type === 'user') {
      const toolResults = extractToolResults(m)
      if (toolResults.length === 0) {
        session.messages.push(m)
        return
      }

      for (const tr of toolResults) {
        const existing = session.toolCalls.get(tr.toolUseId)
        const title = existing?.title ?? 'Tool'
        const kind = existing?.kind ?? 'other'

        if (!existing || existing.status === 'pending') {
          session.toolCalls.set(tr.toolUseId, {
            title,
            kind,
            status: 'in_progress',
            rawInput: existing?.rawInput,
          })
          this.sendToolCallUpdate(session.sessionId, {
            toolCallId: tr.toolUseId,
            status: 'in_progress',
          })
        }

        const status: Protocol.ToolCallStatus = tr.isError ? 'failed' : 'completed'
        session.toolCalls.set(tr.toolUseId, {
          title,
          kind,
          status,
          rawInput: existing?.rawInput,
        })

        const rawOutput = asJsonObject((m as any).toolUseResult?.data)

        const content: Protocol.ToolCallContent[] = []
        const diffContent = status === 'completed' ? this.buildDiffContentForToolResult(session, tr.toolUseId, rawOutput) : null
        if (diffContent) content.push(diffContent)
        if (tr.content) {
          content.push({ type: 'content', content: { type: 'text', text: tr.content } })
        }

        this.sendToolCallUpdate(session.sessionId, {
          toolCallId: tr.toolUseId,
          status,
          ...(content.length > 0 ? { content } : {}),
          ...(rawOutput ? { rawOutput } : {}),
        })
      }

      session.messages.push(m)
      return
    }
  }

  private createAcpCanUseTool(session: SessionState): CanUseToolFn {
    const timeoutMs = (() => {
      const raw = process.env.KODE_ACP_PERMISSION_TIMEOUT_MS
      const parsed = raw ? Number(raw) : NaN
      return Number.isFinite(parsed) && parsed > 0 ? parsed : 30_000
    })()

    return async (tool, input, toolUseContext, assistantMessage) => {
      const toolUseId =
        typeof toolUseContext?.toolUseId === 'string' && toolUseContext.toolUseId
          ? toolUseContext.toolUseId
          : `call_${nanoid()}`

      const base = await hasPermissionsToUseTool(tool, input, toolUseContext, assistantMessage)
      if (base.result === true) {
        this.captureFileSnapshotForTool(session, toolUseId, tool.name, input)
        return base
      }

      const denied = base as Extract<typeof base, { result: false }>
      if (denied.shouldPromptUser === false) {
        return { result: false as const, message: denied.message }
      }

      const title = titleForToolCall(tool.name, input as any)
      const kind = toolKindForName(tool.name)

      if (!session.toolCalls.has(toolUseId)) {
        session.toolCalls.set(toolUseId, { title, kind, status: 'pending', rawInput: asJsonObject(input) })
        this.peer.sendNotification('session/update', {
          sessionId: session.sessionId,
          update: {
            sessionUpdate: 'tool_call',
            toolCallId: toolUseId,
            title,
            kind,
            status: 'pending',
            rawInput: asJsonObject(input),
          } satisfies Protocol.ToolCall,
        } satisfies Protocol.SessionUpdateNotification)
      }

      const options: Protocol.PermissionOption[] = [
        { optionId: 'allow_once', name: 'Allow once', kind: 'allow_once' },
        { optionId: 'reject_once', name: 'Reject', kind: 'reject_once' },
      ]
      if (Array.isArray((denied as any).suggestions) && (denied as any).suggestions.length > 0) {
        options.splice(1, 0, {
          optionId: 'allow_always',
          name: 'Allow always (remember)',
          kind: 'allow_always',
        })
      }

      try {
        const response = await this.peer.sendRequest<Protocol.RequestPermissionResponse>({
          method: 'session/request_permission',
          params: {
            sessionId: session.sessionId,
            toolCall: {
              toolCallId: toolUseId,
              title,
              kind,
              status: 'pending',
              content: [
                {
                  type: 'content',
                  content: { type: 'text', text: denied.message },
                },
              ],
              rawInput: asJsonObject(input),
            },
            options,
          } satisfies Protocol.RequestPermissionParams,
          signal: toolUseContext.abortController.signal,
          timeoutMs,
        })

        const outcome = response?.outcome
        if (!outcome || outcome.outcome === 'cancelled') {
          toolUseContext.abortController.abort()
          return { result: false as const, message: denied.message, shouldPromptUser: false }
        }

        if (outcome.outcome === 'selected' && outcome.optionId === 'allow_once') {
          this.captureFileSnapshotForTool(session, toolUseId, tool.name, input)
          return { result: true as const }
        }

        if (outcome.outcome === 'selected' && outcome.optionId === 'allow_always') {
          const suggestions = Array.isArray((denied as any).suggestions) ? ((denied as any).suggestions as any[]) : []
          if (suggestions.length > 0) {
            const next = applyToolPermissionContextUpdates(session.toolPermissionContext, suggestions as any)
            session.toolPermissionContext = next
            if (toolUseContext?.options) toolUseContext.options.toolPermissionContext = next
            for (const update of suggestions) {
              try {
                persistToolPermissionUpdateToDisk({ update, projectDir: session.cwd })
              } catch (e) {
                logError(e)
              }
            }
          }
          this.captureFileSnapshotForTool(session, toolUseId, tool.name, input)
          return { result: true as const }
        }

        return { result: false as const, message: denied.message }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        return { result: false as const, message: `Permission prompt failed: ${msg}`, shouldPromptUser: false }
      }
    }
  }

  private captureFileSnapshotForTool(
    session: SessionState,
    toolUseId: string,
    toolName: string,
    input: unknown,
  ): void {
    if (toolName !== 'Write' && toolName !== 'MultiEdit') return

    const filePath = input && typeof input === 'object' ? String((input as any).file_path ?? '') : ''
    if (!filePath) return

    const absPath = isAbsolute(filePath) ? filePath : resolve(session.cwd, filePath)

    const oldContent = existsSync(absPath) ? readTextFileForDiff(absPath) : ''
    if (oldContent === null) return

    const existing = session.toolCalls.get(toolUseId)
    if (existing) {
      existing.fileSnapshot = { path: absPath, content: oldContent }
      session.toolCalls.set(toolUseId, existing)
      return
    }

    session.toolCalls.set(toolUseId, {
      title: toolName,
      kind: toolKindForName(toolName),
      status: 'pending',
      rawInput: asJsonObject(input),
      fileSnapshot: { path: absPath, content: oldContent },
    })
  }

  private buildDiffContentForToolResult(
    session: SessionState,
    toolUseId: string,
    rawOutput: Protocol.JsonObject | undefined,
  ): Protocol.ToolCallContent | null {
    const existing = session.toolCalls.get(toolUseId)
    if (!existing || existing.kind !== 'edit') return null

    const inputFilePath =
      typeof existing.rawInput?.file_path === 'string'
        ? existing.rawInput.file_path
        : rawOutput && typeof (rawOutput as any).filePath === 'string'
          ? String((rawOutput as any).filePath)
          : ''

    if (!inputFilePath) return null

    const absPath = isAbsolute(inputFilePath) ? inputFilePath : resolve(session.cwd, inputFilePath)

    const oldText =
      rawOutput && typeof (rawOutput as any).originalFile === 'string'
        ? String((rawOutput as any).originalFile)
        : existing.fileSnapshot && existing.fileSnapshot.path === absPath
          ? existing.fileSnapshot.content
          : undefined

    if (oldText === undefined) return null

    const newTextFromDisk = readTextFileForDiff(absPath)
    const newTextFromOutput = rawOutput && typeof (rawOutput as any).content === 'string' ? String((rawOutput as any).content) : null
    const newText = newTextFromDisk ?? newTextFromOutput
    if (newText === null) return null

    return {
      type: 'diff',
      path: absPath,
      oldText: truncateDiffText(oldText),
      newText: truncateDiffText(newText),
    }
  }

  private replayConversation(session: SessionState): void {
    session.toolCalls.clear()

    for (const m of session.messages) {
      if (!m || typeof m !== 'object') continue

      if (m.type === 'assistant') {
        const blocks: any[] = Array.isArray((m as any).message?.content) ? ((m as any).message.content as any[]) : []
        for (const b of blocks) {
          if (!b || typeof b !== 'object') continue
          if (b.type === 'text' && typeof b.text === 'string') {
            this.sendAgentMessage(session.sessionId, b.text)
          } else if (b.type === 'thinking' && typeof (b as any).thinking === 'string') {
            this.sendAgentThought(session.sessionId, (b as any).thinking)
          } else if (b.type === 'tool_use') {
            const toolUseId = typeof b.id === 'string' ? b.id : ''
            const toolName = typeof b.name === 'string' ? b.name : ''
            const input = b.input && typeof b.input === 'object' && !Array.isArray(b.input) ? (b.input as Record<string, unknown>) : {}
            if (!toolUseId || !toolName) continue

            if (!session.toolCalls.has(toolUseId)) {
              const kind = toolKindForName(toolName)
              const title = titleForToolCall(toolName, input)
              session.toolCalls.set(toolUseId, {
                title,
                kind,
                status: 'pending',
                rawInput: asJsonObject(input),
              })
              this.peer.sendNotification('session/update', {
                sessionId: session.sessionId,
                update: {
                  sessionUpdate: 'tool_call',
                  toolCallId: toolUseId,
                  title,
                  kind,
                  status: 'pending',
                  rawInput: asJsonObject(input),
                } satisfies Protocol.ToolCall,
              } satisfies Protocol.SessionUpdateNotification)
            }
          }
        }
        continue
      }

      if (m.type === 'user') {
        const content = (m as any)?.message?.content
        if (typeof content === 'string' && content.trim()) {
          this.sendUserMessage(session.sessionId, content)
        }

        const toolResults = extractToolResults(m)
        if (toolResults.length === 0) continue

        for (const tr of toolResults) {
          const existing = session.toolCalls.get(tr.toolUseId)
          const title = existing?.title ?? 'Tool'
          const kind = existing?.kind ?? 'other'

          if (!existing) {
            session.toolCalls.set(tr.toolUseId, { title, kind, status: 'pending' })
            this.peer.sendNotification('session/update', {
              sessionId: session.sessionId,
              update: {
                sessionUpdate: 'tool_call',
                toolCallId: tr.toolUseId,
                title,
                kind,
                status: 'pending',
              } satisfies Protocol.ToolCall,
            } satisfies Protocol.SessionUpdateNotification)
          }

          const status: Protocol.ToolCallStatus = tr.isError ? 'failed' : 'completed'
          const contentBlocks: Protocol.ToolCallContent[] = []
          if (tr.content) {
            contentBlocks.push({ type: 'content', content: { type: 'text', text: tr.content } })
          }

          const rawOutput = asJsonObject((m as any).toolUseResult?.data)

          this.sendToolCallUpdate(session.sessionId, {
            toolCallId: tr.toolUseId,
            status,
            ...(contentBlocks.length > 0 ? { content: contentBlocks } : {}),
            ...(rawOutput ? { rawOutput } : {}),
          })

          session.toolCalls.set(tr.toolUseId, {
            title,
            kind,
            status,
            rawInput: existing?.rawInput,
          })
        }
      }
    }
  }

  private getModeState(session: SessionState): Protocol.SessionModeState {
    const availableModes: Protocol.SessionMode[] = [
      { id: 'default', name: 'Default', description: 'Normal permissions (prompt when needed)' },
      { id: 'acceptEdits', name: 'Accept Edits', description: 'Auto-approve safe file edits' },
      { id: 'plan', name: 'Plan', description: 'Read-only planning mode' },
      { id: 'dontAsk', name: "Don't Ask", description: 'Auto-deny permission prompts' },
      { id: 'bypassPermissions', name: 'Bypass', description: 'Bypass permission prompts (dangerous)' },
    ]

    const currentModeId = availableModes.some(m => m.id === session.currentModeId) ? session.currentModeId : 'default'
    return { currentModeId, availableModes }
  }

  private sendAvailableCommands(session: SessionState): void {
    const availableCommands: Protocol.AvailableCommand[] = session.commands
      .filter(c => !c.isHidden)
      .map(c => ({
        name: c.userFacingName(),
        description: c.description,
        ...(c.argumentHint ? { input: { hint: c.argumentHint } } : {}),
      }))

    this.peer.sendNotification('session/update', {
      sessionId: session.sessionId,
      update: {
        sessionUpdate: 'available_commands_update',
        availableCommands,
      } satisfies Protocol.AvailableCommandsUpdate,
    } satisfies Protocol.SessionUpdateNotification)
  }

  private sendCurrentMode(session: SessionState): void {
    this.peer.sendNotification('session/update', {
      sessionId: session.sessionId,
      update: {
        sessionUpdate: 'current_mode_update',
        currentModeId: session.currentModeId,
      } satisfies Protocol.CurrentModeUpdate,
    } satisfies Protocol.SessionUpdateNotification)
  }

  private sendUserMessage(sessionId: string, text: string): void {
    if (!text) return
    this.peer.sendNotification('session/update', {
      sessionId,
      update: {
        sessionUpdate: 'user_message_chunk',
        content: { type: 'text', text },
      } satisfies Protocol.UserMessageChunk,
    } satisfies Protocol.SessionUpdateNotification)
  }

  private sendAgentMessage(sessionId: string, text: string): void {
    if (!text) return
    this.peer.sendNotification('session/update', {
      sessionId,
      update: {
        sessionUpdate: 'agent_message_chunk',
        content: { type: 'text', text },
      } satisfies Protocol.AgentMessageChunk,
    } satisfies Protocol.SessionUpdateNotification)
  }

  private sendAgentThought(sessionId: string, text: string): void {
    if (!text) return
    this.peer.sendNotification('session/update', {
      sessionId,
      update: {
        sessionUpdate: 'agent_thought_chunk',
        content: { type: 'text', text },
      } satisfies Protocol.AgentThoughtChunk,
    } satisfies Protocol.SessionUpdateNotification)
  }

  private sendToolCallUpdate(sessionId: string, update: Omit<Protocol.ToolCallUpdate, 'sessionUpdate'>): void {
    this.peer.sendNotification('session/update', {
      sessionId,
      update: {
        sessionUpdate: 'tool_call_update',
        ...update,
      } satisfies Protocol.ToolCallUpdate,
    } satisfies Protocol.SessionUpdateNotification)
  }
}
