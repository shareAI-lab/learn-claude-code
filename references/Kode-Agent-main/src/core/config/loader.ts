import { existsSync, readFileSync, writeFileSync } from 'fs'
import { join, posix, resolve, win32 } from 'path'
import { cloneDeep, memoize, pick } from 'lodash-es'
import { homedir } from 'os'
import { randomBytes } from 'crypto'
import { getGlobalConfigFilePath } from '@utils/config/env'
import { getCwd } from '@utils/state'
import { safeParseJSON } from '@utils/text/json'
import { ConfigParseError } from '@utils/text/errors'
import { debug as debugLogger } from '@utils/log/debugLogger'
import {
  DEFAULT_GLOBAL_CONFIG,
  DEFAULT_PROJECT_CONFIG,
  defaultConfigForProject,
} from './defaults'
import {
  GLOBAL_CONFIG_KEYS,
  PROJECT_CONFIG_KEYS,
  isGlobalConfigKey,
  isAutoUpdaterStatus,
  isProjectConfigKey,
  type GlobalConfig,
  type McpServerConfig,
  type ProjectConfig,
  type ProjectMcpServerDefinitions,
} from './schema'
import { migrateModelProfilesRemoveId } from './migrations'

function expandHomeDirForPlatform(
  input: string,
  homeDirPath: string,
  platform: NodeJS.Platform,
): string {
  const trimmed = input.trim()
  if (!trimmed) return trimmed
  if (trimmed === '~') return homeDirPath
  if (trimmed.startsWith('~/') || trimmed.startsWith('~\\')) {
    const rest = trimmed.slice(2)
    return platform === 'win32'
      ? win32.join(homeDirPath, rest)
      : posix.join(homeDirPath, rest)
  }
  return trimmed
}

export function normalizeProjectPathForComparison(
  projectPath: string,
  baseDir: string,
  opts?: { platform?: NodeJS.Platform; homeDir?: string },
): string {
  const platform = opts?.platform ?? process.platform
  const homeDirPath = opts?.homeDir ?? homedir()
  const expanded = expandHomeDirForPlatform(projectPath, homeDirPath, platform)
  if (!expanded) return ''

  if (platform === 'win32') {
    const resolved = win32.isAbsolute(expanded)
      ? win32.resolve(expanded)
      : win32.resolve(baseDir, expanded)
    return resolved.toLowerCase()
  }

  const resolved = posix.isAbsolute(expanded)
    ? posix.resolve(expanded)
    : posix.resolve(baseDir, expanded)
  return resolved
}

function findMatchingProjectKey(
  projects: Record<string, ProjectConfig> | undefined,
  absolutePath: string,
): string | undefined {
  if (!projects) return undefined
  if (projects[absolutePath]) return absolutePath

  const normalizedTarget = normalizeProjectPathForComparison(
    absolutePath,
    absolutePath,
  )

  for (const key of Object.keys(projects)) {
    if (
      normalizeProjectPathForComparison(key, absolutePath) === normalizedTarget
    ) {
      return key
    }
  }

  return undefined
}

export function checkHasTrustDialogAccepted(): boolean {
  let currentPath = getCwd()
  const config = getConfig(getGlobalConfigFilePath(), DEFAULT_GLOBAL_CONFIG)

  while (true) {
    const projectKey = findMatchingProjectKey(config.projects, currentPath)
    const projectConfig = projectKey ? config.projects?.[projectKey] : undefined
    if (projectConfig?.hasTrustDialogAccepted) {
      return true
    }
    const parentPath = resolve(currentPath, '..')
    if (parentPath === currentPath) {
      break
    }
    currentPath = parentPath
  }

  return false
}

const TEST_GLOBAL_CONFIG_FOR_TESTING: GlobalConfig = {
  ...DEFAULT_GLOBAL_CONFIG,
  autoUpdaterStatus: 'disabled',
}
const TEST_PROJECT_CONFIG_FOR_TESTING: ProjectConfig = {
  ...DEFAULT_PROJECT_CONFIG,
}

export function saveGlobalConfig(config: GlobalConfig): void {
  if (process.env.NODE_ENV === 'test') {
    for (const key in config) {
      TEST_GLOBAL_CONFIG_FOR_TESTING[key] = config[key]
    }
    return
  }

  saveConfig(
    getGlobalConfigFilePath(),
    {
      ...config,
      projects: getConfig(getGlobalConfigFilePath(), DEFAULT_GLOBAL_CONFIG)
        .projects,
    },
    DEFAULT_GLOBAL_CONFIG,
  )
}

export function getGlobalConfig(): GlobalConfig {
  if (process.env.NODE_ENV === 'test') {
    return TEST_GLOBAL_CONFIG_FOR_TESTING
  }
  const config = getConfig(getGlobalConfigFilePath(), DEFAULT_GLOBAL_CONFIG)
  return migrateModelProfilesRemoveId(config)
}

export function normalizeApiKeyForConfig(apiKey: string): string {
  return apiKey?.slice(-20) ?? ''
}

export function getCustomApiKeyStatus(
  truncatedApiKey: string,
): 'approved' | 'rejected' | 'new' {
  const config = getGlobalConfig()
  if (config.customApiKeyResponses?.approved?.includes(truncatedApiKey)) {
    return 'approved'
  }
  if (config.customApiKeyResponses?.rejected?.includes(truncatedApiKey)) {
    return 'rejected'
  }
  return 'new'
}

function saveConfig<A extends object>(
  file: string,
  config: A,
  defaultConfig: A,
): void {
  const filteredConfig = Object.fromEntries(
    Object.entries(config).filter(
      ([key, value]) =>
        JSON.stringify(value) !== JSON.stringify(defaultConfig[key as keyof A]),
    ),
  )
  try {
    writeFileSync(file, JSON.stringify(filteredConfig, null, 2), 'utf-8')
  } catch (error) {
    const err = error as NodeJS.ErrnoException
    if (
      err?.code === 'EACCES' ||
      err?.code === 'EPERM' ||
      err?.code === 'EROFS'
    ) {
      debugLogger.state('CONFIG_SAVE_SKIPPED', {
        file,
        reason: String(err.code),
      })
      return
    }
    throw error
  }
}

let configReadingAllowed = false

export function enableConfigs(): void {
  configReadingAllowed = true
  getConfig(
    getGlobalConfigFilePath(),
    DEFAULT_GLOBAL_CONFIG,
    true,
  )
}

function getConfig<A>(
  file: string,
  defaultConfig: A,
  throwOnInvalid?: boolean,
): A {
  void configReadingAllowed

  debugLogger.state('CONFIG_LOAD_START', {
    file,
    fileExists: String(existsSync(file)),
    throwOnInvalid: String(!!throwOnInvalid),
  })

  if (!existsSync(file)) {
    debugLogger.state('CONFIG_LOAD_DEFAULT', {
      file,
      reason: 'file_not_exists',
      defaultConfigKeys: Object.keys(defaultConfig as object).join(', '),
    })
    return cloneDeep(defaultConfig)
  }

  try {
    const fileContent = readFileSync(file, 'utf-8')
    debugLogger.state('CONFIG_FILE_READ', {
      file,
      contentLength: String(fileContent.length),
      contentPreview:
        fileContent.substring(0, 100) + (fileContent.length > 100 ? '...' : ''),
    })

    try {
      const parsedConfig = JSON.parse(fileContent)
      debugLogger.state('CONFIG_JSON_PARSED', {
        file,
        parsedKeys: Object.keys(parsedConfig).join(', '),
      })

      const finalConfig = {
        ...cloneDeep(defaultConfig),
        ...parsedConfig,
      }

      debugLogger.state('CONFIG_LOAD_SUCCESS', {
        file,
        finalConfigKeys: Object.keys(finalConfig as object).join(', '),
      })

      return finalConfig
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error)

      debugLogger.error('CONFIG_JSON_PARSE_ERROR', {
        file,
        errorMessage,
        errorType: error instanceof Error ? error.constructor.name : typeof error,
        contentLength: String(fileContent.length),
      })

      throw new ConfigParseError(errorMessage, file, defaultConfig)
    }
  } catch (error: unknown) {
    if (error instanceof ConfigParseError && throwOnInvalid) {
      debugLogger.error('CONFIG_PARSE_ERROR_RETHROWN', {
        file,
        throwOnInvalid: String(throwOnInvalid),
        errorMessage: error.message,
      })
      throw error
    }

    debugLogger.warn('CONFIG_FALLBACK_TO_DEFAULT', {
      file,
      errorType: error instanceof Error ? error.constructor.name : typeof error,
      errorMessage: error instanceof Error ? error.message : String(error),
      action: 'using_default_config',
    })

    return cloneDeep(defaultConfig)
  }
}

export function getCurrentProjectConfig(): ProjectConfig {
  if (process.env.NODE_ENV === 'test') {
    return TEST_PROJECT_CONFIG_FOR_TESTING
  }

  const absolutePath = resolve(getCwd())
  const config = getConfig(getGlobalConfigFilePath(), DEFAULT_GLOBAL_CONFIG)

  if (!config.projects) {
    return defaultConfigForProject(absolutePath)
  }

  const projectKey = findMatchingProjectKey(config.projects, absolutePath)
  const projectConfig =
    projectKey && config.projects[projectKey]
      ? config.projects[projectKey]
      : defaultConfigForProject(absolutePath)
  if (typeof projectConfig.allowedTools === 'string') {
    projectConfig.allowedTools =
      (safeParseJSON(projectConfig.allowedTools) as string[]) ?? []
  }
  if (typeof (projectConfig as any).deniedTools === 'string') {
    ;(projectConfig as any).deniedTools =
      (safeParseJSON((projectConfig as any).deniedTools) as string[]) ?? []
  }
  if (typeof (projectConfig as any).askedTools === 'string') {
    ;(projectConfig as any).askedTools =
      (safeParseJSON((projectConfig as any).askedTools) as string[]) ?? []
  }
  return projectConfig
}

export function saveCurrentProjectConfig(projectConfig: ProjectConfig): void {
  if (process.env.NODE_ENV === 'test') {
    for (const key in projectConfig) {
      TEST_PROJECT_CONFIG_FOR_TESTING[key] = projectConfig[key]
    }
    return
  }
  const config = getConfig(getGlobalConfigFilePath(), DEFAULT_GLOBAL_CONFIG)
  const resolvedCwd = resolve(getCwd())
  const existingKey = findMatchingProjectKey(config.projects, resolvedCwd)
  const storageKey = existingKey ?? resolvedCwd

  saveConfig(
    getGlobalConfigFilePath(),
    {
      ...config,
      projects: {
        ...config.projects,
        [storageKey]: projectConfig,
      },
    },
    DEFAULT_GLOBAL_CONFIG,
  )
}

export async function isAutoUpdaterDisabled(): Promise<boolean> {
  const status = getGlobalConfig().autoUpdaterStatus
  return status !== 'enabled'
}

export const TEST_MCPRC_CONFIG_FOR_TESTING: Record<string, McpServerConfig> = {}

export function clearMcprcConfigForTesting(): void {
  if (process.env.NODE_ENV === 'test') {
    Object.keys(TEST_MCPRC_CONFIG_FOR_TESTING).forEach(key => {
      delete TEST_MCPRC_CONFIG_FOR_TESTING[key]
    })
  }
}

export function addMcprcServerForTesting(
  name: string,
  server: McpServerConfig,
): void {
  if (process.env.NODE_ENV === 'test') {
    TEST_MCPRC_CONFIG_FOR_TESTING[name] = server
  }
}

export function removeMcprcServerForTesting(name: string): void {
  if (process.env.NODE_ENV === 'test') {
    if (!TEST_MCPRC_CONFIG_FOR_TESTING[name]) {
      throw new Error(`No MCP server found with name: ${name} in .mcprc`)
    }
    delete TEST_MCPRC_CONFIG_FOR_TESTING[name]
  }
}

export const getMcprcConfig = memoize(
  (): Record<string, McpServerConfig> => {
    if (process.env.NODE_ENV === 'test') {
      return TEST_MCPRC_CONFIG_FOR_TESTING
    }

    const mcprcPath = join(getCwd(), '.mcprc')
    if (!existsSync(mcprcPath)) {
      return {}
    }

    try {
      const mcprcContent = readFileSync(mcprcPath, 'utf-8')
      const config = safeParseJSON(mcprcContent)
      if (config && typeof config === 'object') {
        return config as Record<string, McpServerConfig>
      }
    } catch {}
    return {}
  },
  () => {
    const cwd = getCwd()
    const mcprcPath = join(cwd, '.mcprc')
    if (existsSync(mcprcPath)) {
      try {
        const stat = readFileSync(mcprcPath, 'utf-8')
        return `${cwd}:${stat}`
      } catch {
        return cwd
      }
    }
    return cwd
  },
)

function parseMcpServersFromMcpJson(
  value: unknown,
): Record<string, McpServerConfig> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  const raw = (value as { mcpServers?: unknown }).mcpServers
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  return raw as Record<string, McpServerConfig>
}

function parseMcpServersFromMcprc(
  value: unknown,
): Record<string, McpServerConfig> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  const maybeNested = (value as { mcpServers?: unknown }).mcpServers
  if (
    maybeNested &&
    typeof maybeNested === 'object' &&
    !Array.isArray(maybeNested)
  ) {
    return maybeNested as Record<string, McpServerConfig>
  }
  return value as Record<string, McpServerConfig>
}

export const getProjectMcpServerDefinitions = memoize(
  (): ProjectMcpServerDefinitions => {
    if (process.env.NODE_ENV === 'test') {
      return {
        servers: {},
        sources: {},
        mcpJsonPath: join(getCwd(), '.mcp.json'),
        mcprcPath: join(getCwd(), '.mcprc'),
      }
    }

    const cwd = getCwd()
    const mcpJsonPath = join(cwd, '.mcp.json')
    const mcprcPath = join(cwd, '.mcprc')

    let mcpJsonServers: Record<string, McpServerConfig> = {}
    let mcprcServers: Record<string, McpServerConfig> = {}

    if (existsSync(mcpJsonPath)) {
      try {
        const content = readFileSync(mcpJsonPath, 'utf-8')
        const parsed = safeParseJSON(content)
        mcpJsonServers = parseMcpServersFromMcpJson(parsed)
      } catch {}
    }

    if (existsSync(mcprcPath)) {
      try {
        const content = readFileSync(mcprcPath, 'utf-8')
        const parsed = safeParseJSON(content)
        mcprcServers = parseMcpServersFromMcprc(parsed)
      } catch {}
    }

    const sources: Record<string, '.mcp.json' | '.mcprc'> = {}
    for (const name of Object.keys(mcpJsonServers)) {
      sources[name] = '.mcp.json'
    }
    for (const name of Object.keys(mcprcServers)) {
      sources[name] = '.mcprc'
    }

    return {
      servers: { ...mcpJsonServers, ...mcprcServers },
      sources,
      mcpJsonPath,
      mcprcPath,
    }
  },
  () => {
    const cwd = getCwd()
    const mcpJsonPath = join(cwd, '.mcp.json')
    const mcprcPath = join(cwd, '.mcprc')

    const parts: string[] = [cwd]

    if (existsSync(mcpJsonPath)) {
      try {
        parts.push('mcp.json')
        parts.push(readFileSync(mcpJsonPath, 'utf-8'))
      } catch {}
    }

    if (existsSync(mcprcPath)) {
      try {
        parts.push('mcprc')
        parts.push(readFileSync(mcprcPath, 'utf-8'))
      } catch {}
    }

    return parts.join(':')
  },
)

export function getOrCreateUserID(): string {
  const config = getGlobalConfig()
  if (config.userID) {
    return config.userID
  }

  const userID = randomBytes(32).toString('hex')
  saveGlobalConfig({ ...config, userID })
  return userID
}

export function getConfigForCLI(key: string, global: boolean): unknown {
  if (global) {
    if (!isGlobalConfigKey(key)) {
      console.error(
        `Error: '${key}' is not a valid config key. Valid keys are: ${GLOBAL_CONFIG_KEYS.join(', ')}`,
      )
      process.exit(1)
    }
    return getGlobalConfig()[key]
  } else {
    if (!isProjectConfigKey(key)) {
      console.error(
        `Error: '${key}' is not a valid config key. Valid keys are: ${PROJECT_CONFIG_KEYS.join(', ')}`,
      )
      process.exit(1)
    }
    return getCurrentProjectConfig()[key]
  }
}

export function setConfigForCLI(
  key: string,
  value: unknown,
  global: boolean,
): void {
  if (global) {
    if (!isGlobalConfigKey(key)) {
      console.error(
        `Error: Cannot set '${key}'. Only these keys can be modified: ${GLOBAL_CONFIG_KEYS.join(', ')}`,
      )
      process.exit(1)
    }

    if (key === 'autoUpdaterStatus' && !isAutoUpdaterStatus(value as string)) {
      console.error(
        `Error: Invalid value for autoUpdaterStatus. Must be one of: disabled, enabled, no_permissions, not_configured`,
      )
      process.exit(1)
    }

    const currentConfig = getGlobalConfig()
    saveGlobalConfig({
      ...currentConfig,
      [key]: value,
    })
  } else {
    if (!isProjectConfigKey(key)) {
      console.error(
        `Error: Cannot set '${key}'. Only these keys can be modified: ${PROJECT_CONFIG_KEYS.join(', ')}. Did you mean --global?`,
      )
      process.exit(1)
    }
    const currentConfig = getCurrentProjectConfig()
    saveCurrentProjectConfig({
      ...currentConfig,
      [key]: value,
    })
  }
  setTimeout(() => {
    process.exit(0)
  }, 100)
}

export function deleteConfigForCLI(key: string, global: boolean): void {
  if (global) {
    if (!isGlobalConfigKey(key)) {
      console.error(
        `Error: Cannot delete '${key}'. Only these keys can be modified: ${GLOBAL_CONFIG_KEYS.join(', ')}`,
      )
      process.exit(1)
    }
    const currentConfig = getGlobalConfig()
    delete currentConfig[key]
    saveGlobalConfig(currentConfig)
  } else {
    if (!isProjectConfigKey(key)) {
      console.error(
        `Error: Cannot delete '${key}'. Only these keys can be modified: ${PROJECT_CONFIG_KEYS.join(', ')}. Did you mean --global?`,
      )
      process.exit(1)
    }
    const currentConfig = getCurrentProjectConfig()
    delete currentConfig[key]
    saveCurrentProjectConfig(currentConfig)
  }
}

export function listConfigForCLI(global: true): GlobalConfig
export function listConfigForCLI(global: false): ProjectConfig
export function listConfigForCLI(global: boolean): object {
  if (global) {
    const currentConfig = pick(getGlobalConfig(), GLOBAL_CONFIG_KEYS)
    return currentConfig
  } else {
    return pick(getCurrentProjectConfig(), PROJECT_CONFIG_KEYS)
  }
}

export function getOpenAIApiKey(): string | undefined {
  return process.env.OPENAI_API_KEY
}

export function getAnthropicApiKey(): string {
  return process.env.ANTHROPIC_API_KEY || ''
}
