import { homedir } from 'os'
import type { GlobalConfig, ProjectConfig, ProviderType } from './schema'
import type { ThemeNames } from '@utils/theme'

export const DEFAULT_PROJECT_CONFIG: ProjectConfig = {
  allowedTools: [],
  deniedTools: [],
  askedTools: [],
  context: {},
  history: [],
  dontCrawlDirectory: false,
  enableArchitectTool: false,
  mcpContextUris: [],
  mcpServers: {},
  approvedMcprcServers: [],
  rejectedMcprcServers: [],
  hasTrustDialogAccepted: false,
}

export function defaultConfigForProject(projectPath: string): ProjectConfig {
  const config = { ...DEFAULT_PROJECT_CONFIG }
  if (projectPath === homedir()) {
    config.dontCrawlDirectory = true
  }
  return config
}

export const DEFAULT_GLOBAL_CONFIG: GlobalConfig = {
  numStartups: 0,
  autoUpdaterStatus: 'not_configured',
  theme: 'dark' as ThemeNames,
  preferredNotifChannel: 'iterm2',
  verbose: false,
  primaryProvider: 'anthropic' as ProviderType,
  customApiKeyResponses: {
    approved: [],
    rejected: [],
  },
  stream: true,

  modelProfiles: [],
  modelPointers: {
    main: '',
    task: '',
    compact: '',
    quick: '',
  },
  lastDismissedUpdateVersion: undefined,
}

