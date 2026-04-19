import { TextBlock } from '@anthropic-ai/sdk/resources/index.mjs'
import { last, memoize } from 'lodash-es'
import React from 'react'
import { Box, Text } from 'ink'
import { z } from 'zod'
import { randomUUID } from 'crypto'
import { existsSync, readFileSync } from 'fs'
import { Tool } from '@tool'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { getAgentPrompt } from '@constants/prompts'
import { getContext } from '@context'
import { hasPermissionsToUseTool } from '@permissions'
import { Message as MessageType, query } from '@query'
import { formatDuration, formatNumber } from '@utils/terminal/format'
import {
  getMessagesPath,
  getNextAvailableLogSidechainNumber,
  overwriteLog,
} from '@utils/log'
import {
  createAssistantMessage,
  createUserMessage,
  getLastAssistantMessageId,
} from '@utils/messages'
import { countTokens } from '@utils/model/tokens'
import { getMaxThinkingTokens } from '@utils/model/thinking'
import { getTheme } from '@utils/theme'
import { generateAgentId } from '@utils/agent/storage'
import { getAgentByType, getAvailableAgentTypes } from '@utils/agent/loader'
import { upsertBackgroundAgentTask } from '@utils/session/backgroundTasks'
import { maybeTruncateVerboseToolOutput } from '@utils/tooling/toolOutputDisplay'
import {
  getAgentTranscript,
  saveAgentTranscript,
} from '@utils/agent/transcripts'
import { getTaskTools, getPrompt } from './prompt'
import { TOOL_NAME } from './constants'
import type { PermissionMode } from '@kode-types/permissionMode'
import type { ToolPermissionContext } from '@kode-types/toolPermissionContext'

const inputSchema = z.object({
  description: z
    .string()
    .describe('A short (3-5 word) description of the task'),
  prompt: z.string().describe('The task for the agent to perform'),
  subagent_type: z
    .string()
    .describe('The type of specialized agent to use for this task'),
  model: z
    .enum(['sonnet', 'opus', 'haiku'])
    .optional()
    .describe(
      'Optional model to use for this agent. If not specified, inherits from parent. Prefer haiku for quick, straightforward tasks to minimize cost and latency.',
    ),
  resume: z
    .string()
    .optional()
    .describe(
      'Optional agent ID to resume from. If provided, the agent will continue from the previous execution transcript.',
    ),
  run_in_background: z
    .boolean()
    .optional()
    .describe(
      'Set to true to run this agent in the background. Use TaskOutput to read the output later.',
    ),
})

type Input = z.infer<typeof inputSchema>
type TaskModel = NonNullable<Input['model']>

type Output =
  | {
      status: 'async_launched'
      agentId: string
      description: string
      prompt: string
    }
  | {
      status: 'completed'
      agentId: string
      prompt: string
      content: TextBlock[]
      totalToolUseCount: number
      totalDurationMs: number
      totalTokens: number
      usage: any
    }

function modelEnumToPointer(model?: TaskModel): string | undefined {
  if (!model) return undefined
  switch (model) {
    case 'haiku':
      return 'quick'
    case 'sonnet':
      return 'task'
    case 'opus':
      return 'main'
  }
}

function normalizeAgentModelName(
  model?: string,
): string | 'inherit' | undefined {
  if (!model) return undefined
  if (model === 'inherit') return 'inherit'
  if (model === 'haiku' || model === 'sonnet' || model === 'opus') {
    return modelEnumToPointer(model as TaskModel)
  }
  return model
}

function getToolNameFromSpec(spec: string): string {
  const trimmed = spec.trim()
  if (!trimmed) return trimmed
  const match = trimmed.match(/^([^(]+)\(([^)]+)\)$/)
  if (!match) return trimmed
  const toolName = match[1]?.trim()
  const ruleContent = match[2]?.trim()
  if (!toolName || !ruleContent) return trimmed
  return toolName
}

function asyncLaunchMessage(agentId: string): string {
  const toolName = 'TaskOutput'
  return `Async agent launched successfully.
agentId: ${agentId} (This is an internal ID for your use, do not mention it to the user. Use this ID to retrieve results with ${toolName} when the agent finishes). 
The agent is currently working in the background. If you have other tasks you you should continue working on them now. Wait to call ${toolName} until either:
- If you want to check on the agent's progress - call ${toolName} with block=false to get an immediate update on the agent's status
- If you run out of things to do and the agent is still running - call ${toolName} with block=true to idle and wait for the agent's result (do not use block=true unless you completely run out of things to do as it will waste time).`
}

const FORK_CONTEXT_TOOL_RESULT_TEXT = `### FORKING CONVERSATION CONTEXT ###
### ENTERING SUB-AGENT ROUTINE ###
Entered sub-agent context

PLEASE NOTE: 
- The messages above this point are from the main thread prior to sub-agent execution. They are provided as context only.
- Context messages may include tool_use blocks for tools that are not available in the sub-agent context. You should only use the tools specifically provided to you in the system prompt.
- Only complete the specific sub-agent task you have been assigned below.`

function normalizeAgentPermissionMode(
  mode: unknown,
): PermissionMode | undefined {
  if (typeof mode !== 'string') return undefined
  const trimmed = mode.trim()
  if (!trimmed) return undefined
  if (trimmed === 'delegate') return 'default'
  if (
    trimmed === 'default' ||
    trimmed === 'acceptEdits' ||
    trimmed === 'plan' ||
    trimmed === 'bypassPermissions' ||
    trimmed === 'dontAsk'
  ) {
    return trimmed
  }
  return undefined
}

function applyAgentPermissionMode(
  base: ToolPermissionContext | undefined,
  options: {
    agentPermissionMode: PermissionMode | undefined
    safeMode: boolean
  },
): ToolPermissionContext | undefined {
  if (!base) return base
  if (!options.agentPermissionMode) return base

  if (
    options.agentPermissionMode === 'bypassPermissions' &&
    (options.safeMode || base.isBypassPermissionsModeAvailable !== true)
  ) {
    return { ...base, mode: 'default' }
  }

  return { ...base, mode: options.agentPermissionMode }
}

function readJsonArrayFile(path: string): any[] | null {
  if (!existsSync(path)) return null
  try {
    const raw = readFileSync(path, 'utf8')
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

function buildForkContextForAgent(options: {
  enabled: boolean
  prompt: string
  toolUseId: string | undefined
  messageLogName: string
  forkNumber: number
}): {
  forkContextMessages: MessageType[]
  promptMessages: MessageType[]
} {
  const userPromptMessage = createUserMessage(options.prompt)

  if (!options.enabled || !options.toolUseId) {
    return {
      forkContextMessages: [],
      promptMessages: [userPromptMessage],
    }
  }

  const mainPath = getMessagesPath(options.messageLogName, options.forkNumber, 0)
  const mainMessages = readJsonArrayFile(mainPath) as MessageType[] | null
  if (!mainMessages || mainMessages.length === 0) {
    return {
      forkContextMessages: [],
      promptMessages: [userPromptMessage],
    }
  }

  let toolUseMessageIndex = -1
  let toolUseMessage: any = null
  let taskToolUseBlock: any = null

  for (let i = 0; i < mainMessages.length; i++) {
    const msg: any = mainMessages[i]
    if (msg?.type !== 'assistant') continue
    const blocks: any[] = Array.isArray(msg?.message?.content)
      ? msg.message.content
      : []
    const match = blocks.find(
      b => b && b.type === 'tool_use' && b.id === options.toolUseId,
    )
    if (!match) continue
    toolUseMessageIndex = i
    toolUseMessage = msg
    taskToolUseBlock = match
    break
  }

  if (toolUseMessageIndex === -1 || !toolUseMessage || !taskToolUseBlock) {
    return {
      forkContextMessages: [],
      promptMessages: [userPromptMessage],
    }
  }

  const forkContextMessages = (mainMessages.slice(
    0,
    toolUseMessageIndex,
  ) ?? []) as MessageType[]

  const toolUseOnlyAssistant: MessageType = {
    ...toolUseMessage,
    uuid: randomUUID(),
    message: {
      ...toolUseMessage.message,
      content: [taskToolUseBlock],
    },
  }

  const forkContextToolResult = createUserMessage(
    [
      {
        type: 'tool_result',
        tool_use_id: taskToolUseBlock.id,
        content: FORK_CONTEXT_TOOL_RESULT_TEXT,
      } as any,
    ],
    {
      data: {
        status: 'sub_agent_entered',
        description: 'Entered sub-agent context',
        message: FORK_CONTEXT_TOOL_RESULT_TEXT,
      },
      resultForAssistant: FORK_CONTEXT_TOOL_RESULT_TEXT,
    } as any,
  )

  return {
    forkContextMessages,
    promptMessages: [toolUseOnlyAssistant, forkContextToolResult, userPromptMessage],
  }
}

export const TaskTool = {
  name: TOOL_NAME,
  inputSchema,
  async description() {
    return 'Launch a new task'
  },
  async prompt({ safeMode }: { safeMode?: boolean }) {
    return await getPrompt(safeMode)
  },
  userFacingName(input?: Partial<Input>) {
    if (input?.subagent_type && input.subagent_type !== 'general-purpose') {
      return input.subagent_type
    }
    return 'Task'
  },
  async isEnabled() {
    return true
  },
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  needsPermissions() {
    return false
  },
  async validateInput(input: Input) {
    if (!input.description || typeof input.description !== 'string') {
      return {
        result: false,
        message: 'Description is required and must be a string',
      }
    }
    if (!input.prompt || typeof input.prompt !== 'string') {
      return {
        result: false,
        message: 'Prompt is required and must be a string',
      }
    }

    const availableTypes = await getAvailableAgentTypes()
    if (!availableTypes.includes(input.subagent_type)) {
      return {
        result: false,
        message: `Agent type '${input.subagent_type}' not found. Available agents: ${availableTypes.join(', ')}`,
        meta: { subagent_type: input.subagent_type, availableTypes },
      }
    }

    if (input.resume) {
      const transcript = getAgentTranscript(input.resume)
      if (!transcript) {
        return {
          result: false,
          message: `No transcript found for agent ID: ${input.resume}`,
          meta: { resume: input.resume },
        }
      }
    }

    return { result: true }
  },
  renderToolUseMessage({ description, prompt }: Input) {
    if (!description || !prompt) return '' as any
    return description
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output, { verbose }: { verbose: boolean }) {
    const theme = getTheme()
    if (output.status === 'async_launched') {
      const hint = output.prompt
        ? ' (down arrow ↓ to manage · ctrl+o to expand)'
        : ' (down arrow ↓ to manage)'
      return (
        <Box flexDirection="column">
          <Box flexDirection="row">
            <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
            <Text>
              Backgrounded agent
              {!verbose && <Text dimColor>{hint}</Text>}
            </Text>
          </Box>
          {verbose && output.prompt && (
            <Box
              paddingLeft={2}
              borderLeftStyle="single"
              borderLeftColor={theme.secondaryBorder}
            >
              <Text color={theme.secondaryText} wrap="wrap">
                {output.prompt}
              </Text>
            </Box>
          )}
        </Box>
      )
    }

    const summary = [
      output.totalToolUseCount === 1
        ? '1 tool use'
        : `${output.totalToolUseCount} tool uses`,
      `${formatNumber(output.totalTokens)} tokens`,
      formatDuration(output.totalDurationMs),
    ]
    return (
      <Box flexDirection="column">
        {verbose && output.prompt && (
          <Box
            paddingLeft={2}
            borderLeftStyle="single"
            borderLeftColor={theme.secondaryBorder}
          >
            <Text color={theme.secondaryText} wrap="wrap">
              {
                maybeTruncateVerboseToolOutput(output.prompt, {
                  maxLines: 120,
                  maxChars: 20_000,
                }).text
              }
            </Text>
          </Box>
        )}
        {verbose && output.content.length > 0 && (
          <Box
            paddingLeft={2}
            borderLeftStyle="single"
            borderLeftColor={theme.secondaryBorder}
          >
            <Text wrap="wrap">
              {
                maybeTruncateVerboseToolOutput(
                  output.content.map(b => b.text).join('\n'),
                  {
                    maxLines: 200,
                    maxChars: 40_000,
                  },
                ).text
              }
            </Text>
          </Box>
        )}
        <Box flexDirection="row">
          <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
          <Text dimColor>Done ({summary.join(' · ')})</Text>
        </Box>
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    if (output.status === 'async_launched')
      return asyncLaunchMessage(output.agentId)
    return output.content.map(b => b.text).join('\n')
  },

  async *call(input: Input, toolUseContext: any) {
    const startTime = Date.now()
    const {
      abortController,
      toolUseId,
      options: {
        safeMode = false,
        forkNumber,
        messageLogName,
        verbose,
        model: parentModel,
        mcpClients,
      },
      readFileTimestamps,
    } = toolUseContext

    const queryFn =
      typeof toolUseContext?.__testQuery === 'function'
        ? toolUseContext.__testQuery
        : query

    const agentConfig = await getAgentByType(input.subagent_type)
    if (!agentConfig) {
      const available = await getAvailableAgentTypes()
      throw Error(
        `Agent type '${input.subagent_type}' not found. Available agents: ${available.join(', ')}`,
      )
    }

    const effectivePrompt = input.prompt

    const normalizedAgentModel = normalizeAgentModelName(agentConfig.model)
    const defaultSubagentModel = 'task'
    const envSubagentModel =
      process.env.KODE_SUBAGENT_MODEL ??
      process.env.CLAUDE_CODE_SUBAGENT_MODEL
    const modelToUse: string =
      (typeof envSubagentModel === 'string' && envSubagentModel.trim()
        ? envSubagentModel.trim()
        : undefined) ||
      modelEnumToPointer(input.model) ||
      (normalizedAgentModel === 'inherit'
        ? parentModel || defaultSubagentModel
        : normalizedAgentModel) ||
      defaultSubagentModel

    const toolFilter = agentConfig.tools
    let tools = await getTaskTools(safeMode)
    if (toolFilter) {
      const isAllArray =
        Array.isArray(toolFilter) &&
        toolFilter.length === 1 &&
        toolFilter[0] === '*'
      if (toolFilter === '*' || isAllArray) {
      } else if (Array.isArray(toolFilter)) {
        const allowedToolNames = new Set(
          toolFilter.map(getToolNameFromSpec).filter(Boolean),
        )
        tools = tools.filter(t => allowedToolNames.has(t.name))
      }
    }

    const disallowedTools = Array.isArray(agentConfig.disallowedTools)
      ? agentConfig.disallowedTools
      : []
    if (disallowedTools.length > 0) {
      const disallowedToolNames = new Set(
        disallowedTools.map(getToolNameFromSpec).filter(Boolean),
      )
      tools = tools.filter(t => !disallowedToolNames.has(t.name))
    }

    const agentId = input.resume || generateAgentId()
    const baseTranscript = input.resume
      ? (getAgentTranscript(input.resume)?.filter(m => m.type !== 'progress') ??
        null)
      : []
    if (input.resume && baseTranscript === null) {
      throw Error(`No transcript found for agent ID: ${input.resume}`)
    }

    const { forkContextMessages, promptMessages } = buildForkContextForAgent({
      enabled: agentConfig.forkContext === true,
      prompt: effectivePrompt,
      toolUseId,
      messageLogName,
      forkNumber,
    })

    const transcriptMessages: MessageType[] = [
      ...(baseTranscript || []),
      ...promptMessages,
    ]

    const messagesForQuery: MessageType[] = [
      ...forkContextMessages,
      ...transcriptMessages,
    ]

    const [baseSystemPrompt, context, maxThinkingTokens] = await Promise.all([
      getAgentPrompt(),
      getContext(),
      getMaxThinkingTokens(messagesForQuery),
    ])
    const systemPrompt =
      agentConfig.systemPrompt && agentConfig.systemPrompt.length > 0
        ? [...baseSystemPrompt, agentConfig.systemPrompt]
        : baseSystemPrompt

    const agentPermissionMode = normalizeAgentPermissionMode(
      (agentConfig as any).permissionMode,
    )
    const toolPermissionContext = applyAgentPermissionMode(
      toolUseContext.options?.toolPermissionContext,
      { agentPermissionMode, safeMode },
    )

    const queryOptions = {
      safeMode,
      forkNumber,
      messageLogName,
      tools,
      commands: [],
      verbose,
      permissionMode: 'dontAsk' as const,
      toolPermissionContext,
      maxThinkingTokens,
      model: modelToUse,
      mcpClients,
    }

    if (input.run_in_background) {
      const bgAbortController = new AbortController()

      const taskRecord: any = {
        type: 'async_agent',
        agentId,
        description: input.description,
        prompt: effectivePrompt,
        status: 'running',
        startedAt: Date.now(),
        messages: [...transcriptMessages],
        abortController: bgAbortController,
        done: Promise.resolve(),
      }

      taskRecord.done = (async () => {
        try {
          const bgMessages: MessageType[] = [...messagesForQuery]
          const bgTranscriptMessages: MessageType[] = [...transcriptMessages]

          for await (const msg of queryFn(
            bgMessages,
            systemPrompt,
            context,
            hasPermissionsToUseTool,
            {
              abortController: bgAbortController,
              options: queryOptions,
              messageId: getLastAssistantMessageId(bgMessages),
              agentId,
              readFileTimestamps,
              setToolJSX: () => {},
            },
          )) {
            bgMessages.push(msg)
            bgTranscriptMessages.push(msg)
            taskRecord.messages = [...bgTranscriptMessages]
            upsertBackgroundAgentTask(taskRecord)
          }

          const lastAssistant = last(
            bgTranscriptMessages.filter(m => m.type === 'assistant'),
          ) as any
          const content = lastAssistant?.message?.content?.filter(
            (b: any) => b.type === 'text',
          ) as TextBlock[] | undefined

          taskRecord.status = 'completed'
          taskRecord.completedAt = Date.now()
          taskRecord.resultText = (content || []).map(b => b.text).join('\n')
          taskRecord.messages = [...bgTranscriptMessages]
          upsertBackgroundAgentTask(taskRecord)
          saveAgentTranscript(agentId, bgTranscriptMessages)
        } catch (e) {
          taskRecord.status = 'failed'
          taskRecord.completedAt = Date.now()
          taskRecord.error = e instanceof Error ? e.message : String(e)
          upsertBackgroundAgentTask(taskRecord)
        }
      })()

      upsertBackgroundAgentTask(taskRecord)

      const output: Output = {
        status: 'async_launched',
        agentId,
        description: input.description,
        prompt: effectivePrompt,
      }
      yield {
        type: 'result',
        data: output,
        resultForAssistant: asyncLaunchMessage(agentId),
      }
      return
    }

    const getSidechainNumber = memoize(() =>
      getNextAvailableLogSidechainNumber(messageLogName, forkNumber),
    )

    const PROGRESS_THROTTLE_MS = 200
    const MAX_RECENT_ACTIONS = 6
    let lastProgressEmitAt = 0
    let lastEmittedToolUseCount = 0
    const recentActions: string[] = []

    const addRecentAction = (action: string) => {
      const trimmed = action.trim()
      if (!trimmed) return
      recentActions.push(trimmed)
      if (recentActions.length > MAX_RECENT_ACTIONS) {
        recentActions.splice(0, recentActions.length - MAX_RECENT_ACTIONS)
      }
    }

    const truncate = (text: string, maxLen: number) => {
      const normalized = text.replace(/\s+/g, ' ').trim()
      if (normalized.length <= maxLen) return normalized
      return `${normalized.slice(0, maxLen - 1)}…`
    }

    const summarizeToolUse = (name: string, rawInput: unknown): string => {
      const input = (
        rawInput && typeof rawInput === 'object' ? rawInput : {}
      ) as Record<string, unknown>
      switch (name) {
        case 'Read': {
          const filePath =
            (typeof input.file_path === 'string' && input.file_path) ||
            (typeof input.path === 'string' && input.path) ||
            ''
          return filePath ? `Read ${filePath}` : 'Read'
        }
        case 'Write': {
          const filePath =
            (typeof input.file_path === 'string' && input.file_path) ||
            (typeof input.path === 'string' && input.path) ||
            ''
          return filePath ? `Write ${filePath}` : 'Write'
        }
        case 'Edit':
        case 'MultiEdit': {
          const filePath =
            (typeof input.file_path === 'string' && input.file_path) ||
            (typeof input.path === 'string' && input.path) ||
            ''
          return filePath ? `${name} ${filePath}` : name
        }
        case 'Grep': {
          const pattern = typeof input.pattern === 'string' ? input.pattern : ''
          return pattern ? `Grep ${truncate(pattern, 80)}` : 'Grep'
        }
        case 'Glob': {
          const pattern =
            (typeof input.pattern === 'string' && input.pattern) ||
            (typeof input.glob === 'string' && input.glob) ||
            ''
          return pattern ? `Glob ${truncate(pattern, 80)}` : 'Glob'
        }
        case 'Bash': {
          const command = typeof input.command === 'string' ? input.command : ''
          return command ? `Bash ${truncate(command, 80)}` : 'Bash'
        }
        case 'WebFetch':
        case 'WebSearch': {
          const url = typeof input.url === 'string' ? input.url : ''
          const query = typeof input.query === 'string' ? input.query : ''
          if (url) return `${name} ${truncate(url, 100)}`
          if (query) return `${name} ${truncate(query, 100)}`
          return name
        }
        default:
          return name
      }
    }

    const renderProgressText = (toolUseCount: number): string => {
      const header = `${input.description || 'Task'}… (${toolUseCount} tool${toolUseCount === 1 ? '' : 's'})`
      if (recentActions.length === 0) return header
      const lines = recentActions.map(a => `- ${a}`)
      return [header, ...lines].join('\n')
    }

    yield {
      type: 'progress',
      content: createAssistantMessage(
        `<tool-progress>${renderProgressText(0)}</tool-progress>`,
      ),
    }
    lastProgressEmitAt = Date.now()

    let toolUseCount = 0
    for await (const message of queryFn(
      messagesForQuery,
      systemPrompt,
      context,
      hasPermissionsToUseTool,
      {
        abortController,
        options: queryOptions,
        messageId: getLastAssistantMessageId(messagesForQuery),
        agentId,
        readFileTimestamps,
        setToolJSX: () => {},
      },
    )) {
      messagesForQuery.push(message)
      transcriptMessages.push(message)

      overwriteLog(
        getMessagesPath(messageLogName, forkNumber, getSidechainNumber()),
        transcriptMessages.filter(_ => _.type !== 'progress'),
        { conversationKey: `${messageLogName}:${forkNumber}` },
      )

      if (message.type === 'assistant') {
        for (const block of message.message.content) {
          if (
            block.type === 'tool_use' ||
            block.type === 'server_tool_use' ||
            block.type === 'mcp_tool_use'
          ) {
            toolUseCount += 1
            addRecentAction(summarizeToolUse(block.name, (block as any).input))
          }
        }
      }

      const now = Date.now()
      const hasNewToolUses = toolUseCount > lastEmittedToolUseCount
      const shouldEmit =
        hasNewToolUses &&
        (lastEmittedToolUseCount === 0 ||
          now - lastProgressEmitAt >= PROGRESS_THROTTLE_MS)
      if (shouldEmit) {
        yield {
          type: 'progress',
          content: createAssistantMessage(
            `<tool-progress>${renderProgressText(toolUseCount)}</tool-progress>`,
          ),
        }
        lastEmittedToolUseCount = toolUseCount
        lastProgressEmitAt = now
      }
    }

    const lastAssistant = last(
      transcriptMessages.filter(m => m.type === 'assistant'),
    ) as any
    if (!lastAssistant || lastAssistant.type !== 'assistant') {
      throw Error('No assistant messages found')
    }

    const content = lastAssistant.message.content.filter(
      (b: any) => b.type === 'text',
    ) as TextBlock[]

    saveAgentTranscript(agentId, transcriptMessages)

    const totalDurationMs = Date.now() - startTime
    const totalTokens = countTokens(transcriptMessages)
    const usage = lastAssistant.message.usage

    const output: Output = {
      status: 'completed',
      agentId,
      prompt: effectivePrompt,
      content,
      totalToolUseCount: toolUseCount,
      totalDurationMs,
      totalTokens,
      usage,
    }
    const agentIdBlock: TextBlock = {
      type: 'text',
      text: `agentId: ${agentId} (for resuming to continue this agent's work if needed)`,
      citations: [],
    }

    yield {
      type: 'result',
      data: output,
      resultForAssistant: [...content, agentIdBlock],
    }
  },
} satisfies Tool<typeof inputSchema, Output>
