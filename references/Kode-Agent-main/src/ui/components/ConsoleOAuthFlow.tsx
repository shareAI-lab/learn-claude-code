import React, { useEffect, useState, useCallback } from 'react'
import { Static, Box, Text, useInput } from 'ink'
import TextInput from './TextInput'
import { OAuthService, createAndStoreApiKey } from '@services/oauth'
import { getTheme } from '@utils/theme'
import { AsciiLogo } from './AsciiLogo'
import { useTerminalSize } from '@hooks/useTerminalSize'
import { logError } from '@utils/log'
import { clearTerminal } from '@utils/terminal'
import { SimpleSpinner } from './Spinner'
import { WelcomeBox } from './Onboarding'
import { PRODUCT_NAME } from '@constants/product'
import { sendNotification } from '@services/notifier'

type Props = {
  onDone(): void
}

type OAuthStatus =
  | { state: 'idle' }
  | { state: 'ready_to_start' }
  | { state: 'waiting_for_login'; url: string }
  | { state: 'creating_api_key' }
  | { state: 'about_to_retry'; nextState: OAuthStatus }
  | { state: 'success'; apiKey: string }
  | {
      state: 'error'
      message: string
      toRetry?: OAuthStatus
    }

const PASTE_HERE_MSG = 'Paste code here if prompted > '

export function ConsoleOAuthFlow({ onDone }: Props): React.ReactNode {
  const [oauthStatus, setOAuthStatus] = useState<OAuthStatus>({
    state: 'idle',
  })
  const theme = getTheme()

  const [pastedCode, setPastedCode] = useState('')
  const [cursorOffset, setCursorOffset] = useState(0)
  const [oauthService] = useState(() => new OAuthService())
  const [showPastePrompt, setShowPastePrompt] = useState(false)
  const [isClearing, setIsClearing] = useState(false)

  const textInputColumns = useTerminalSize().columns - PASTE_HERE_MSG.length - 1

  useEffect(() => {
    if (isClearing) {
      clearTerminal()
      setIsClearing(false)
    }
  }, [isClearing])

  useEffect(() => {
    if (oauthStatus.state === 'about_to_retry') {
      setIsClearing(true)
      setTimeout(() => {
        setOAuthStatus(oauthStatus.nextState)
      }, 1000)
    }
  }, [oauthStatus])

  useInput(async (_, key) => {
    if (key.return) {
      if (oauthStatus.state === 'idle') {
        setOAuthStatus({ state: 'ready_to_start' })
      } else if (oauthStatus.state === 'success') {
        await clearTerminal()
        onDone()
      } else if (oauthStatus.state === 'error' && oauthStatus.toRetry) {
        setPastedCode('')
        setOAuthStatus({
          state: 'about_to_retry',
          nextState: oauthStatus.toRetry,
        })
      }
    }
  })

  async function handleSubmitCode(value: string, url: string) {
    try {
      const [authorizationCode, state] = value.split('#')

      if (!authorizationCode || !state) {
        setOAuthStatus({
          state: 'error',
          message: 'Invalid code. Please make sure the full code was copied',
          toRetry: { state: 'waiting_for_login', url },
        })
        return
      }


      oauthService.processCallback({
        authorizationCode,
        state,
        useManualRedirect: true,
      })
    } catch (err) {
      logError(err)
      setOAuthStatus({
        state: 'error',
        message: (err as Error).message,
        toRetry: { state: 'waiting_for_login', url },
      })
    }
  }

  const startOAuth = useCallback(async () => {
    try {
      const result = await oauthService
        .startOAuthFlow(async url => {
          setOAuthStatus({ state: 'waiting_for_login', url })
          setTimeout(() => setShowPastePrompt(true), 3000)
        })
        .catch(err => {
          if (err.message.includes('Token exchange failed')) {
            setOAuthStatus({
              state: 'error',
              message:
                'Failed to exchange authorization code for access token. Please try again.',
              toRetry: { state: 'ready_to_start' },
            })
          } else {
            setOAuthStatus({
              state: 'error',
              message: err.message,
              toRetry: { state: 'ready_to_start' },
            })
          }
          throw err
        })

      setOAuthStatus({ state: 'creating_api_key' })

      const apiKey = await createAndStoreApiKey(result.accessToken).catch(
        err => {
          setOAuthStatus({
            state: 'error',
            message: 'Failed to create API key: ' + err.message,
            toRetry: { state: 'ready_to_start' },
          })

          throw err
        },
      )

      if (apiKey) {
        setOAuthStatus({ state: 'success', apiKey })
        sendNotification({ message: 'Kode login successful' })
      } else {
        setOAuthStatus({
          state: 'error',
          message:
            "Unable to create API key. The server accepted the request but didn't return a key.",
          toRetry: { state: 'ready_to_start' },
        })
      }
    } catch (err) {
      const errorMessage = (err as Error).message
    }
  }, [oauthService, setShowPastePrompt])

  useEffect(() => {
    if (oauthStatus.state === 'ready_to_start') {
      startOAuth()
    }
  }, [oauthStatus.state, startOAuth])

  function renderStatusMessage(): React.ReactNode {
    switch (oauthStatus.state) {
      case 'idle':
        return (
          <Box flexDirection="column" gap={1}>
            <Text bold>
              {PRODUCT_NAME} is billed based on API usage through your ShareAI
              Lab account.
            </Text>

            <Box>
              <Text>
                Pricing may evolve as we move towards general availability.
              </Text>
            </Box>

            <Box marginTop={1}>
              <Text color={theme.permission}>
                Press <Text bold>Enter</Text> to login to your ShareAI Lab
                account…
              </Text>
            </Box>
          </Box>
        )

      case 'waiting_for_login':
        return (
          <Box flexDirection="column" gap={1}>
            {!showPastePrompt && (
              <Box>
                <SimpleSpinner />
                <Text>Opening browser to sign in…</Text>
              </Box>
            )}

            {showPastePrompt && (
              <Box>
                <Text>{PASTE_HERE_MSG}</Text>
                <TextInput
                  value={pastedCode}
                  onChange={setPastedCode}
                  onSubmit={(value: string) =>
                    handleSubmitCode(value, oauthStatus.url)
                  }
                  cursorOffset={cursorOffset}
                  onChangeCursorOffset={setCursorOffset}
                  columns={textInputColumns}
                />
              </Box>
            )}
          </Box>
        )

      case 'creating_api_key':
        return (
          <Box flexDirection="column" gap={1}>
            <Box>
              <SimpleSpinner />
              <Text>Creating API key for Kode…</Text>
            </Box>
          </Box>
        )

      case 'about_to_retry':
        return (
          <Box flexDirection="column" gap={1}>
            <Text color={theme.permission}>Retrying…</Text>
          </Box>
        )

      case 'success':
        return (
          <Box flexDirection="column" gap={1}>
            <Text color={theme.success}>
              Login successful. Press <Text bold>Enter</Text> to continue…
            </Text>
          </Box>
        )

      case 'error':
        return (
          <Box flexDirection="column" gap={1}>
            <Text color={theme.error}>OAuth error: {oauthStatus.message}</Text>

            {oauthStatus.toRetry && (
              <Box marginTop={1}>
                <Text color={theme.permission}>
                  Press <Text bold>Enter</Text> to retry.
                </Text>
              </Box>
            )}
          </Box>
        )

      default:
        return null
    }
  }

  const staticItems: Record<string, React.JSX.Element> = {}
  if (!isClearing) {
    staticItems.header = (
      <Box key="header" flexDirection="column" gap={1}>
        <WelcomeBox />
        <Box paddingBottom={1} paddingLeft={1}>
          <AsciiLogo />
        </Box>
      </Box>
    )
  }
  if (oauthStatus.state === 'waiting_for_login' && showPastePrompt) {
    staticItems.urlToCopy = (
      <Box flexDirection="column" key="urlToCopy" gap={1} paddingBottom={1}>
        <Box paddingX={1}>
          <Text dimColor>
            Browser didn&apos;t open? Use the url below to sign in:
          </Text>
        </Box>
        <Box width={1000}>
          <Text dimColor>{oauthStatus.url}</Text>
        </Box>
      </Box>
    )
  }
  return (
    <Box flexDirection="column" gap={1}>
      <Static
        items={Object.keys(staticItems)}
        children={(item: string) => staticItems[item]}
      />
      <Box paddingLeft={1} flexDirection="column" gap={1}>
        {renderStatusMessage()}
      </Box>
    </Box>
  )
}
