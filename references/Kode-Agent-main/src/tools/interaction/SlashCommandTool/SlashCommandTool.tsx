import { z } from 'zod'
import { FallbackToolUseRejectedMessage } from '@components/FallbackToolUseRejectedMessage'
import { Tool } from '@tool'
import * as React from 'react'
import type { Message } from '@query'
import { createUserMessage } from '@utils/messages'
import { getCommands } from '@commands'
import {
  loadCustomCommands,
  type CustomCommandWithScope,
} from '@services/customCommands'
import { TOOL_NAME_FOR_PROMPT } from './prompt'

const inputSchema = z.strictObject({
  command: z
    .string()
    .describe(
      'The slash command to execute with its arguments, e.g., "/review-pr 123"',
    ),
})

type Input = z.infer<typeof inputSchema>
type Output = {
  success: boolean
  commandName: string
}

function normalizeCommandModelName(model: unknown): string | undefined {
  if (typeof model !== 'string') return undefined
  const trimmed = model.trim()
  if (!trimmed || trimmed === 'inherit') return undefined
  if (trimmed === 'haiku') return 'quick'
  if (trimmed === 'sonnet') return 'task'
  if (trimmed === 'opus') return 'main'
  return trimmed
}

function getCharBudget(): number {
  const raw = Number(process.env.SLASH_COMMAND_TOOL_CHAR_BUDGET)
  return Number.isFinite(raw) && raw > 0 ? raw : 15000
}

export const SlashCommandTool = {
  name: TOOL_NAME_FOR_PROMPT,
  async description({ command }: Input) {
    return `Execute slash command: ${command}`
  },
  userFacingName() {
    return 'SlashCommand'
  },
  inputSchema,
  isReadOnly() {
    return false
  },
  isConcurrencySafe() {
    return false
  },
  async isEnabled() {
    return true
  },
  needsPermissions() {
    return true
  },
  async prompt() {
    const all = await loadCustomCommands()
    const commands = all.filter(
      cmd =>
        cmd.type === 'prompt' &&
        cmd.isSkill !== true &&
        cmd.disableModelInvocation !== true &&
        (cmd.hasUserSpecifiedDescription || cmd.whenToUse),
    )

    const limited: CustomCommandWithScope[] = []
    let used = 0
    for (const cmd of commands) {
      const name = `/${cmd.name}`
      const args = cmd.argumentHint ? ` ${cmd.argumentHint}` : ''
      const whenToUse = cmd.whenToUse ? `- ${cmd.whenToUse}` : ''
      const line = `- ${name}${args}: ${cmd.description} ${whenToUse}`.trim()
      used += line.length + 1
      if (used > getCharBudget()) break
      limited.push(cmd)
    }

    const availableLines =
      limited.length > 0
        ? limited
            .map(cmd => {
              const name = `/${cmd.name}`
              const args = cmd.argumentHint ? ` ${cmd.argumentHint}` : ''
              const whenToUse = cmd.whenToUse ? `- ${cmd.whenToUse}` : ''
              return `- ${name}${args}: ${cmd.description} ${whenToUse}`.trim()
            })
            .join('\n')
        : ''

    const truncatedNotice =
      commands.length > limited.length
        ? `\n(Showing ${limited.length} of ${commands.length} commands due to token limits)`
        : ''

    return `Execute a slash command within the main conversation

How slash commands work:
When you use this tool or when a user types a slash command, you will see <command-message>{name} is running…</command-message> followed by the expanded prompt. For example, if .claude/commands/foo.md contains "Print today's date", then /foo expands to that prompt in the next message.

Usage:
- \`command\` (required): The slash command to execute, including any arguments
- Example: \`command: "/review-pr 123"\`

IMPORTANT: Only use this tool for custom slash commands that appear in the Available Commands list below. Do NOT use for:
- Built-in CLI commands (like /help, /clear, etc.)
- Commands not shown in the list
- Commands you think might exist but aren't listed

${
  availableLines
    ? `Available Commands:
${availableLines}${truncatedNotice}
`
    : ''
}Notes:
- When a user requests multiple slash commands, execute each one sequentially and check for <command-message>{name} is running…</command-message> to verify each has been processed
- Do not invoke a command that is already running. For example, if you see <command-message>foo is running…</command-message>, do NOT use this tool with "/foo" - process the expanded prompt in the following message
- Only custom slash commands with descriptions are listed in Available Commands. If a user's command is not listed, ask them to check the slash command file and consult the docs.
`
  },
  renderToolUseMessage({ command }: Input, _options: { verbose: boolean }) {
    return command || ''
  },
  renderToolUseRejectedMessage() {
    return <FallbackToolUseRejectedMessage />
  },
  renderResultForAssistant(output: Output) {
    return `Launching command: /${output.commandName}`
  },
  async validateInput({ command }: Input, context) {
    const parsed = parseSlashCommand(command)
    if (!parsed) {
      return {
        result: false,
        message: `Invalid slash command format: ${command}`,
        errorCode: 1,
      }
    }

    const commands = context?.options?.commands ?? (await getCommands())

    const cmd = findCommand(parsed.commandName, commands)
    if (!cmd) {
      return {
        result: false,
        message: `Unknown slash command: ${parsed.commandName}`,
        errorCode: 2,
      }
    }

    if ((cmd as any).disableModelInvocation) {
      return {
        result: false,
        message: `Slash command ${parsed.commandName} cannot be used with ${TOOL_NAME_FOR_PROMPT} tool due to disable-model-invocation`,
        errorCode: 4,
      }
    }

    if ((cmd as any).disableNonInteractive) {
      return {
        result: false,
        message: `Slash command ${parsed.commandName} cannot be used with ${TOOL_NAME_FOR_PROMPT} tool because it is non-interactive`,
        errorCode: 6,
      }
    }

    if (cmd.type !== 'prompt') {
      return {
        result: false,
        message: `Slash command ${parsed.commandName} is not a prompt-based command`,
        errorCode: 5,
      }
    }

    return { result: true }
  },
  async *call({ command }: Input, context) {
    const parsed = parseSlashCommand(command)
    if (!parsed) {
      throw new Error(`Invalid slash command format: ${command}`)
    }

    const commands = context.options?.commands ?? (await getCommands())
    const cmd = findCommand(parsed.commandName, commands)
    if (!cmd) {
      throw new Error(`Unknown slash command: ${parsed.commandName}`)
    }
    if ((cmd as any).disableModelInvocation) {
      throw new Error(
        `Slash command ${parsed.commandName} cannot be used with ${TOOL_NAME_FOR_PROMPT} tool due to disable-model-invocation`,
      )
    }
    if ((cmd as any).disableNonInteractive) {
      throw new Error(
        `Slash command ${parsed.commandName} cannot be used with ${TOOL_NAME_FOR_PROMPT} tool because it is non-interactive`,
      )
    }
    if (cmd.type !== 'prompt') {
      throw new Error(
        `Unexpected ${cmd.type} command. Expected 'prompt' command. Use /${parsed.commandName} directly in the main conversation.`,
      )
    }

    const prompt = await cmd.getPromptForCommand(parsed.args)
    const expandedMessages: Message[] = prompt.map(msg => {
      const userMessage = createUserMessage(
        typeof msg.content === 'string'
          ? msg.content
          : msg.content
              .map(block => (block.type === 'text' ? block.text : ''))
              .join('\n'),
      )
      userMessage.options = {
        ...userMessage.options,
        isCustomCommand: true,
        commandName: cmd.userFacingName(),
        commandArgs: parsed.args,
      }
      return userMessage
    })

    const commandNameForMeta = cmd.userFacingName()
    const progressMessage = (cmd as any).progressMessage || 'running'
    const metaMessage =
      createUserMessage(`<command-name>${commandNameForMeta}</command-name>
<command-message>${commandNameForMeta} is ${progressMessage}…</command-message>
<command-args>${parsed.args}</command-args>`)

    const allowedTools: string[] = Array.isArray((cmd as any).allowedTools)
      ? (cmd as any).allowedTools
      : []
    const model = normalizeCommandModelName((cmd as any).model)
    const maxThinkingTokens: number | undefined =
      typeof (cmd as any).maxThinkingTokens === 'number'
        ? (cmd as any).maxThinkingTokens
        : undefined

    const output: Output = { success: true, commandName: parsed.commandName }

    yield {
      type: 'result' as const,
      data: output,
      resultForAssistant: this.renderResultForAssistant(output),
      newMessages: [metaMessage, ...expandedMessages],
      contextModifier:
        allowedTools.length > 0 || model || maxThinkingTokens !== undefined
          ? {
              modifyContext(ctx) {
                const next = { ...ctx }

                if (allowedTools.length > 0) {
                  const prev = Array.isArray(
                    (next.options as any)?.commandAllowedTools,
                  )
                    ? ((next.options as any).commandAllowedTools as string[])
                    : []
                  next.options = {
                    ...(next.options || {}),
                    commandAllowedTools: [
                      ...new Set([...prev, ...allowedTools]),
                    ],
                  }
                }

                if (model) {
                  next.options = { ...(next.options || {}), model }
                }

                if (maxThinkingTokens !== undefined) {
                  next.options = {
                    ...(next.options || {}),
                    maxThinkingTokens,
                  }
                }

                return next
              },
            }
          : undefined,
    }
  },
} satisfies Tool<typeof inputSchema, Output>

function parseSlashCommand(
  command: string,
): { commandName: string; args: string } | null {
  const trimmed = command.trim()
  if (!trimmed.startsWith('/')) return null
  const withoutSlash = trimmed.slice(1)
  const spaceIdx = withoutSlash.indexOf(' ')
  const commandName =
    spaceIdx === -1
      ? withoutSlash.trim()
      : withoutSlash.slice(0, spaceIdx).trim()
  if (!commandName) return null
  const args = spaceIdx === -1 ? '' : withoutSlash.slice(spaceIdx + 1).trim()
  return { commandName, args }
}

function findCommand(commandName: string, commands: any[]): any | null {
  return (
    commands.find(
      (c: any) =>
        c?.name === commandName ||
        c?.userFacingName?.() === commandName ||
        (Array.isArray(c?.aliases) && c.aliases.includes(commandName)),
    ) ?? null
  )
}
