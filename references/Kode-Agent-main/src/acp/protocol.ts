export const ACP_PROTOCOL_VERSION = 1

export type JsonObject = Record<string, unknown>

export type Implementation = {
  name: string
  title?: string | null
  version: string
  _meta?: JsonObject | null
}

export type FileSystemCapability = {
  readTextFile?: boolean
  writeTextFile?: boolean
  _meta?: JsonObject | null
}

export type ClientCapabilities = {
  fs?: FileSystemCapability
  terminal?: boolean
  _meta?: JsonObject | null
}

export type PromptCapabilities = {
  audio?: boolean
  image?: boolean
  embeddedContext?: boolean
  embeddedContent?: boolean
  _meta?: JsonObject | null
}

export type McpCapabilities = {
  http?: boolean
  sse?: boolean
  _meta?: JsonObject | null
}

export type AgentCapabilities = {
  loadSession?: boolean
  promptCapabilities?: PromptCapabilities
  mcpCapabilities?: McpCapabilities
  sessionCapabilities?: JsonObject
  _meta?: JsonObject | null
}

export type AuthMethod = {
  id: string
  name: string
  description?: string | null
  _meta?: JsonObject | null
}

export type InitializeParams = {
  protocolVersion: number
  clientCapabilities?: ClientCapabilities
  clientInfo?: Implementation | null
  _meta?: JsonObject | null
}

export type InitializeResponse = {
  protocolVersion: number
  agentCapabilities: AgentCapabilities
  agentInfo?: Implementation | null
  authMethods?: AuthMethod[]
  _meta?: JsonObject | null
}

export type AuthenticateParams = {
  methodId: string
  _meta?: JsonObject | null
}

export type AuthenticateResponse = JsonObject

export type EnvVariable = {
  name: string
  value: string
  _meta?: JsonObject | null
}

export type HttpHeader = {
  name: string
  value: string
  _meta?: JsonObject | null
}

export type McpServerStdio = {
  type?: 'stdio'
  name: string
  command: string
  args: string[]
  env: EnvVariable[]
  _meta?: JsonObject | null
}

export type McpServerHttp = {
  type: 'http'
  name: string
  url: string
  headers: HttpHeader[]
  _meta?: JsonObject | null
}

export type McpServerSse = {
  type: 'sse'
  name: string
  url: string
  headers: HttpHeader[]
  _meta?: JsonObject | null
}

export type McpServer = McpServerStdio | McpServerHttp | McpServerSse

export type SessionModeId = string

export type SessionMode = {
  id: SessionModeId
  name: string
  description?: string | null
  _meta?: JsonObject | null
}

export type SessionModeState = {
  currentModeId: SessionModeId
  availableModes: SessionMode[]
  _meta?: JsonObject | null
}

export type NewSessionParams = {
  cwd: string
  mcpServers: McpServer[]
  _meta?: JsonObject | null
}

export type NewSessionResponse = {
  sessionId: string
  modes?: SessionModeState | null
  _meta?: JsonObject | null
}

export type LoadSessionParams = {
  sessionId: string
  cwd: string
  mcpServers: McpServer[]
  _meta?: JsonObject | null
}

export type LoadSessionResponse = {
  modes?: SessionModeState | null
  _meta?: JsonObject | null
}

export type StopReason =
  | 'end_turn'
  | 'max_tokens'
  | 'max_turn_requests'
  | 'refusal'
  | 'cancelled'

export type PromptResponse = {
  stopReason: StopReason
  _meta?: JsonObject | null
}

export type SessionCancelParams = {
  sessionId: string
  _meta?: JsonObject | null
}

export type SetSessionModeParams = {
  sessionId: string
  modeId: SessionModeId
  _meta?: JsonObject | null
}

export type SetSessionModeResponse = JsonObject

export type TextContent = {
  type: 'text'
  text: string
  annotations?: JsonObject | null
  _meta?: JsonObject | null
}

export type ImageContent = {
  type: 'image'
  data?: string
  mimeType?: string
  url?: string
  annotations?: JsonObject | null
  _meta?: JsonObject | null
}

export type AudioContent = {
  type: 'audio'
  data: string
  mimeType: string
  annotations?: JsonObject | null
  _meta?: JsonObject | null
}

export type EmbeddedResource = {
  uri: string
  mimeType?: string | null
  text?: string
  blob?: string
  _meta?: JsonObject | null
}

export type EmbeddedResourceContent = {
  type: 'resource'
  resource: EmbeddedResource
  annotations?: JsonObject | null
  _meta?: JsonObject | null
}

export type ResourceLinkContent = {
  type: 'resource_link'
  uri: string
  name: string
  title?: string | null
  description?: string | null
  mimeType?: string | null
  size?: number | null
  annotations?: JsonObject | null
  _meta?: JsonObject | null
}

export type ContentBlock =
  | TextContent
  | ImageContent
  | AudioContent
  | EmbeddedResourceContent
  | ResourceLinkContent

export type PromptParams = {
  sessionId: string
  prompt: ContentBlock[]
  _meta?: JsonObject | null
}

export type SessionUpdateKind =
  | 'user_message_chunk'
  | 'agent_message_chunk'
  | 'agent_thought_chunk'
  | 'tool_call'
  | 'tool_call_update'
  | 'plan'
  | 'available_commands_update'
  | 'current_mode_update'

export type PlanEntryPriority = 'high' | 'medium' | 'low'

export type PlanEntryStatus = 'pending' | 'in_progress' | 'completed'

export type PlanEntry = {
  content: string
  priority: PlanEntryPriority
  status: PlanEntryStatus
  _meta?: JsonObject | null
}

export type PlanUpdate = {
  sessionUpdate: 'plan'
  entries: PlanEntry[]
  _meta?: JsonObject | null
}

export type ToolKind =
  | 'read'
  | 'edit'
  | 'delete'
  | 'move'
  | 'search'
  | 'execute'
  | 'think'
  | 'fetch'
  | 'switch_mode'
  | 'other'

export type ToolCallStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

export type ToolCallLocation = {
  path: string
  line?: number | null
  _meta?: JsonObject | null
}

export type ToolCallContent =
  | { type: 'content'; content: ContentBlock; _meta?: JsonObject | null }
  | {
      type: 'diff'
      path: string
      newText: string
      oldText?: string | null
      _meta?: JsonObject | null
    }
  | { type: 'terminal'; terminalId: string; _meta?: JsonObject | null }

export type ToolCall = {
  sessionUpdate: 'tool_call'
  toolCallId: string
  title: string
  kind?: ToolKind
  status?: ToolCallStatus
  content?: ToolCallContent[]
  locations?: ToolCallLocation[]
  rawInput?: JsonObject
  rawOutput?: JsonObject
  _meta?: JsonObject | null
}

export type ToolCallUpdate = {
  sessionUpdate: 'tool_call_update'
  toolCallId: string
  title?: string | null
  kind?: ToolKind | null
  status?: ToolCallStatus | null
  content?: ToolCallContent[] | null
  locations?: ToolCallLocation[] | null
  rawInput?: JsonObject
  rawOutput?: JsonObject
  _meta?: JsonObject | null
}

export type ToolCallUpdatePermissionRequest = Omit<ToolCallUpdate, 'sessionUpdate'>

export type PermissionOptionKind =
  | 'allow_once'
  | 'allow_always'
  | 'reject_once'
  | 'reject_always'

export type PermissionOption = {
  optionId: string
  name: string
  kind: PermissionOptionKind
  _meta?: JsonObject | null
}

export type OutcomeCancelled = { outcome: 'cancelled'; _meta?: JsonObject | null }
export type OutcomeSelected = {
  outcome: 'selected'
  optionId: string
  _meta?: JsonObject | null
}
export type RequestPermissionOutcome = OutcomeCancelled | OutcomeSelected

export type RequestPermissionParams = {
  sessionId: string
  toolCall: ToolCallUpdatePermissionRequest
  options: PermissionOption[]
  _meta?: JsonObject | null
}

export type RequestPermissionResponse = {
  outcome: RequestPermissionOutcome
  _meta?: JsonObject | null
}

export type AvailableCommandInput = { hint: string; _meta?: JsonObject | null }
export type AvailableCommand = {
  name: string
  description: string
  input?: AvailableCommandInput | null
  _meta?: JsonObject | null
}

export type AvailableCommandsUpdate = {
  sessionUpdate: 'available_commands_update'
  availableCommands: AvailableCommand[]
  _meta?: JsonObject | null
}

export type CurrentModeUpdate = {
  sessionUpdate: 'current_mode_update'
  currentModeId: SessionModeId
  _meta?: JsonObject | null
}

export type UserMessageChunk = {
  sessionUpdate: 'user_message_chunk'
  content: ContentBlock
  _meta?: JsonObject | null
}

export type AgentMessageChunk = {
  sessionUpdate: 'agent_message_chunk'
  content: ContentBlock
  _meta?: JsonObject | null
}

export type AgentThoughtChunk = {
  sessionUpdate: 'agent_thought_chunk'
  content: ContentBlock
  _meta?: JsonObject | null
}

export type SessionUpdate =
  | UserMessageChunk
  | AgentMessageChunk
  | AgentThoughtChunk
  | ToolCall
  | ToolCallUpdate
  | PlanUpdate
  | AvailableCommandsUpdate
  | CurrentModeUpdate

export type SessionUpdateNotification = {
  sessionId: string
  update: SessionUpdate
  _meta?: JsonObject | null
}
