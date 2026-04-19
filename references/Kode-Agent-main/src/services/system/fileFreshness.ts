import { statSync, existsSync, watchFile, unwatchFile } from 'fs'
import {
  emitReminderEvent,
  systemReminderService,
} from '@services/systemReminder'
import { getAgentFilePath } from '@utils/agent/storage'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

interface FileTimestamp {
  path: string
  lastRead: number
  lastModified: number
  size: number
  lastAgentEdit?: number
}

interface FileFreshnessState {
  readTimestamps: Map<string, FileTimestamp>
  editConflicts: Set<string>
  sessionFiles: Set<string>
  watchedTodoFiles: Map<string, string>
}

class FileFreshnessService {
  private state: FileFreshnessState = {
    readTimestamps: new Map(),
    editConflicts: new Set(),
    sessionFiles: new Set(),
    watchedTodoFiles: new Map(),
  }

  constructor() {
    this.setupEventListeners()
  }

  private setupEventListeners(): void {
    systemReminderService.addEventListener(
      'session:startup',
      (context: any) => {
        this.resetSession()
      },
    )
  }

  public recordFileRead(filePath: string): void {
    try {
      if (!existsSync(filePath)) {
        return
      }

      const stats = statSync(filePath)
      const timestamp: FileTimestamp = {
        path: filePath,
        lastRead: Date.now(),
        lastModified: stats.mtimeMs,
        size: stats.size,
      }

      this.state.readTimestamps.set(filePath, timestamp)
      this.state.sessionFiles.add(filePath)

      emitReminderEvent('file:read', {
        filePath,
        timestamp: timestamp.lastRead,
        size: timestamp.size,
        modified: timestamp.lastModified,
      })
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_FRESHNESS_RECORD_READ_FAILED', {
        filePath,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  public checkFileFreshness(filePath: string): {
    isFresh: boolean
    lastRead?: number
    currentModified?: number
    conflict: boolean
  } {
    const recorded = this.state.readTimestamps.get(filePath)

    if (!recorded) {
      return { isFresh: true, conflict: false }
    }

    try {
      if (!existsSync(filePath)) {
        return { isFresh: false, conflict: true }
      }

      const currentStats = statSync(filePath)
      const isFresh = currentStats.mtimeMs <= recorded.lastModified
      const conflict = !isFresh

      if (conflict) {
        this.state.editConflicts.add(filePath)

        emitReminderEvent('file:conflict', {
          filePath,
          lastRead: recorded.lastRead,
          lastModified: recorded.lastModified,
          currentModified: currentStats.mtimeMs,
          sizeDiff: currentStats.size - recorded.size,
        })
      }

      return {
        isFresh,
        lastRead: recorded.lastRead,
        currentModified: currentStats.mtimeMs,
        conflict,
      }
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_FRESHNESS_CHECK_FAILED', {
        filePath,
        error: error instanceof Error ? error.message : String(error),
      })
      return { isFresh: false, conflict: true }
    }
  }

  public recordFileEdit(filePath: string, content?: string): void {
    try {
      const now = Date.now()

      if (existsSync(filePath)) {
        const stats = statSync(filePath)
        const existing = this.state.readTimestamps.get(filePath)

        if (existing) {
          existing.lastModified = stats.mtimeMs
          existing.size = stats.size
          existing.lastAgentEdit = now
          this.state.readTimestamps.set(filePath, existing)
        } else {
          const timestamp: FileTimestamp = {
            path: filePath,
            lastRead: now,
            lastModified: stats.mtimeMs,
            size: stats.size,
            lastAgentEdit: now,
          }
          this.state.readTimestamps.set(filePath, timestamp)
        }
      }

      this.state.editConflicts.delete(filePath)

      emitReminderEvent('file:edited', {
        filePath,
        timestamp: now,
        contentLength: content?.length || 0,
        source: 'agent',
      })
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_FRESHNESS_RECORD_EDIT_FAILED', {
        filePath,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  public generateFileModificationReminder(filePath: string): string | null {
    const recorded = this.state.readTimestamps.get(filePath)

    if (!recorded) {
      return null
    }

    try {
      if (!existsSync(filePath)) {
        return `Note: ${filePath} was deleted since last read.`
      }

      const currentStats = statSync(filePath)
      const isModified = currentStats.mtimeMs > recorded.lastModified

      if (!isModified) {
        return null
      }

      const TIME_TOLERANCE_MS = 100
      if (
        recorded.lastAgentEdit &&
        recorded.lastAgentEdit >= recorded.lastModified - TIME_TOLERANCE_MS
      ) {
        return null
      }

      return `Note: ${filePath} was modified externally since last read. The file may have changed outside of this session.`
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_FRESHNESS_CHECK_MODIFICATION_FAILED', {
        filePath,
        error: error instanceof Error ? error.message : String(error),
      })
      return null
    }
  }

  public getConflictedFiles(): string[] {
    return Array.from(this.state.editConflicts)
  }

  public getSessionFiles(): string[] {
    return Array.from(this.state.sessionFiles)
  }

  public resetSession(): void {
    this.state.watchedTodoFiles.forEach(filePath => {
      try {
        unwatchFile(filePath)
      } catch (error) {
        logError(error)
        debugLogger.warn('FILE_FRESHNESS_UNWATCH_FAILED', {
          filePath,
          error: error instanceof Error ? error.message : String(error),
        })
      }
    })

    this.state = {
      readTimestamps: new Map(),
      editConflicts: new Set(),
      sessionFiles: new Set(),
      watchedTodoFiles: new Map(),
    }
  }

  public startWatchingTodoFile(agentId: string): void {
    try {
      const filePath = getAgentFilePath(agentId)

      if (this.state.watchedTodoFiles.has(agentId)) {
        return
      }

      this.state.watchedTodoFiles.set(agentId, filePath)

      if (existsSync(filePath)) {
        this.recordFileRead(filePath)
      }

      watchFile(filePath, { interval: 1000 }, (curr, prev) => {
        const reminder = this.generateFileModificationReminder(filePath)
        if (reminder) {
          emitReminderEvent('todo:file_changed', {
            agentId,
            filePath,
            reminder,
            timestamp: Date.now(),
            currentStats: { mtime: curr.mtime, size: curr.size },
            previousStats: { mtime: prev.mtime, size: prev.size },
          })
        }
      })
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_FRESHNESS_TODO_WATCH_START_FAILED', {
        agentId,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  public stopWatchingTodoFile(agentId: string): void {
    try {
      const filePath = this.state.watchedTodoFiles.get(agentId)
      if (filePath) {
        unwatchFile(filePath)
        this.state.watchedTodoFiles.delete(agentId)
      }
    } catch (error) {
      logError(error)
      debugLogger.warn('FILE_FRESHNESS_TODO_WATCH_STOP_FAILED', {
        agentId,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  public getFileInfo(filePath: string): FileTimestamp | null {
    return this.state.readTimestamps.get(filePath) || null
  }

  public isFileTracked(filePath: string): boolean {
    return this.state.readTimestamps.has(filePath)
  }

  public getImportantFiles(maxFiles: number = 5): Array<{
    path: string
    timestamp: number
    size: number
  }> {
    return Array.from(this.state.readTimestamps.entries())
      .map(([path, info]) => ({
        path,
        timestamp: info.lastRead,
        size: info.size,
      }))
      .filter(file => this.isValidForRecovery(file.path))
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, maxFiles)
  }

  private isValidForRecovery(filePath: string): boolean {
    return (
      !filePath.includes('node_modules') &&
      !filePath.includes('.git') &&
      !filePath.startsWith('/tmp') &&
      !filePath.includes('.cache') &&
      !filePath.includes('dist/') &&
      !filePath.includes('build/')
    )
  }
}

export const fileFreshnessService = new FileFreshnessService()

export const recordFileRead = (filePath: string) =>
  fileFreshnessService.recordFileRead(filePath)
export const recordFileEdit = (filePath: string, content?: string) =>
  fileFreshnessService.recordFileEdit(filePath, content)
export const checkFileFreshness = (filePath: string) =>
  fileFreshnessService.checkFileFreshness(filePath)
export const generateFileModificationReminder = (filePath: string) =>
  fileFreshnessService.generateFileModificationReminder(filePath)
export const resetFileFreshnessSession = () =>
  fileFreshnessService.resetSession()
export const startWatchingTodoFile = (agentId: string) =>
  fileFreshnessService.startWatchingTodoFile(agentId)
export const stopWatchingTodoFile = (agentId: string) =>
  fileFreshnessService.stopWatchingTodoFile(agentId)
