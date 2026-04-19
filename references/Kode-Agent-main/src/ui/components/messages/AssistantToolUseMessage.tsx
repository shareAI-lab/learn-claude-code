import { Box, Text } from 'ink'
import React from 'react'
import { logError } from '@utils/log'
import { ToolUseBlockParam } from '@anthropic-ai/sdk/resources/index.mjs'
import { Tool } from '@tool'
import { Cost } from '@components/Cost'
import { ToolUseLoader } from '@components/ToolUseLoader'
import { getTheme } from '@utils/theme'
import { BLACK_CIRCLE } from '@constants/figures'
import { TaskToolMessage } from './TaskToolMessage'
import { resolveToolNameAlias } from '@utils/tooling/toolNameAliases'

type Props = {
  param: ToolUseBlockParam
  costUSD: number
  durationMs: number
  addMargin: boolean
  tools: Tool[]
  debug: boolean
  verbose: boolean
  erroredToolUseIDs: Set<string>
  inProgressToolUseIDs: Set<string>
  unresolvedToolUseIDs: Set<string>
  shouldAnimate: boolean
  shouldShowDot: boolean
}

export function AssistantToolUseMessage({
  param,
  costUSD,
  durationMs,
  addMargin,
  tools,
  debug,
  verbose,
  erroredToolUseIDs,
  inProgressToolUseIDs,
  unresolvedToolUseIDs,
  shouldAnimate,
  shouldShowDot,
}: Props): React.ReactNode {
  const resolvedName = resolveToolNameAlias(param.name).resolvedName
  const tool = tools.find(_ => _.name === resolvedName)
  if (!tool) {
    logError(`Tool ${param.name} not found`)
    return null
  }
  const isQueued =
    !inProgressToolUseIDs.has(param.id) && unresolvedToolUseIDs.has(param.id)
  const color = isQueued ? getTheme().secondaryText : undefined

  const parsedInput = tool.inputSchema.safeParse(param.input)
  const userFacingToolName = tool.userFacingName
    ? tool.userFacingName(
        parsedInput.success ? (parsedInput.data as any) : undefined,
      )
    : tool.name

  const hasToolName = userFacingToolName.trim().length > 0
  const hasInputObject =
    param.input &&
    typeof param.input === 'object' &&
    Object.keys(param.input as { [key: string]: unknown }).length > 0
  const toolMessage = hasInputObject
    ? tool.renderToolUseMessage(param.input as never, { verbose })
    : null
  const hasToolMessage =
    React.isValidElement(toolMessage) ||
    (typeof toolMessage === 'string' && toolMessage.trim().length > 0)

  if (!hasToolName && !hasToolMessage) {
    return null
  }
  return (
    <Box
      flexDirection="row"
      justifyContent="space-between"
      marginTop={addMargin ? 1 : 0}
      width="100%"
    >
      <Box>
        <Box
          flexWrap="nowrap"
          minWidth={userFacingToolName.length + (shouldShowDot ? 2 : 0)}
        >
          {shouldShowDot &&
            (isQueued ? (
              <Box minWidth={2}>
                <Text color={color}>{BLACK_CIRCLE}</Text>
              </Box>
            ) : (
              <ToolUseLoader
                shouldAnimate={shouldAnimate}
                isUnresolved={unresolvedToolUseIDs.has(param.id)}
                isError={erroredToolUseIDs.has(param.id)}
              />
            ))}
          {tool.name === 'Task' && param.input ? (
            <TaskToolMessage
              agentType={
                parsedInput.success
                  ? String(
                      (parsedInput.data as any).subagent_type ||
                        'general-purpose',
                    )
                  : 'general-purpose'
              }
              bold={Boolean(!isQueued)}
              children={String(userFacingToolName || '')}
            />
          ) : (
            hasToolName && (
              <Text color={color} bold={!isQueued}>
                {userFacingToolName}
              </Text>
            )
          )}
        </Box>
        <Box flexWrap="nowrap">
          {hasToolMessage &&
            (() => {
              if (React.isValidElement(toolMessage)) {
                if (!hasToolName) return toolMessage
                return (
                  <Box flexDirection="row">
                    <Text color={color}>(</Text>
                    {toolMessage}
                    <Text color={color}>)</Text>
                  </Box>
                )
              }

              if (typeof toolMessage !== 'string') return null

              if (!hasToolName) {
                return <Text color={color}>{toolMessage}</Text>
              }

              return <Text color={color}>({toolMessage})</Text>
            })()}
          <Text color={color}>…</Text>
        </Box>
      </Box>
      <Cost costUSD={costUSD} durationMs={durationMs} debug={debug} />
    </Box>
  )
}
