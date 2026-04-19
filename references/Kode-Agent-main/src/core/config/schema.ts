import type { ThemeNames } from '@utils/theme'

export type McpStdioServerConfig = {
  type?: 'stdio'
  command: string
  args: string[]
  env?: Record<string, string>
}

export type McpSSEServerConfig = {
  type: 'sse'
  url: string
  headers?: Record<string, string>
  headersHelper?: string
}

export type McpHttpServerConfig = {
  type: 'http'
  url: string
  headers?: Record<string, string>
  headersHelper?: string
}

export type McpSSEIdeServerConfig = {
  type: 'sse-ide'
  url: string
  ideName: string
  ideRunningInWindows?: boolean
  headers?: Record<string, string>
  headersHelper?: string
}

export type McpWsServerConfig = {
  type: 'ws'
  url: string
}

export type McpWsIdeServerConfig = {
  type: 'ws-ide'
  url: string
  ideName: string
  authToken?: string
  ideRunningInWindows?: boolean
}

export type McpServerConfig =
  | McpStdioServerConfig
  | McpSSEServerConfig
  | McpHttpServerConfig
  | McpSSEIdeServerConfig
  | McpWsServerConfig
  | McpWsIdeServerConfig

export type ProjectConfig = {
  allowedTools: string[]
  deniedTools?: string[]
  askedTools?: string[]
  context: Record<string, string>
  contextFiles?: string[]
  history: string[]
  dontCrawlDirectory?: boolean
  enableArchitectTool?: boolean
  mcpContextUris: string[]
  mcpServers?: Record<string, McpServerConfig>
  approvedMcprcServers?: string[]
  rejectedMcprcServers?: string[]
  lastAPIDuration?: number
  lastCost?: number
  lastDuration?: number
  lastSessionId?: string
  exampleFiles?: string[]
  exampleFilesGeneratedAt?: number
  hasTrustDialogAccepted?: boolean
  hasCompletedProjectOnboarding?: boolean
}

export type AutoUpdaterStatus =
  | 'disabled'
  | 'enabled'
  | 'no_permissions'
  | 'not_configured'

export function isAutoUpdaterStatus(value: string): value is AutoUpdaterStatus {
  return ['disabled', 'enabled', 'no_permissions', 'not_configured'].includes(
    value as AutoUpdaterStatus,
  )
}

export type NotificationChannel =
  | 'iterm2'
  | 'terminal_bell'
  | 'iterm2_with_bell'
  | 'notifications_disabled'

export type ProviderType =
  | 'anthropic'
  | 'openai'
  | 'mistral'
  | 'deepseek'
  | 'kimi'
  | 'qwen'
  | 'glm'
  | 'minimax'
  | 'baidu-qianfan'
  | 'siliconflow'
  | 'bigdream'
  | 'opendev'
  | 'xai'
  | 'groq'
  | 'gemini'
  | 'ollama'
  | 'azure'
  | 'custom'
  | 'custom-openai'
  | (string & {})

export type ModelProfile = {
  name: string
  provider: ProviderType
  modelName: string
  baseURL?: string
  apiKey: string
  maxTokens: number
  contextLength: number
  reasoningEffort?: 'low' | 'medium' | 'high' | 'minimal' | string
  isActive: boolean
  createdAt: number
  lastUsed?: number
  isGPT5?: boolean
  validationStatus?: 'valid' | 'needs_repair' | 'auto_repaired'
  lastValidation?: number
}

export type ModelPointerType = 'main' | 'task' | 'compact' | 'quick'

export type ModelPointers = {
  main: string
  task: string
  compact: string
  quick: string
}

export type AccountInfo = {
  accountUuid: string
  emailAddress: string
  organizationUuid?: string
}

export type GlobalConfig = {
  projects?: Record<string, ProjectConfig>
  numStartups: number
  autoUpdaterStatus?: AutoUpdaterStatus
  userID?: string
  theme: ThemeNames
  hasCompletedOnboarding?: boolean
  lastPlanModeUse?: number
  lastOnboardingVersion?: string
  lastReleaseNotesSeen?: string
  mcpServers?: Record<string, McpServerConfig>
  preferredNotifChannel: NotificationChannel
  verbose: boolean
  customApiKeyResponses?: {
    approved?: string[]
    rejected?: string[]
  }
  primaryProvider?: ProviderType
  maxTokens?: number
  autoCompactThreshold?: number
  hasAcknowledgedCostThreshold?: boolean
  oauthAccount?: AccountInfo
  proxy?: string
  stream?: boolean

  modelProfiles?: ModelProfile[]
  modelPointers?: ModelPointers
  defaultModelName?: string
  lastDismissedUpdateVersion?: string
}

export const GLOBAL_CONFIG_KEYS = [
  'autoUpdaterStatus',
  'theme',
  'hasCompletedOnboarding',
  'lastOnboardingVersion',
  'lastReleaseNotesSeen',
  'verbose',
  'customApiKeyResponses',
  'primaryProvider',
  'preferredNotifChannel',
  'maxTokens',
  'autoCompactThreshold',
] as const

export type GlobalConfigKey = (typeof GLOBAL_CONFIG_KEYS)[number]

export function isGlobalConfigKey(key: string): key is GlobalConfigKey {
  return GLOBAL_CONFIG_KEYS.includes(key as GlobalConfigKey)
}

export const PROJECT_CONFIG_KEYS = [
  'dontCrawlDirectory',
  'enableArchitectTool',
  'hasTrustDialogAccepted',
  'hasCompletedProjectOnboarding',
] as const

export type ProjectConfigKey = (typeof PROJECT_CONFIG_KEYS)[number]

export function isProjectConfigKey(key: string): key is ProjectConfigKey {
  return PROJECT_CONFIG_KEYS.includes(key as ProjectConfigKey)
}

export type ProjectMcpServerDefinitions = {
  servers: Record<string, McpServerConfig>
  sources: Record<string, '.mcp.json' | '.mcprc'>
  mcpJsonPath: string
  mcprcPath: string
}
