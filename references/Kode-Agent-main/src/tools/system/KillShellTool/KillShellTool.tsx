import { Box, Text } from 'ink'
import React from 'react'
import { z } from 'zod'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool } from '@tool'
import { BunShell } from '@utils/bun/shell'
import { DESCRIPTION, PROMPT, TOOL_NAME_FOR_PROMPT } from './prompt'

const inputSchema = z.strictObject({
  shell_id: z.string().describe('The ID of the background shell to kill'),
})

type Input = z.infer<typeof inputSchema>
type Output = {
  message: string
  shell_id: string
}

export const KillShellTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description() {
    return DESCRIPTION
  },
  userFacingName() {
    return 'Kill Shell'
  },
  inputSchema,
  isReadOnly() {
    return false
  },
  isConcurrencySafe() {
    return true
  },
  async isEnabled() {
    return true
  },
  needsPermissions() {
    return false
  },
  async prompt() {
    return PROMPT
  },
  renderToolUseMessage({ shell_id }: Input) {
    return `Kill shell: ${shell_id}`
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderToolResultMessage(output: Output) {
    return (
      <Box flexDirection="row">
        <Text>&nbsp;&nbsp;⎿ &nbsp;</Text>
        <Text>Shell {output.shell_id} killed</Text>
      </Box>
    )
  },
  renderResultForAssistant(output: Output) {
    return JSON.stringify(output)
  },
  async validateInput({ shell_id }: Input) {
    const bg = BunShell.getInstance().getBackgroundOutput(shell_id)
    if (!bg) {
      return {
        result: false,
        message: `No shell found with ID: ${shell_id}`,
        errorCode: 1,
      }
    }
    return { result: true }
  },
  async *call({ shell_id }: Input) {
    const bg = BunShell.getInstance().getBackgroundOutput(shell_id)
    if (!bg) {
      throw new Error(`No shell found with ID: ${shell_id}`)
    }

    const status = bg.killed
      ? 'killed'
      : bg.code === null
        ? 'running'
        : bg.code === 0
          ? 'completed'
          : 'failed'

    if (status !== 'running') {
      throw new Error(
        `Shell ${shell_id} is not running, so cannot be killed (status: ${status})`,
      )
    }

    const killed = BunShell.getInstance().killBackgroundShell(shell_id)
    const output: Output = {
      message: killed
        ? `Successfully killed shell: ${shell_id} (${bg.command})`
        : `No shell found with ID: ${shell_id}`,
      shell_id,
    }
    yield {
      type: 'result',
      data: output,
      resultForAssistant: this.renderResultForAssistant(output),
    }
  },
} satisfies Tool<typeof inputSchema, Output>
