import { Command } from '@commands'
import { getContext } from '@context'
import { getMessagesGetter, getMessagesSetter } from '@messages'
import { API_ERROR_MESSAGE_PREFIX } from '@services/llmConstants'
import { queryLLM } from '@services/llmLazy'
import { getGlobalConfig } from '@utils/config'
import { createUserMessage, normalizeMessagesForAPI } from '@utils/messages'
import { getCodeStyle } from '@utils/config/style'
import { clearTerminal } from '@utils/terminal'
import { resetReminderSession } from '@services/systemReminder'
import { resetFileFreshnessSession } from '@services/fileFreshness'

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

const compact = {
  type: 'local',
  name: 'compact',
  description: 'Clear conversation history but keep a summary in context',
  isEnabled: true,
  isHidden: false,
  async call(
    _,
    {
      options: { tools },
      abortController,
      setForkConvoWithMessagesOnTheNextRender,
    },
  ) {
    const messages = getMessagesGetter()()

    const summaryRequest = createUserMessage(COMPRESSION_PROMPT)
    const compactPointer = getGlobalConfig().modelPointers?.compact

    const summaryResponse = await queryLLM(
      normalizeMessagesForAPI([...messages, summaryRequest]),
      [
        'You are a helpful AI assistant tasked with creating comprehensive conversation summaries that preserve all essential context for continuing development work.',
      ],
      0,
      tools,
      abortController.signal,
      {
        safeMode: false,
        model: compactPointer ? 'compact' : 'main',
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
        `Failed to generate conversation summary - response did not contain valid text content - ${summaryResponse}`,
      )
    } else if (summary.startsWith(API_ERROR_MESSAGE_PREFIX)) {
      throw new Error(summary)
    }

    summaryResponse.message.usage = {
      input_tokens: 0,
      output_tokens: summaryResponse.message.usage.output_tokens,
      cache_creation_input_tokens: 0,
      cache_read_input_tokens: 0,
    }

    await clearTerminal()
    getMessagesSetter()([])
    setForkConvoWithMessagesOnTheNextRender([
      createUserMessage(
        `Context has been compressed using structured 8-section algorithm. All essential information has been preserved for seamless continuation.`,
      ),
      summaryResponse,
    ])
    getContext.cache.clear?.()
    getCodeStyle.cache.clear?.()
    resetFileFreshnessSession()

    resetReminderSession()

    return ''
  },
  userFacingName() {
    return 'compact'
  },
} satisfies Command

export default compact
