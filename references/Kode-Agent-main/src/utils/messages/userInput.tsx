import { Box } from 'ink'
import { getCommand, hasCommand } from '@commands'
import { MalformedCommandError } from '@utils/text/errors'
import { logError } from '@utils/log'
import { resolve } from 'path'
import { lastX } from '@utils/text/generators'
import type { SetToolJSXFn, ToolUseContext } from '@tool'
import type { ContentBlockParam } from '@anthropic-ai/sdk/resources/index.mjs'
import { setCwd } from '@utils/state'
import { getCwd } from '@utils/state'
import chalk from 'chalk'
import * as React from 'react'
import { UserBashInputMessage } from '@components/messages/UserBashInputMessage'
import { Spinner } from '@components/Spinner'
import { BashTool } from '@tools/BashTool/BashTool'
import type { Message, UserMessage } from '@query'
import { NO_RESPONSE_REQUESTED, createAssistantMessage, createUserMessage } from './core'


export async function processUserInput(
  input: string,
  mode: 'bash' | 'prompt' | 'koding',
  setToolJSX: SetToolJSXFn,
  context: ToolUseContext & {
    setForkConvoWithMessagesOnTheNextRender: (
      forkConvoWithMessages: Message[],
    ) => void
    options?: {
      isKodingRequest?: boolean
      kodingContext?: string
    }
  },
  pastedImages: Array<{
    placeholder: string
    data: string
    mediaType: string
  }> | null,
): Promise<Message[]> {
  if (mode === 'bash') {
    const userMessage = createUserMessage(`<bash-input>${input}</bash-input>`)

    if (input.startsWith('cd ')) {
      const oldCwd = getCwd()
      const newCwd = resolve(getCwd(), input.slice(3).trim())
      try {
        await setCwd(newCwd)
        return [
          userMessage,
          createAssistantMessage(
            `<bash-stdout>Changed directory to ${chalk.bold(`${newCwd}/`)}</bash-stdout>`,
          ),
        ]
      } catch (e) {
        logError(e)
        return [
          userMessage,
          createAssistantMessage(
            `<bash-stderr>cwd error: ${e instanceof Error ? e.message : String(e)}</bash-stderr>`,
          ),
        ]
      }
    }

    setToolJSX({
      jsx: (
        <Box flexDirection="column" marginTop={1}>
          <UserBashInputMessage
            addMargin={false}
            param={{ text: `<bash-input>${input}</bash-input>`, type: 'text' }}
          />
          <Spinner />
        </Box>
      ),
      shouldHidePromptInput: false,
    })
    try {
      const validationResult = await BashTool.validateInput(
        { command: input },
        { commandSource: 'user_bash_mode' } as any,
      )
      if (!validationResult.result) {
        return [userMessage, createAssistantMessage(validationResult.message)]
      }
      const { data } = await lastX(
        BashTool.call({ command: input }, {
          ...(context as any),
          commandSource: 'user_bash_mode',
        } as any),
      )
      return [
        userMessage,
        createAssistantMessage(
          `<bash-stdout>${data.stdout}</bash-stdout><bash-stderr>${data.stderr}</bash-stderr>`,
        ),
      ]
    } catch (e) {
      return [
        userMessage,
        createAssistantMessage(
          `<bash-stderr>Command failed: ${e instanceof Error ? e.message : String(e)}</bash-stderr>`,
        ),
      ]
    } finally {
      setToolJSX(null)
    }
  }
  else if (mode === 'koding') {
    const userMessage = createUserMessage(
      `<koding-input>${input}</koding-input>`,
    )
    userMessage.options = {
      ...userMessage.options,
      isKodingRequest: true,
    }

    return [userMessage]
  }

  if (context.options?.disableSlashCommands !== true && input.startsWith('/')) {
    const words = input.slice(1).split(' ')
    let commandName = words[0]
    if (words.length > 1 && words[1] === '(MCP)') {
      commandName = commandName + ' (MCP)'
    }
    if (!commandName) {
      return [
        createAssistantMessage('Commands are in the form `/command [args]`'),
      ]
    }

    if (!hasCommand(commandName, context.options.commands)) {

      return [createUserMessage(input)]
    }

    const args = input.slice(commandName.length + 2)
    const newMessages = await getMessagesForSlashCommand(
      commandName,
      args,
      setToolJSX,
      context,
    )

    if (newMessages.length === 0) {
      return []
    }

    if (
      newMessages.length === 2 &&
      newMessages[0]!.type === 'user' &&
      newMessages[1]!.type === 'assistant' &&
      typeof newMessages[1]!.message.content === 'string' &&
      newMessages[1]!.message.content.startsWith('Unknown command:')
    ) {
      return newMessages
    }

    if (newMessages.length === 2) {
      return newMessages
    }


    return newMessages
  }


  const isKodingRequest = context.options?.isKodingRequest === true
  const kodingContextInfo = context.options?.kodingContext

  let userMessage: UserMessage

  let processedInput =
    isKodingRequest && kodingContextInfo
      ? `${kodingContextInfo}\n\n${input}`
      : input

  if (processedInput.includes('!`') || processedInput.includes('@')) {
    try {
      const { executeBashCommands } = await import('@services/customCommands')

      if (processedInput.includes('!`')) {
        processedInput = await executeBashCommands(processedInput)
      }

      if (processedInput.includes('@')) {
        const { processMentions } = await import('@services/mentionProcessor')
        await processMentions(processedInput)
      }
    } catch (error) {
      logError(error)
    }
  }

  if (pastedImages && pastedImages.length > 0) {
    const occurrences = pastedImages
      .map(img => ({ img, index: processedInput.indexOf(img.placeholder) }))
      .filter(o => o.index >= 0)
      .sort((a, b) => a.index - b.index)

    const blocks: ContentBlockParam[] = []
    let cursor = 0

    for (const { img, index } of occurrences) {
      const before = processedInput.slice(cursor, index)
      if (before) {
        blocks.push({ type: 'text', text: before })
      }
      blocks.push({
        type: 'image',
        source: {
          type: 'base64',
          media_type: img.mediaType,
          data: img.data,
        },
      } as any)
      cursor = index + img.placeholder.length
    }

    const after = processedInput.slice(cursor)
    if (after) {
      blocks.push({ type: 'text', text: after })
    }

    if (!blocks.some(b => b.type === 'text')) {
      blocks.push({ type: 'text', text: '' })
    }

    userMessage = createUserMessage(blocks)
  } else {
    userMessage = createUserMessage(processedInput)
  }

  if (isKodingRequest) {
    userMessage.options = {
      ...userMessage.options,
      isKodingRequest: true,
    }
  }

  return [userMessage]
}

async function getMessagesForSlashCommand(
  commandName: string,
  args: string,
  setToolJSX: SetToolJSXFn,
  context: ToolUseContext & {
    setForkConvoWithMessagesOnTheNextRender: (
      forkConvoWithMessages: Message[],
    ) => void
  },
): Promise<Message[]> {
  try {
    const command = getCommand(commandName, context.options.commands)
    switch (command.type) {
      case 'local-jsx': {
        return new Promise(resolve => {
          command
            .call(
              r => {
                setToolJSX(null)
                resolve([
                  createUserMessage(`<command-name>${command.userFacingName()}</command-name>
          <command-message>${command.userFacingName()}</command-message>
          <command-args>${args}</command-args>`),
                  r
                    ? createAssistantMessage(r)
                    : createAssistantMessage(NO_RESPONSE_REQUESTED),
                ])
              },
              context,
              args,
            )
            .then(jsx => {
              if (!jsx) return
              setToolJSX({ jsx, shouldHidePromptInput: true })
            })
        })
      }
      case 'local': {
        const userMessage =
          createUserMessage(`<command-name>${command.userFacingName()}</command-name>
        <command-message>${command.userFacingName()}</command-message>
        <command-args>${args}</command-args>`)

        try {
          const result = await command.call(args, {
            ...context,
            options: {
              commands: context.options.commands || [],
              tools: context.options.tools || [],
              slowAndCapableModel:
                context.options.slowAndCapableModel || 'main',
            },
          })

          return [
            userMessage,
            createAssistantMessage(
              `<local-command-stdout>${result}</local-command-stdout>`,
            ),
          ]
        } catch (e) {
          logError(e)
          return [
            userMessage,
            createAssistantMessage(
              `<local-command-stderr>${String(e)}</local-command-stderr>`,
            ),
          ]
        }
      }
      case 'prompt': {
        const commandName = command.userFacingName()
        const progressMessage = (command as any).progressMessage || 'running'
        const metaMessage =
          createUserMessage(`<command-name>${commandName}</command-name>
        <command-message>${commandName} is ${progressMessage}…</command-message>
        <command-args>${args}</command-args>`)

        const prompt = await command.getPromptForCommand(args)
        const expandedMessages = prompt.map(msg => {
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
            commandName: command.userFacingName(),
            commandArgs: args,
          }

          return userMessage
        })

        return [metaMessage, ...expandedMessages]
      }
    }
  } catch (e) {
    if (e instanceof MalformedCommandError) {
      return [createAssistantMessage(e.message)]
    }
    throw e
  }
}
