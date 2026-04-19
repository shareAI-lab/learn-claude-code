import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'
import { randomUUID } from 'crypto'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'


function getConfigDirectory(): string {
  return (
    process.env.KODE_CONFIG_DIR ??
    process.env.ANYKODE_CONFIG_DIR ??
    join(homedir(), '.kode')
  )
}

function getSessionId(): string {
  return process.env.ANYKODE_SESSION_ID ?? 'default-session'
}

export function getAgentFilePath(agentId: string): string {
  const sessionId = getSessionId()
  const filename = `${sessionId}-agent-${agentId}.json`
  const configDir = getConfigDirectory()

  if (!existsSync(configDir)) {
    mkdirSync(configDir, { recursive: true })
  }

  return join(configDir, filename)
}

export function readAgentData<T = any>(agentId: string): T | null {
  const filePath = getAgentFilePath(agentId)

  if (!existsSync(filePath)) {
    return null
  }

  try {
    const content = readFileSync(filePath, 'utf-8')
    return JSON.parse(content) as T
  } catch (error) {
    logError(error)
    debugLogger.warn('AGENT_STORAGE_READ_FAILED', {
      agentId,
      error: error instanceof Error ? error.message : String(error),
    })
    return null
  }
}

export function writeAgentData<T = any>(agentId: string, data: T): void {
  const filePath = getAgentFilePath(agentId)

  try {
    writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8')
  } catch (error) {
    logError(error)
    debugLogger.warn('AGENT_STORAGE_WRITE_FAILED', {
      agentId,
      error: error instanceof Error ? error.message : String(error),
    })
    throw error
  }
}

export function getDefaultAgentId(): string {
  return 'default'
}

export function resolveAgentId(agentId?: string): string {
  return agentId || getDefaultAgentId()
}

export function generateAgentId(): string {
  return randomUUID()
}
