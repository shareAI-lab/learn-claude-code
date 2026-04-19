import {
  existsSync,
  mkdirSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from 'fs'
import { join } from 'path'
import { homedir } from 'os'

import { getCwd } from '@utils/state'
import type { AgentConfig } from '@utils/agent/loader'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

import { generateAgentFileContent } from './generation'

export type AgentLocation = 'user' | 'project'

const PRIMARY_FOLDER = '.claude'
const LEGACY_FOLDER = '.kode'
const AGENTS_DIR = 'agents'

export function getAgentDirectory(location: AgentLocation): string {
  if (location === 'user') {
    return join(homedir(), PRIMARY_FOLDER, AGENTS_DIR)
  }
  return join(getCwd(), PRIMARY_FOLDER, AGENTS_DIR)
}

function getLegacyAgentDirectory(location: AgentLocation): string {
  if (location === 'user') {
    return join(homedir(), LEGACY_FOLDER, AGENTS_DIR)
  }
  return join(getCwd(), LEGACY_FOLDER, AGENTS_DIR)
}

export function getPrimaryAgentFilePath(
  location: AgentLocation,
  agentType: string,
): string {
  return join(getAgentDirectory(location), `${agentType}.md`)
}

function getLegacyAgentFilePath(
  location: AgentLocation,
  agentType: string,
): string {
  return join(getLegacyAgentDirectory(location), `${agentType}.md`)
}

export function getAgentFilePath(agent: AgentConfig): string {
  if (agent.location === 'built-in' || agent.location === 'plugin') {
    throw new Error(`Cannot get file path for ${agent.location} agents`)
  }

  const location = agent.location as AgentLocation
  const primary = getPrimaryAgentFilePath(location, agent.agentType)
  if (existsSync(primary)) return primary

  const legacy = getLegacyAgentFilePath(location, agent.agentType)
  if (existsSync(legacy)) return legacy

  return primary
}

export function ensureDirectoryExists(location: AgentLocation): string {
  const dir = getAgentDirectory(location)
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }
  return dir
}

export async function saveAgent(
  location: AgentLocation,
  agentType: string,
  description: string,
  tools: string[],
  systemPrompt: string,
  model?: string,
  color?: string,
  throwIfExists: boolean = true,
): Promise<void> {
  ensureDirectoryExists(location)

  const filePath = getPrimaryAgentFilePath(location, agentType)
  const legacyPath = getLegacyAgentFilePath(location, agentType)

  if (throwIfExists && (existsSync(filePath) || existsSync(legacyPath))) {
    throw new Error(`Agent file already exists: ${filePath}`)
  }

  const tempFile = `${filePath}.tmp.${Date.now()}.${Math.random()
    .toString(36)
    .substr(2, 9)}`

  const toolsForFile: string[] | '*' =
    Array.isArray(tools) && tools.length === 1 && tools[0] === '*' ? '*' : tools
  const content = generateAgentFileContent(
    agentType,
    description,
    toolsForFile,
    systemPrompt,
    model,
    color,
  )

  try {
    writeFileSync(tempFile, content, { encoding: 'utf-8', flag: 'wx' })

    if (throwIfExists && (existsSync(filePath) || existsSync(legacyPath))) {
      try {
        unlinkSync(tempFile)
      } catch {}
      throw new Error(`Agent file already exists: ${filePath}`)
    }

    renameSync(tempFile, filePath)
  } catch (error) {
    try {
      if (existsSync(tempFile)) {
        unlinkSync(tempFile)
      }
    } catch (cleanupError) {
      logError(cleanupError)
      debugLogger.warn('AGENT_STORAGE_TEMP_CLEANUP_FAILED', {
        error: cleanupError instanceof Error ? cleanupError.message : String(cleanupError),
      })
    }
    throw error
  }
}

export async function updateAgent(
  agent: AgentConfig,
  description: string,
  tools: string[] | '*',
  systemPrompt: string,
  color?: string,
  model?: string,
): Promise<void> {
  if (agent.location === 'built-in' || agent.location === 'plugin') {
    throw new Error(`Cannot update ${agent.location} agents`)
  }

  const toolsForFile = tools.length === 1 && tools[0] === '*' ? '*' : tools
  const content = generateAgentFileContent(
    agent.agentType,
    description,
    toolsForFile,
    systemPrompt,
    model,
    color,
  )

  const location = agent.location as AgentLocation
  const primaryPath = getPrimaryAgentFilePath(location, agent.agentType)
  const legacyPath = getLegacyAgentFilePath(location, agent.agentType)
  const filePath = existsSync(primaryPath)
    ? primaryPath
    : existsSync(legacyPath)
      ? legacyPath
      : primaryPath

  ensureDirectoryExists(location)
  writeFileSync(filePath, content, { encoding: 'utf-8', flag: 'w' })
}

export async function deleteAgent(agent: AgentConfig): Promise<void> {
  if (agent.location === 'built-in' || agent.location === 'plugin') {
    throw new Error(`Cannot delete ${agent.location} agents`)
  }

  const location = agent.location as AgentLocation
  const primaryPath = getPrimaryAgentFilePath(location, agent.agentType)
  const legacyPath = getLegacyAgentFilePath(location, agent.agentType)

  if (existsSync(primaryPath)) {
    unlinkSync(primaryPath)
  }
  if (existsSync(legacyPath)) {
    unlinkSync(legacyPath)
  }
}
