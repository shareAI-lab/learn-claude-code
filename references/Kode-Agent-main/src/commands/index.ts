import React from 'react'
import bug from './bug'
import clear from './clear'
import compact from './compact'
import compactThreshold from './compact-threshold'
import config from './config'
import cost from './cost'
import ctxViz from './ctx-viz'
import doctor from './doctor'
import help from './help'
import init from './init'
import listen from './listen'
import messagesDebug from './messages-debug'
import login from './login'
import logout from './logout'
import mcp from './mcp'
import plugin from './plugin'
import outputStyle from './output-style'
import * as model from './model'
import modelstatus from './modelstatus'
import onboarding from './onboarding'
import prComments from './pr-comments'
import refreshCommands from './refresh-commands'
import releaseNotes from './release-notes'
import review from './review'
import rename from './rename'
import statusline from './statusline'
import tag from './tag'
import todos from './todos'
import type { Tool, ToolUseContext } from '@tool'
import resume from './resume'
import agents from './agents'
import { getMCPCommands } from '@services/mcpClient'
import { loadCustomCommands } from '@services/customCommands'
import type { MessageParam } from '@anthropic-ai/sdk/resources/index.mjs'
import { memoize } from 'lodash-es'
import type { Message } from '@query'
import { isAnthropicAuthEnabled } from '@utils/identity/auth'

type PromptCommand = {
  type: 'prompt'
  progressMessage: string
  argNames?: string[]
  getPromptForCommand(args: string): Promise<MessageParam[]>
}

type LocalCommand = {
  type: 'local'
  call(
    args: string,
    context: {
      options: {
        commands: Command[]
        tools: Tool[]
        slowAndCapableModel: string
      }
      abortController: AbortController
      setForkConvoWithMessagesOnTheNextRender: (
        forkConvoWithMessages: Message[],
      ) => void
    },
  ): Promise<string>
}

type LocalJSXCommand = {
  type: 'local-jsx'
  call(
    onDone: (result?: string) => void,
    context: ToolUseContext & {
      setForkConvoWithMessagesOnTheNextRender: (
        forkConvoWithMessages: Message[],
      ) => void
    },
    args?: string,
  ): Promise<React.ReactNode>
}

export type Command = {
  description: string
  isEnabled: boolean
  isHidden: boolean
  name: string
  argumentHint?: string
  aliases?: string[]
  disableNonInteractive?: boolean
  allowedTools?: string[]
  userFacingName(): string
} & (PromptCommand | LocalCommand | LocalJSXCommand)

const INTERNAL_ONLY_COMMANDS = [ctxViz, resume, listen, messagesDebug]

const COMMANDS = memoize((): Command[] => [
  agents,
  clear,
  compact,
  compactThreshold,
  config,
  cost,
  doctor,
  help,
  init,
  outputStyle,
  statusline,
  mcp,
  plugin,
  model,
  modelstatus,
  onboarding,
  prComments,
  rename,
  tag,
  refreshCommands,
  releaseNotes,
  bug,
  review,
  todos,
  ...(isAnthropicAuthEnabled() ? [logout, login()] : []),
  ...INTERNAL_ONLY_COMMANDS,
])

export const getCommands = memoize(async (): Promise<Command[]> => {
  const [mcpCommands, customCommands] = await Promise.all([
    getMCPCommands(),
    loadCustomCommands(),
  ])

  return [...mcpCommands, ...customCommands, ...COMMANDS()].filter(
    _ => _.isEnabled,
  )
})

export function hasCommand(commandName: string, commands: Command[]): boolean {
  return commands.some(
    _ => _.userFacingName() === commandName || _.aliases?.includes(commandName),
  )
}

export function getCommand(commandName: string, commands: Command[]): Command {
  const command = commands.find(
    _ => _.userFacingName() === commandName || _.aliases?.includes(commandName),
  ) as Command | undefined
  if (!command) {
    throw ReferenceError(
      `Command ${commandName} not found. Available commands: ${commands
        .map(_ => {
          const name = _.userFacingName()
          return _.aliases ? `${name} (aliases: ${_.aliases.join(', ')})` : name
        })
        .join(', ')}`,
    )
  }

  return command
}
