import { Box, Text, useInput } from 'ink'
import * as React from 'react'
import { useState, useCallback, useEffect } from 'react'
import { getTheme } from '@utils/theme'
import { getMessagesGetter } from '@messages'
import type { Message } from '@query'
import TextInput from './TextInput'
import { logError, getInMemoryErrors } from '@utils/log'
import { env } from '@utils/config/env'
import { getGitState, getIsGit, GitRepoState } from '@utils/system/git'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { getGlobalConfig } from '@utils/config'
import { USER_AGENT } from '@utils/system/http'
import { PRODUCT_NAME } from '@constants/product'
import { API_ERROR_MESSAGE_PREFIX } from '@services/llmConstants'
import { queryQuick } from '@services/llmLazy'
import { openBrowser } from '@utils/system/browser'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { MACRO } from '@constants/macros'
import { GITHUB_ISSUES_REPO_URL } from '@constants/product'

type Props = {
  onDone(result: string): void
}

type Step = 'userInput' | 'consent' | 'submitting' | 'done'

type FeedbackData = {
  message_count: number
  datetime: string
  description: string
  platform: string
  gitRepo: boolean
  version: string | null
  transcript: Message[]
}

export function Bug({ onDone }: Props): React.ReactNode {
  const [step, setStep] = useState<Step>('userInput')
  const [cursorOffset, setCursorOffset] = useState(0)
  const [description, setDescription] = useState('')
  const [feedbackId, setFeedbackId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [envInfo, setEnvInfo] = useState<{
    isGit: boolean
    gitState: GitRepoState | null
  }>({ isGit: false, gitState: null })
  const [title, setTitle] = useState<string | null>(null)
  const textInputColumns = useTerminalSize().columns - 4
  const messages = getMessagesGetter()()

  useEffect(() => {
    async function loadEnvInfo() {
      const isGit = await getIsGit()
      let gitState: GitRepoState | null = null
      if (isGit) {
        gitState = await getGitState()
      }
      setEnvInfo({ isGit, gitState })
    }
    void loadEnvInfo()
  }, [])

  const exitState = useExitOnCtrlCD(() => process.exit(0))

  const submitReport = useCallback(async () => {
    setStep('done')




  }, [description, envInfo.isGit, messages])

  useInput((input, key) => {

    if (error) {
      onDone('<bash-stderr>Error submitting bug report</bash-stderr>')
      return
    }

    if (key.escape) {
      onDone('<bash-stderr>Bug report cancelled</bash-stderr>')
      return
    }

    if (step === 'consent' && (key.return || input === ' ')) {
      const issueUrl = createGitHubIssueUrl(
        feedbackId,
        description.slice(0, 80),
        description,
      )
      void openBrowser(issueUrl)
      onDone('<bash-stdout>Bug report submitted</bash-stdout>')
    }
  })

  const theme = getTheme()

  return (
    <>
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={theme.permission}
        paddingX={1}
        paddingBottom={1}
        gap={1}
      >
        <Text bold color={theme.permission}>
          Submit Bug Report
        </Text>
        {step === 'userInput' && (
          <Box flexDirection="column" gap={1}>
            <Text>
              Describe the issue below and copy/paste any errors you see:
            </Text>
            <TextInput
              value={description}
              onChange={setDescription}
              columns={textInputColumns}
              onSubmit={() => setStep('consent')}
              onExitMessage={() =>
                onDone('<bash-stderr>Bug report cancelled</bash-stderr>')
              }
              cursorOffset={cursorOffset}
              onChangeCursorOffset={setCursorOffset}
            />
            {error && (
              <Box flexDirection="column" gap={1}>
                <Text color="red">{error}</Text>
                <Text dimColor>Press any key to close</Text>
              </Box>
            )}
          </Box>
        )}

        {step === 'consent' && (
          <Box flexDirection="column">
            <Text>This report will include:</Text>
            <Box marginLeft={2} flexDirection="column">
              <Text>
                - Your bug description: <Text dimColor>{description}</Text>
              </Text>
              <Text>
                - Environment info:{' '}
                <Text dimColor>
                  {env.platform}, {env.terminal}, v{MACRO.VERSION}
                </Text>
              </Text>
              {}
              <Text>- Model settings (no api keys)</Text>
            </Box>
            {}
          </Box>
        )}

        {step === 'submitting' && (
          <Box flexDirection="row" gap={1}>
            <Text>Submitting report…</Text>
          </Box>
        )}

        {step === 'done' && (
          <Box flexDirection="column">
            <Text color={getTheme().success}>Thank you for your report!</Text>
            {feedbackId && <Text dimColor>Feedback ID: {feedbackId}</Text>}
            <Box marginTop={1}>
              <Text>Press </Text>
              <Text bold>Enter </Text>
              <Text>
                to also create a GitHub issue, or any other key to close.
              </Text>
            </Box>
          </Box>
        )}
      </Box>

      <Box marginLeft={3}>
        <Text dimColor>
          {exitState.pending ? (
            <>Press {exitState.keyName} again to exit</>
          ) : step === 'userInput' ? (
            <>Enter to continue · Esc to cancel</>
          ) : step === 'consent' ? (
            <>Enter to open browser to create GitHub issue · Esc to cancel</>
          ) : null}
        </Text>
      </Box>
    </>
  )
}

function createGitHubIssueUrl(
  feedbackId: string,
  title: string,
  description: string,
): string {
  const globalConfig = getGlobalConfig()

  const modelProfiles = globalConfig.modelProfiles || []
  const activeProfiles = modelProfiles.filter(p => p.isActive)

  let modelInfo = '## Models\n'
  if (activeProfiles.length === 0) {
    modelInfo += '- No model profiles configured\n'
  } else {
    activeProfiles.forEach(profile => {
      modelInfo += `- ${profile.name}\n`
      modelInfo += `    - provider: ${profile.provider}\n`
      modelInfo += `    - model: ${profile.modelName}\n`
      modelInfo += `    - baseURL: ${profile.baseURL}\n`
      modelInfo += `    - maxTokens: ${profile.maxTokens}\n`
      modelInfo += `    - contextLength: ${profile.contextLength}\n`
      if (profile.reasoningEffort) {
        modelInfo += `    - reasoning effort: ${profile.reasoningEffort}\n`
      }
    })
  }

  const body = encodeURIComponent(`
## Bug Description
${description}

## Environment Info
- Platform: ${env.platform}
- Terminal: ${env.terminal}
- Version: ${MACRO.VERSION || 'unknown'}

${modelInfo}`)
  return `${GITHUB_ISSUES_REPO_URL}/new?title=${encodeURIComponent(title)}&body=${body}&labels=user-reported,bug`
}

async function generateTitle(description: string): Promise<string> {
  const response = await queryQuick({
    systemPrompt: [
      'Generate a concise issue title (max 80 chars) that captures the key point of this feedback. Do not include quotes or prefixes like "Feedback:" or "Issue:". If you cannot generate a title, just use "User Feedback".',
    ],
    userPrompt: description,
  })
  const title =
    response.message.content[0]?.type === 'text'
      ? response.message.content[0].text
      : 'Bug Report'
  if (title.startsWith(API_ERROR_MESSAGE_PREFIX)) {
    return `Bug Report: ${description.slice(0, 60)}${description.length > 60 ? '...' : ''}`
  }
  return title
}

async function submitFeedback(
  data: FeedbackData,
): Promise<{ success: boolean; feedbackId?: string }> {
  return { success: true, feedbackId: '123' }
}
