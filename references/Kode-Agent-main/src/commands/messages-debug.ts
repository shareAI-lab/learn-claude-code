import type { Command } from '@commands'
import { getMessagesGetter } from '@messages'
import type { ProgressMessage } from '@query'
import {
  extractTag,
  getInProgressToolUseIDs,
  getToolUseID,
  getUnresolvedToolUseIDs,
  isNotEmptyMessage,
  normalizeMessages,
  reorderMessages,
  type NormalizedMessage,
} from '@utils/messages'
import { getReplStaticPrefixLength } from '@utils/terminal/replStaticSplit'
import { CACHE_PATHS } from '@utils/log'
import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { join } from 'path'

function isDebugMode(): boolean {
  return (
    process.argv.includes('--debug') || process.argv.includes('--debug-verbose')
  )
}

function safeStringify(value: unknown): string {
  const seen = new WeakSet<object>()
  return JSON.stringify(
    value,
    (_key, val) => {
      if (typeof val === 'function') return '[Function]'
      if (typeof val === 'bigint') return val.toString()
      if (val && typeof val === 'object') {
        if (seen.has(val)) return '[Circular]'
        seen.add(val)
      }
      return val
    },
    2,
  )
}

function getProgressText(message: ProgressMessage): string {
  const first = message.content.message.content[0]
  if (!first || first.type !== 'text') return ''
  const rawText = String(first.text ?? '')
  if (rawText.startsWith('<tool-progress>')) {
    return extractTag(rawText, 'tool-progress') ?? rawText
  }
  return rawText
}

function getLatestMessagesLogFile(): { path: string; mtimeMs: number } | null {
  const dir = CACHE_PATHS.messages()
  if (!existsSync(dir)) return null
  const files = readdirSync(dir).filter(f => f.endsWith('.json'))
  if (files.length === 0) return null

  let best: { path: string; mtimeMs: number } | null = null
  for (const file of files) {
    const fullPath = join(dir, file)
    let mtimeMs = 0
    try {
      mtimeMs = statSync(fullPath).mtimeMs
    } catch {
      continue
    }
    if (!best || mtimeMs > best.mtimeMs) {
      best = { path: fullPath, mtimeMs }
    }
  }
  return best
}

type ToolUseSummary = {
  toolUseID: string
  toolName: string | null
  occurrencesInNormalized: number
  progressMessagesInNormalized: number
  progressReplacements: number
  sawQueuedWaiting: boolean
}

function summarizeToolUses(normalized: NormalizedMessage[]): {
  toolUseIDs: string[]
  duplicates: string[]
  byID: ToolUseSummary[]
} {
  const toolUseNameById = new Map<string, string>()
  const toolUseCounts = new Map<string, number>()

  const progressCounts = new Map<string, number>()
  const sawQueuedWaiting = new Set<string>()

  for (const message of normalized) {
    const toolUseID = getToolUseID(message)
    if (toolUseID) {
      toolUseCounts.set(toolUseID, (toolUseCounts.get(toolUseID) ?? 0) + 1)
      if (message.type === 'assistant') {
        const first = message.message.content[0] as any
        if (first?.type === 'tool_use' && typeof first.name === 'string') {
          toolUseNameById.set(toolUseID, first.name)
        }
      }
    }

    if (message.type === 'progress') {
      progressCounts.set(
        message.toolUseID,
        (progressCounts.get(message.toolUseID) ?? 0) + 1,
      )
      if (getProgressText(message).trim() === 'Waiting…') {
        sawQueuedWaiting.add(message.toolUseID)
      }
    }
  }

  const toolUseIDs = [...toolUseCounts.keys()]
  toolUseIDs.sort()

  const duplicates = toolUseIDs.filter(id => (toolUseCounts.get(id) ?? 0) > 1)

  const byID: ToolUseSummary[] = toolUseIDs.map(toolUseID => {
    const occurrencesInNormalized = toolUseCounts.get(toolUseID) ?? 0
    const progressMessagesInNormalized = progressCounts.get(toolUseID) ?? 0
    return {
      toolUseID,
      toolName: toolUseNameById.get(toolUseID) ?? null,
      occurrencesInNormalized,
      progressMessagesInNormalized,
      progressReplacements: Math.max(0, progressMessagesInNormalized - 1),
      sawQueuedWaiting: sawQueuedWaiting.has(toolUseID),
    }
  })

  return { toolUseIDs, duplicates, byID }
}

function summarizeOrderedMessages(ordered: NormalizedMessage[]): Array<{
  index: number
  uuid: string
  type: NormalizedMessage['type']
  toolUseID: string | null
  preview: string | null
}> {
  return ordered.map((m, index) => {
    let preview: string | null = null
    if (m.type === 'progress') {
      preview = getProgressText(m).trim() || null
    } else if (m.type === 'assistant') {
      const first = m.message.content[0] as any
      if (first?.type === 'text')
        preview = String(first.text ?? '').slice(0, 120)
      if (first?.type === 'tool_use') {
        const name = typeof first.name === 'string' ? first.name : 'UnknownTool'
        preview = `${name}(${safeStringify(first.input ?? {}).slice(0, 120)})`
      }
    } else if (m.type === 'user') {
      const content = (m as any).message.content as unknown
      if (Array.isArray(content)) {
        const first = content[0] as any
        if (first?.type === 'tool_result') {
          preview = `tool_result(${String(first.tool_use_id ?? '')})`
        } else if (first?.type === 'text') {
          preview = String(first.text ?? '').slice(0, 120)
        }
      } else if (typeof content === 'string') {
        preview = content.slice(0, 120)
      }
    }

    return {
      index,
      uuid: String((m as any).uuid ?? ''),
      type: m.type,
      toolUseID: getToolUseID(m),
      preview,
    }
  })
}

const command: Command = {
  name: 'messages-debug',
  description: 'Dump messages + derived UI state for debugging',
  isEnabled: isDebugMode(),
  isHidden: true,
  type: 'local',

  userFacingName() {
    return this.name
  },

  async call(args: string) {
    const wantFull = args.includes('--full') || args.includes('--json')

    const rawMessages = getMessagesGetter()()
    const normalized = normalizeMessages(rawMessages).filter(isNotEmptyMessage)
    const ordered = reorderMessages(normalized)
    const unresolvedToolUseIDs = getUnresolvedToolUseIDs(normalized)
    const inProgressToolUseIDs = getInProgressToolUseIDs(normalized)
    const replStaticPrefixLength = getReplStaticPrefixLength(
      ordered,
      normalized,
      unresolvedToolUseIDs,
    )

    const { toolUseIDs, duplicates, byID } = summarizeToolUses(normalized)

    const latestLog = getLatestMessagesLogFile()
    const latestLogContent =
      latestLog && existsSync(latestLog.path)
        ? (() => {
            try {
              return JSON.parse(readFileSync(latestLog.path, 'utf8'))
            } catch {
              return null
            }
          })()
        : null

    const payload = {
      projectMessagesDir: CACHE_PATHS.messages(),
      latestMessagesLog: latestLog
        ? { path: latestLog.path, mtimeMs: latestLog.mtimeMs }
        : null,
      latestMessagesLogJson: latestLogContent,
      summary: {
        rawMessageCount: rawMessages.length,
        normalizedMessageCount: normalized.length,
        orderedMessageCount: ordered.length,
        replStaticPrefixLength,
        unresolvedToolUseIDs: [...unresolvedToolUseIDs],
        inProgressToolUseIDs: [...inProgressToolUseIDs],
        toolUseIDs,
        duplicateToolUseIDs: duplicates,
        toolUseSummary: byID,
      },
      orderedMessages: summarizeOrderedMessages(ordered),
      ...(wantFull ? { rawMessages } : {}),
    }

    return safeStringify(payload)
  },
}

export default command
