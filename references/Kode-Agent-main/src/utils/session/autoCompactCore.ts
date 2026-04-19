import { Message } from '@query'
import { countTokens } from '@utils/model/tokens'
import { getMessagesGetter, getMessagesSetter } from '@messages'
import { getContext } from '@context'
import { getCodeStyle } from '@utils/config/style'
import { clearTerminal } from '@utils/terminal'
import { resetFileFreshnessSession } from '@services/fileFreshness'
import { createUserMessage, normalizeMessagesForAPI } from '@utils/messages'
import { queryLLM } from '@services/llmLazy'
import { selectAndReadFiles } from './fileRecoveryCore'
import { addLineNumbers } from '@utils/fs/file'
import { getModelManager } from '@utils/model'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'
import {
  calculateAutoCompactThresholds,
} from './autoCompactThreshold'

async function getMainConversationContextLimit(): Promise<number> {
  try {
    const modelManager = getModelManager()
    const resolution = modelManager.resolveModelWithInfo('main')
    const modelProfile = resolution.success ? resolution.profile : null

    if (modelProfile?.contextLength) {
      return modelProfile.contextLength
    }

    return 200_000
  } catch (error) {
    return 200_000
  }
}

const COMPRESSION_PROMPT = `Please provide a comprehensive summary of our conversation structured as follows:

## Technical Context
Development environment, tools, frameworks, and configurations in use. Programming languages, libraries, and technical constraints. File structure, directory organization, and project architecture.

## Project Overview  
Main project goals, features, and scope. Key components, modules, and their relationships. Data models, APIs, and integration patterns.

## Code Changes
Files created, modified, or analyzed during our conversation. Specific code implementations, functions, and algorithms added. Configuration changes and structural modifications.

## Debugging & Issues
Problems encountered and their root causes. Solutions implemented and their effectiveness. Error messages, logs, and diagnostic information.

## Current Status
What we just completed successfully. Current state of the codebase and any ongoing work. Test results, validation steps, and verification performed.

## Pending Tasks
Immediate next steps and priorities. Planned features, improvements, and refactoring. Known issues, technical debt, and areas needing attention.

## User Preferences
Coding style, formatting, and organizational preferences. Communication patterns and feedback style. Tool choices and workflow preferences.

## Key Decisions
Important technical decisions made and their rationale. Alternative approaches considered and why they were rejected. Trade-offs accepted and their implications.

Focus on information essential for continuing the conversation effectively, including specific details about code, files, errors, and plans.`

async function calculateThresholds(tokenCount: number) {
  const contextLimit = await getMainConversationContextLimit()
  return calculateAutoCompactThresholds(tokenCount, contextLimit)
}

async function shouldAutoCompact(messages: Message[]): Promise<boolean> {
  if (messages.length < 3) return false

  const tokenCount = countTokens(messages)
  const { isAboveAutoCompactThreshold } = await calculateThresholds(tokenCount)

  return isAboveAutoCompactThreshold
}

export async function checkAutoCompact(
  messages: Message[],
  toolUseContext: any,
): Promise<{ messages: Message[]; wasCompacted: boolean }> {
  if (!(await shouldAutoCompact(messages))) {
    return { messages, wasCompacted: false }
  }

  try {
    const compactedMessages = await executeAutoCompact(messages, toolUseContext)

    return {
      messages: compactedMessages,
      wasCompacted: true,
    }
  } catch (error) {
    logError(error)
    debugLogger.warn('AUTO_COMPACT_FAILED', {
      error: error instanceof Error ? error.message : String(error),
    })
    return { messages, wasCompacted: false }
  }
}

async function executeAutoCompact(
  messages: Message[],
  toolUseContext: any,
): Promise<Message[]> {
  const summaryRequest = createUserMessage(COMPRESSION_PROMPT)

  const tokenCount = countTokens(messages)
  const modelManager = getModelManager()
  const compactResolution = modelManager.resolveModelWithInfo('compact')
  const mainResolution = modelManager.resolveModelWithInfo('main')

  let compressionModelPointer: 'compact' | 'main' = 'compact'
  let compressionNotice: string | null = null

  if (!compactResolution.success || !compactResolution.profile) {
    compressionModelPointer = 'main'
    compressionNotice =
      compactResolution.error ||
      "Compression model pointer 'compact' is not configured."
  } else {
    const compactBudget = Math.floor(
      compactResolution.profile.contextLength * 0.9,
    )
    if (compactBudget > 0 && tokenCount > compactBudget) {
      compressionModelPointer = 'main'
      compressionNotice = `Compression model '${compactResolution.profile.name}' does not fit current context (~${Math.round(tokenCount / 1000)}k tokens).`
    }
  }

  if (
    compressionModelPointer === 'main' &&
    (!mainResolution.success || !mainResolution.profile)
  ) {
    throw new Error(
      mainResolution.error ||
        "Compression fallback failed: model pointer 'main' is not configured.",
    )
  }

  const summaryResponse = await queryLLM(
    normalizeMessagesForAPI([...messages, summaryRequest]),
    [
      'You are a helpful AI assistant tasked with creating comprehensive conversation summaries that preserve all essential context for continuing development work.',
    ],
    0,
    [],
    toolUseContext.abortController.signal,
    {
      safeMode: false,
      model: compressionModelPointer,
      prependCLISysprompt: true,
    },
  )

  const content = summaryResponse.message.content
  const summary =
    typeof content === 'string'
      ? content
      : content.length > 0 && content[0]?.type === 'text'
        ? content[0].text
        : null

  if (!summary) {
    throw new Error(
      'Failed to generate conversation summary - response did not contain valid text content',
    )
  }

  summaryResponse.message.usage = {
    input_tokens: 0,
    output_tokens: summaryResponse.message.usage.output_tokens,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0,
  }

  const recoveredFiles = await selectAndReadFiles()

  const compactedMessages = [
    createUserMessage(
      compressionNotice
        ? `Context automatically compressed due to token limit. ${compressionNotice} Using '${compressionModelPointer}' for compression.`
        : `Context automatically compressed due to token limit. Using '${compressionModelPointer}' for compression.`,
    ),
    summaryResponse,
  ]

  if (recoveredFiles.length > 0) {
    for (const file of recoveredFiles) {
      const contentWithLines = addLineNumbers({
        content: file.content,
        startLine: 1,
      })
      const recoveryMessage = createUserMessage(
        `**Recovered File: ${file.path}**\n\n\`\`\`\n${contentWithLines}\n\`\`\`\n\n` +
          `*Automatically recovered (${file.tokens} tokens)${file.truncated ? ' [truncated]' : ''}*`,
      )
      compactedMessages.push(recoveryMessage)
    }
  }

  getMessagesSetter()([])
  getContext.cache.clear?.()
  getCodeStyle.cache.clear?.()
  resetFileFreshnessSession()

  return compactedMessages
}
