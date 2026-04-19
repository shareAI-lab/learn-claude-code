import { Box, Text, Newline } from 'ink'
import * as React from 'react'
import { getTheme } from '@utils/theme'
import { PRODUCT_NAME } from '@constants/product'
import { getGlobalConfig } from '@utils/config'
import { getCwd } from '@utils/state'
import { AsciiLogo } from './AsciiLogo'
import type { WrappedClient } from '@services/mcpClient'
import { getModelManager } from '@utils/model'
import { MACRO } from '@constants/macros'

export const MIN_LOGO_WIDTH = 50

const DEFAULT_UPDATE_COMMANDS = [
  'bun add -g @shareai-lab/kode@latest',
  'npm install -g @shareai-lab/kode@latest',
] as const

export function Logo({
  mcpClients,
  isDefaultModel = false,
  updateBannerVersion,
  updateBannerCommands,
}: {
  mcpClients: WrappedClient[]
  isDefaultModel?: boolean
  updateBannerVersion?: string | null
  updateBannerCommands?: string[] | null
}): React.ReactNode {
  const width = Math.max(MIN_LOGO_WIDTH, getCwd().length + 12)
  const theme = getTheme()
  const config = getGlobalConfig()

  const modelManager = getModelManager()
  const mainModelName = modelManager.getModelName('main')
  const currentModel = mainModelName || 'No model configured'
  const hasOverrides = Boolean(
    process.env.DISABLE_PROMPT_CACHING ||
    process.env.API_TIMEOUT_MS ||
    process.env.MAX_THINKING_TOKENS,
  )

  return (
    <Box flexDirection="column">
      <Box
        borderColor={theme.kode}
        borderStyle="round"
        flexDirection="column"
        gap={1}
        paddingLeft={1}
        marginRight={2}
        width={width}
      >
        {updateBannerVersion ? (
          <Box flexDirection="column">
            <Text color="yellow">
              New version available: {updateBannerVersion} (current:{' '}
              {MACRO.VERSION})
            </Text>
            <Text>Run the following command to update:</Text>
            <Text>
              {'  '}
              {updateBannerCommands?.[1] ?? DEFAULT_UPDATE_COMMANDS[1]}
            </Text>
            {process.platform !== 'win32' && (
              <Text dimColor>
                Note: you may need to prefix with "sudo" on macOS/Linux.
              </Text>
            )}
          </Box>
        ) : null}
        <Text>
          <Text color={theme.kode}>✻</Text> Welcome to{' '}
          <Text bold>{PRODUCT_NAME}</Text> <Text>research preview!</Text>
        </Text>
        {}

        <>
          <Box paddingLeft={2} flexDirection="column" gap={1}>
            <Text color={theme.secondaryText} italic>
              /help for help
            </Text>
            <Text color={theme.secondaryText}>cwd: {getCwd()}</Text>
          </Box>

          {hasOverrides && (
            <Box
              borderColor={theme.secondaryBorder}
              borderStyle="single"
              borderBottom={false}
              borderLeft={false}
              borderRight={false}
              borderTop={true}
              flexDirection="column"
              marginLeft={2}
              marginRight={1}
              paddingTop={1}
            >
              <Box marginBottom={1}>
                <Text color={theme.secondaryText}>Overrides (via env):</Text>
              </Box>
              {process.env.DISABLE_PROMPT_CACHING ? (
                <Text color={theme.secondaryText}>
                  • Prompt caching:{' '}
                  <Text color={theme.error} bold>
                    off
                  </Text>
                </Text>
              ) : null}
              {process.env.API_TIMEOUT_MS ? (
                <Text color={theme.secondaryText}>
                  • API timeout:{' '}
                  <Text bold>{process.env.API_TIMEOUT_MS}ms</Text>
                </Text>
              ) : null}
              {process.env.MAX_THINKING_TOKENS ? (
                <Text color={theme.secondaryText}>
                  • Max thinking tokens:{' '}
                  <Text bold>{process.env.MAX_THINKING_TOKENS}</Text>
                </Text>
              ) : null}
            </Box>
          )}
        </>
        {mcpClients.length ? (
          <Box
            borderColor={theme.secondaryBorder}
            borderStyle="single"
            borderBottom={false}
            borderLeft={false}
            borderRight={false}
            borderTop={true}
            flexDirection="column"
            marginLeft={2}
            marginRight={1}
            paddingTop={1}
          >
            <Box marginBottom={1}>
              <Text color={theme.secondaryText}>MCP Servers:</Text>
            </Box>
            {mcpClients.map((client, idx) => (
              <Box key={idx} width={width - 6}>
                <Text color={theme.secondaryText}>• {client.name}</Text>
                <Box flexGrow={1} />
                <Text
                  bold
                  color={
                    client.type === 'connected' ? theme.success : theme.error
                  }
                >
                  {client.type === 'connected' ? 'connected' : 'failed'}
                </Text>
              </Box>
            ))}
          </Box>
        ) : null}
      </Box>
    </Box>
  )
}
