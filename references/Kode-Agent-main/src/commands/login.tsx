import * as React from 'react'
import type { Command } from '@commands'
import { ConsoleOAuthFlow } from '@components/ConsoleOAuthFlow'
import { clearTerminal } from '@utils/terminal'
import { isLoggedInToAnthropic } from '@utils/identity/auth'
import { useExitOnCtrlCD } from '@hooks/useExitOnCtrlCD'
import { Box, Text } from 'ink'
import { clearConversation } from './clear'

export default () =>
  ({
    type: 'local-jsx',
    name: 'login',
    description: isLoggedInToAnthropic()
      ? 'Switch ShareAI Lab accounts'
      : 'Sign in with your ShareAI Lab account',
    isEnabled: true,
    isHidden: false,
    async call(onDone, context) {
      await clearTerminal()
      return (
        <Login
          onDone={async () => {
            clearConversation(context)
            onDone()
          }}
        />
      )
    },
    userFacingName() {
      return 'login'
    },
  }) satisfies Command

function Login(props: { onDone: () => void }) {
  const exitState = useExitOnCtrlCD(props.onDone)
  return (
    <Box flexDirection="column">
      <ConsoleOAuthFlow onDone={props.onDone} />
      <Box marginLeft={3}>
        <Text dimColor>
          {exitState.pending ? (
            <>Press {exitState.keyName} again to exit</>
          ) : (
            ''
          )}
        </Text>
      </Box>
    </Box>
  )
}
