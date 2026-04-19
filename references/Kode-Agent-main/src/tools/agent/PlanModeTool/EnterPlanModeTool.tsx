import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { Tool } from '@tool'
import { enterPlanMode } from '@utils/plan/planMode'
import { ENTER_DESCRIPTION, ENTER_PROMPT, ENTER_TOOL_NAME } from './prompt'
import { getTheme } from '@utils/theme'
import { BLACK_CIRCLE } from '@constants/figures'
import { setPermissionMode } from '@utils/permissions/permissionModeState'

const inputSchema = z.strictObject({})

type Output = {
  message: string
}

export const EnterPlanModeTool = {
  name: ENTER_TOOL_NAME,
  async description() {
    return ENTER_DESCRIPTION
  },
  userFacingName() {
    return ''
  },
  inputSchema,
  isReadOnly() {
    return true
  },
  isConcurrencySafe() {
    return true
  },
  async isEnabled() {
    return true
  },
  needsPermissions() {
    return true
  },
  requiresUserInteraction() {
    return true
  },
  async prompt() {
    return ENTER_PROMPT
  },
  renderToolUseMessage() {
    return ''
  },
  renderToolUseRejectedMessage() {
    const theme = getTheme()
    return (
      <Box flexDirection="row" marginTop={1}>
        <Text color={theme.text}>{BLACK_CIRCLE}</Text>
        <Text> User declined to enter plan mode</Text>
      </Box>
    )
  },
  renderToolResultMessage(_output: Output) {
    const theme = getTheme()
    return (
      <Box flexDirection="column" marginTop={1}>
        <Box flexDirection="row">
          <Text color={theme.planMode}>{BLACK_CIRCLE}</Text>
          <Text> Entered plan mode</Text>
        </Box>
        <Box paddingLeft={2}>
          <Text dimColor>
            Kode Agent is now exploring and designing an implementation
            approach.
          </Text>
        </Box>
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    return `${output.message}

In plan mode, you should:
1. Thoroughly explore the codebase to understand existing patterns
2. Identify similar features and architectural approaches
3. Consider multiple approaches and their trade-offs
4. Use AskUserQuestion if you need to clarify the approach
5. Design a concrete implementation strategy
6. When ready, use ExitPlanMode to present your plan for approval

Remember: DO NOT write or edit any files yet. This is a read-only exploration and planning phase.`
  },
  async *call(_input: z.infer<typeof inputSchema>, context: any) {
    if (context?.agentId) {
      throw new Error('EnterPlanMode tool cannot be used in agent contexts')
    }

    setPermissionMode(context, 'plan')
    enterPlanMode(context)

    const output: Output = {
      message:
        'Entered plan mode. You should now focus on exploring the codebase and designing an implementation approach.',
    }
    yield {
      type: 'result',
      data: output,
      resultForAssistant: this.renderResultForAssistant(output),
    }
  },
} satisfies Tool<typeof inputSchema, Output>
