import type { Tool, ToolUseContext } from '@tool'
import { getPermissionKey } from './permissionKey'
import { getCommandSubcommandPrefix, splitCommand } from '@utils/commands'
import { AbortError } from '@utils/text/errors'
import { getCwd } from '@utils/state'
import { PRODUCT_NAME } from '@constants/product'
import type { PermissionResult } from '../ui-helpers'

const SAFE_COMMANDS = new Set([
  'git status',
  'git diff',
  'git log',
  'git branch',
  'pwd',
  'tree',
  'date',
  'which',
])

export function isSafeBashCommand(command: string): boolean {
  return SAFE_COMMANDS.has(command)
}

export const bashToolCommandHasExactMatchPermission = (
  tool: Tool,
  command: string,
  allowedTools: string[],
): boolean => {
  if (isSafeBashCommand(command)) {
    return true
  }
  if (allowedTools.includes(getPermissionKey(tool, { command }, null))) {
    return true
  }
  if (allowedTools.includes(getPermissionKey(tool, { command }, command))) {
    return true
  }
  return false
}

const bashToolCommandHasExplicitRule = (
  tool: Tool,
  command: string,
  prefix: string | null,
  rules: string[],
): boolean => {
  if (rules.includes(getPermissionKey(tool, { command }, null))) {
    return true
  }
  if (rules.includes(getPermissionKey(tool, { command }, command))) {
    return true
  }
  if (prefix && rules.includes(getPermissionKey(tool, { command }, prefix))) {
    return true
  }
  return false
}

export const bashToolCommandHasPermission = (
  tool: Tool,
  command: string,
  prefix: string | null,
  allowedTools: string[],
): boolean => {
  if (bashToolCommandHasExactMatchPermission(tool, command, allowedTools)) {
    return true
  }
  return allowedTools.includes(getPermissionKey(tool, { command }, prefix))
}

export const bashToolHasPermission = async (
  tool: Tool,
  command: string,
  context: ToolUseContext,
  allowedTools: string[],
  deniedTools: string[] = [],
  askedTools: string[] = [],
  getCommandSubcommandPrefixFn = getCommandSubcommandPrefix,
): Promise<PermissionResult> => {
  const trimmedCommand = command.trim()
  const exactKey = getPermissionKey(tool, { command: trimmedCommand }, null)
  if (deniedTools.includes(exactKey)) {
    return {
      result: false,
      message: `Permission to use ${tool.name} with command ${trimmedCommand} has been denied.`,
      shouldPromptUser: false,
    }
  }
  if (askedTools.includes(exactKey)) {
    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
    }
  }

  if (
    bashToolCommandHasExactMatchPermission(tool, trimmedCommand, allowedTools)
  ) {
    return { result: true }
  }

  const subCommands = splitCommand(trimmedCommand).filter(_ => {
    if (_ === `cd ${getCwd()}`) {
      return false
    }
    return true
  })
  const commandSubcommandPrefix = await getCommandSubcommandPrefixFn(
    trimmedCommand,
    context.abortController.signal,
  )
  if (context.abortController.signal.aborted) {
    throw new AbortError()
  }

  if (commandSubcommandPrefix === null) {
    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
    }
  }

  if (commandSubcommandPrefix.commandInjectionDetected) {
    if (
      bashToolCommandHasExplicitRule(tool, trimmedCommand, null, deniedTools)
    ) {
      return {
        result: false,
        message: `Permission to use ${tool.name} with command ${trimmedCommand} has been denied.`,
        shouldPromptUser: false,
      }
    }
    if (bashToolCommandHasExplicitRule(tool, trimmedCommand, null, askedTools)) {
      return {
        result: false,
        message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
      }
    }
    if (
      bashToolCommandHasExactMatchPermission(tool, trimmedCommand, allowedTools)
    ) {
      return { result: true }
    } else {
      return {
        result: false,
        message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
      }
    }
  }

  if (subCommands.length < 2) {
    if (
      bashToolCommandHasExplicitRule(
        tool,
        trimmedCommand,
        commandSubcommandPrefix.commandPrefix,
        deniedTools,
      )
    ) {
      return {
        result: false,
        message: `Permission to use ${tool.name} with command ${trimmedCommand} has been denied.`,
        shouldPromptUser: false,
      }
    }
    if (
      bashToolCommandHasExplicitRule(
        tool,
        trimmedCommand,
        commandSubcommandPrefix.commandPrefix,
        askedTools,
      )
    ) {
      return {
        result: false,
        message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
      }
    }

    if (
      bashToolCommandHasPermission(
        tool,
        trimmedCommand,
        commandSubcommandPrefix.commandPrefix,
        allowedTools,
      )
    ) {
      return { result: true }
    }

    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
    }
  }

  const deniedSubcommand = subCommands.find(subCommand => {
    const prefixResult =
      commandSubcommandPrefix.subcommandPrefixes.get(subCommand)
    if (!prefixResult || prefixResult.commandInjectionDetected) return false
    return bashToolCommandHasExplicitRule(
      tool,
      subCommand,
      prefixResult.commandPrefix,
      deniedTools,
    )
  })
  if (deniedSubcommand) {
    return {
      result: false,
      message: `Permission to use ${tool.name} with command ${deniedSubcommand.trim()} has been denied.`,
      shouldPromptUser: false,
    }
  }

  const askedSubcommand = subCommands.find(subCommand => {
    const prefixResult =
      commandSubcommandPrefix.subcommandPrefixes.get(subCommand)
    if (!prefixResult || prefixResult.commandInjectionDetected) return false
    return bashToolCommandHasExplicitRule(
      tool,
      subCommand,
      prefixResult.commandPrefix,
      askedTools,
    )
  })
  if (askedSubcommand) {
    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
    }
  }

  return {
    result: false,
    message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
  }
}
