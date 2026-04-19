import type { CanUseToolFn } from '@kode-types/canUseTool'
import type { Tool, ToolUseContext } from '@tool'
import { BashTool, inputSchema } from '@tools/BashTool/BashTool'
import { EnterPlanModeTool } from '@tools/agent/PlanModeTool/EnterPlanModeTool'
import { ExitPlanModeTool } from '@tools/agent/PlanModeTool/ExitPlanModeTool'
import { FileEditTool } from '@tools/FileEditTool/FileEditTool'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import { GlobTool } from '@tools/GlobTool/GlobTool'
import { GrepTool } from '@tools/search/GrepTool/GrepTool'
import { KillShellTool } from '@tools/KillShellTool/KillShellTool'
import { NotebookEditTool } from '@tools/NotebookEditTool/NotebookEditTool'
import { ListMcpResourcesTool } from '@tools/mcp/ListMcpResourcesTool/ListMcpResourcesTool'
import { ReadMcpResourceTool } from '@tools/mcp/ReadMcpResourceTool/ReadMcpResourceTool'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'
import { WebSearchTool } from '@tools/network/WebSearchTool/WebSearchTool'
import { AskUserQuestionTool } from '@tools/interaction/AskUserQuestionTool/AskUserQuestionTool'
import { SlashCommandTool } from '@tools/interaction/SlashCommandTool/SlashCommandTool'
import { SkillTool } from '@tools/ai/SkillTool/SkillTool'
import { TodoWriteTool } from '@tools/interaction/TodoWriteTool/TodoWriteTool'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'
import { AbortError } from '@utils/text/errors'
import { logError } from '@utils/log'
import { grantWritePermissionForPath } from '@utils/permissions/filesystem'
import { getCwd } from '@utils/state'
import { PRODUCT_NAME } from '@constants/product'
import {
  getPlanConversationKey,
  getPlanFilePath,
  isPlanModeEnabled,
} from '@utils/plan/planMode'
import { getPermissionMode } from '@utils/permissions/permissionModeState'
import { isAbsolute, resolve } from 'path'
import { homedir } from 'os'
import { minimatch } from 'minimatch'
import { persistToolPermissionUpdateToDisk } from '@utils/permissions/toolPermissionSettings'
import { applyToolPermissionContextUpdateForConversationKey } from '@utils/permissions/toolPermissionContextState'
import {
  expandSymlinkPaths,
  getSpecialAllowedReadReason,
  getWriteSafetyCheckForPath,
  hasSuspiciousWindowsPathPattern,
  isPathInWorkingDirectories,
  isPlanFileForContext,
  matchPermissionRuleForPath,
  suggestFilePermissionUpdates,
} from '@utils/permissions/fileToolPermissionEngine'
import { getBunShellSandboxPlan } from '@utils/sandbox/bunShellSandboxPlan'
import {
  checkBashPermissions,
  checkBashPermissionsAutoAllowedBySandbox,
} from '@utils/permissions/bashToolPermissionEngine'
import {
  createDefaultToolPermissionContext,
  type ToolPermissionContextUpdate,
} from '@kode-types/toolPermissionContext'
import { parseMcpToolName } from '@utils/permissions/ruleString'
import type { PermissionResult } from '../ui-helpers'
import {
  PLAN_MODE_ALLOWED_NON_READONLY_TOOLS,
  bashToolHasPermission,
  getPermissionKey,
  isSafeBashCommand,
} from '../rules'

function parseBoolLike(value: string | undefined): boolean {
  if (!value) return false
  const v = value.trim().toLowerCase()
  return ['1', 'true', 'yes', 'y', 'on', 'enable', 'enabled'].includes(v)
}

function flattenPermissionRuleGroups(
  groups: Partial<Record<string, string[]>> | undefined,
): string[] {
  if (!groups) return []
  const out: string[] = []
  for (const rules of Object.values(groups)) {
    if (!Array.isArray(rules)) continue
    for (const rule of rules) {
      if (typeof rule !== 'string') continue
      out.push(rule)
    }
  }
  return out
}

function isAllowedToolUseInPlanMode(
  tool: Tool,
  input: { [k: string]: unknown },
  context: ToolUseContext,
): boolean {
  if (tool.isReadOnly(input as never)) return true
  if (PLAN_MODE_ALLOWED_NON_READONLY_TOOLS.has(tool.name)) return true

  if (tool === FileWriteTool || tool === FileEditTool) {
    const filePath = typeof input.file_path === 'string' ? input.file_path : ''
    if (!filePath) return false

    const conversationKey = getPlanConversationKey(context)
    const allowedPlanFile = getPlanFilePath(context.agentId, conversationKey)
    const resolvedFilePath = isAbsolute(filePath)
      ? resolve(filePath)
      : resolve(getCwd(), filePath)
    return resolvedFilePath === resolve(allowedPlanFile)
  }

  return false
}

export const hasPermissionsToUseTool: CanUseToolFn = async (
  tool,
  input,
  context,
  _assistantMessage,
): Promise<PermissionResult> => {
  const permissionMode = getPermissionMode(context)
  const isDontAskMode = permissionMode === 'dontAsk'
  const shouldAvoidPermissionPrompts =
    context.options?.shouldAvoidPermissionPrompts === true
  const safeMode = Boolean(context.options?.safeMode ?? context.safeMode)
  const requiresUserInteraction =
    tool.requiresUserInteraction?.(input as never) ?? false
  const dontAskDenied: PermissionResult = {
    result: false,
    message: `Permission to use ${tool.name} has been auto-denied in dontAsk mode.`,
    shouldPromptUser: false,
  }
  const promptsUnavailableDenied: PermissionResult = {
    result: false,
    message: `Permission to use ${tool.name} has been auto-denied (prompts unavailable).`,
    shouldPromptUser: false,
  }

  if (permissionMode === 'bypassPermissions' && !requiresUserInteraction) {
    const bypassSafetyFloor =
      parseBoolLike(process.env.KODE_BYPASS_SAFETY_FLOOR) && !safeMode

    if (!bypassSafetyFloor) {
      const denyIfUnsafeWrite = (toolPath: string): PermissionResult | null => {
        const safety = getWriteSafetyCheckForPath(toolPath)
        if ('message' in safety) {
          return {
            result: false,
            message: safety.message,
            shouldPromptUser: false,
          }
        }
        return null
      }

      if (tool === FileWriteTool || tool === FileEditTool) {
        const filePath =
          typeof (input as any).file_path === 'string'
            ? String((input as any).file_path)
            : ''
        if (filePath) {
          const denied = denyIfUnsafeWrite(filePath)
          if (denied) return denied
        }
      }

      if (tool === NotebookEditTool) {
        const notebookPath =
          typeof (input as any).notebook_path === 'string'
            ? String((input as any).notebook_path)
            : ''
        if (notebookPath) {
          const denied = denyIfUnsafeWrite(notebookPath)
          if (denied) return denied
        }
      }
    }

    return { result: true }
  }

  if (requiresUserInteraction) {
    if (isDontAskMode) {
      return dontAskDenied
    }
    if (shouldAvoidPermissionPrompts) {
      return promptsUnavailableDenied
    }
    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
    }
  }

  if (context.abortController.signal.aborted) {
    throw new AbortError()
  }

  const isFilesystemLikeTool =
    tool === FileReadTool ||
    tool === FileEditTool ||
    tool === FileWriteTool ||
    tool === NotebookEditTool ||
    tool === GlobTool ||
    tool === GrepTool

  if (!isFilesystemLikeTool) {
    try {
      if (!tool.needsPermissions(input as never)) {
        return { result: true }
      }
    } catch (e) {
      logError(`Error checking permissions: ${e}`)
      return { result: false, message: 'Error checking permissions' }
    }
  }

  const projectConfig = getCurrentProjectConfig()
  const toolPermissionContext = context.options?.toolPermissionContext
  const allowedTools = toolPermissionContext
    ? flattenPermissionRuleGroups(toolPermissionContext.alwaysAllowRules)
    : (projectConfig.allowedTools ?? [])
  const deniedTools = toolPermissionContext
    ? flattenPermissionRuleGroups(toolPermissionContext.alwaysDenyRules)
    : (projectConfig.deniedTools ?? [])
  const askedTools = toolPermissionContext
    ? flattenPermissionRuleGroups(toolPermissionContext.alwaysAskRules)
    : (projectConfig.askedTools ?? [])
  const commandAllowedTools = Array.isArray(
    context.options?.commandAllowedTools,
  )
    ? context.options!.commandAllowedTools!
    : []
  const effectiveAllowedTools = [
    ...new Set([...allowedTools, ...commandAllowedTools]),
  ]
  const effectiveDeniedTools = [...new Set([...deniedTools])]
  const effectiveAskedTools = [...new Set([...askedTools])]
  if (tool === BashTool && effectiveAllowedTools.includes(BashTool.name)) {
    return { result: true }
  }

  const effectiveToolPermissionContext =
    context.options?.toolPermissionContext ??
    (() => {
      const fallback = createDefaultToolPermissionContext({
        isBypassPermissionsModeAvailable: !(context.options?.safeMode ?? false),
      })
      fallback.mode = permissionMode
      if (effectiveAllowedTools.length > 0) {
        fallback.alwaysAllowRules.localSettings = effectiveAllowedTools
      }
      if (effectiveDeniedTools.length > 0) {
        fallback.alwaysDenyRules.localSettings = effectiveDeniedTools
      }
      if (effectiveAskedTools.length > 0) {
        fallback.alwaysAskRules.localSettings = effectiveAskedTools
      }
      return fallback
    })()

  const checkEditPermissionForPath = (toolPath: string): PermissionResult => {
    const candidates = expandSymlinkPaths(toolPath)

    for (const candidate of candidates) {
      const deniedRule = matchPermissionRuleForPath({
        inputPath: candidate,
        toolPermissionContext: effectiveToolPermissionContext,
        operation: 'edit',
        behavior: 'deny',
      })
      if (deniedRule) {
        return {
          result: false,
          message: `Permission to edit ${toolPath} has been denied.`,
          shouldPromptUser: false,
        }
      }
    }

    if (isPlanFileForContext({ inputPath: toolPath, context })) {
      return { result: true }
    }

    const safety = getWriteSafetyCheckForPath(toolPath)
    if ('message' in safety) {
      return { result: false, message: safety.message }
    }

    for (const candidate of candidates) {
      const askedRule = matchPermissionRuleForPath({
        inputPath: candidate,
        toolPermissionContext: effectiveToolPermissionContext,
        operation: 'edit',
        behavior: 'ask',
      })
      if (askedRule) {
        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to write to ${toolPath}, but you haven't granted it yet.`,
        }
      }
    }

    const inWorkingDirs = isPathInWorkingDirectories(
      toolPath,
      effectiveToolPermissionContext,
    )
    if (
      effectiveToolPermissionContext.mode === 'acceptEdits' &&
      inWorkingDirs
    ) {
      return { result: true }
    }

    const allowRule = matchPermissionRuleForPath({
      inputPath: toolPath,
      toolPermissionContext: effectiveToolPermissionContext,
      operation: 'edit',
      behavior: 'allow',
    })
    if (allowRule) {
      return { result: true }
    }

    return {
      result: false,
      message: `${PRODUCT_NAME} requested permissions to write to ${toolPath}, but you haven't granted it yet.`,
      suggestions: suggestFilePermissionUpdates({
        inputPath: toolPath,
        operation: 'write',
        toolPermissionContext: effectiveToolPermissionContext,
      }),
    }
  }

  const permissionResult: PermissionResult = await (async () => {
    switch (tool) {
      case BashTool: {
        const { command, dangerouslyDisableSandbox } = inputSchema.parse(input)
        const trimmed = command.trim()
        if (isSafeBashCommand(trimmed)) {
          return { result: true }
        }

        const sandboxPlan = getBunShellSandboxPlan({
          command: trimmed,
          dangerouslyDisableSandbox: dangerouslyDisableSandbox === true,
          toolUseContext: context,
        })

        if (sandboxPlan.shouldBlockUnsandboxedCommand) {
          return {
            result: false,
            message:
              'This command must run in the sandbox, but sandboxed execution is not available.',
            shouldPromptUser: false,
          }
        }

        if (sandboxPlan.shouldAutoAllowBashPermissions) {
          if (effectiveToolPermissionContext.mode !== 'acceptEdits') {
            return await checkBashPermissions({
              command: trimmed,
              toolPermissionContext: effectiveToolPermissionContext,
              toolUseContext: context,
            })
          }
          return checkBashPermissionsAutoAllowedBySandbox({
            command: trimmed,
            toolPermissionContext: effectiveToolPermissionContext,
          })
        }

        return await checkBashPermissions({
          command: trimmed,
          toolPermissionContext: effectiveToolPermissionContext,
          toolUseContext: context,
        })
      }
      case SlashCommandTool: {
        const command =
          typeof (input as any).command === 'string'
            ? (input as any).command
            : ''
        const trimmed = command.trim()
        const exactKey = getPermissionKey(tool, { command: trimmed }, null)
        if (effectiveDeniedTools.includes(exactKey)) {
          return {
            result: false,
            message: `Permission to use ${tool.name}(${trimmed}) has been denied.`,
            shouldPromptUser: false,
          }
        }
        if (effectiveAskedTools.includes(exactKey)) {
          return {
            result: false,
            message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
          }
        }
        if (effectiveAllowedTools.includes(exactKey)) {
          return { result: true }
        }

        const firstWord = trimmed.split(/\s+/)[0]
        if (firstWord && firstWord.startsWith('/')) {
          const prefixKey = getPermissionKey(
            tool,
            { command: trimmed },
            firstWord,
          )
          if (effectiveDeniedTools.includes(prefixKey)) {
            return {
              result: false,
              message: `Permission to use ${tool.name}(${firstWord}:*) has been denied.`,
              shouldPromptUser: false,
            }
          }
          if (effectiveAskedTools.includes(prefixKey)) {
            return {
              result: false,
              message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
            }
          }
          if (effectiveAllowedTools.includes(prefixKey)) {
            return { result: true }
          }
        }

        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
        }
      }
      case SkillTool: {
	        const rawSkill =
	          typeof (input as any).skill === 'string' ? (input as any).skill : ''
	        const skillName = rawSkill.trim().replace(/^\//, '')
	        const exactKey = getPermissionKey(tool, { skill: skillName }, null)
	        if (effectiveDeniedTools.includes(exactKey)) {
	          return {
	            result: false,
            message: `Permission to use ${tool.name}(${skillName}) has been denied.`,
            shouldPromptUser: false,
          }
        }
        if (effectiveAskedTools.includes(exactKey)) {
          return {
            result: false,
            message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
          }
        }
        if (effectiveAllowedTools.includes(exactKey)) {
          return { result: true }
        }

        const prefixes = getSkillPrefixes(skillName)
        for (const prefix of prefixes) {
          const prefixKey = getPermissionKey(tool, { skill: skillName }, prefix)
          if (effectiveDeniedTools.includes(prefixKey)) {
            return {
              result: false,
              message: `Permission to use ${tool.name}(${prefix}:*) has been denied.`,
              shouldPromptUser: false,
            }
          }
        }

        for (const prefix of prefixes) {
          const prefixKey = getPermissionKey(tool, { skill: skillName }, prefix)
          if (effectiveAskedTools.includes(prefixKey)) {
            return {
              result: false,
              message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
            }
          }
        }

        for (const prefix of prefixes) {
          const prefixKey = getPermissionKey(tool, { skill: skillName }, prefix)
          if (effectiveAllowedTools.includes(prefixKey)) {
            return { result: true }
          }
        }

        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
        }
      }
      case FileReadTool:
      case GlobTool:
      case GrepTool: {
        const rawPath =
          tool === FileReadTool
            ? typeof (input as any).file_path === 'string'
              ? (input as any).file_path
              : ''
            : typeof (input as any).path === 'string'
              ? (input as any).path
              : ''
        const toolPath = rawPath || getCwd()

        const candidates = expandSymlinkPaths(toolPath)
        for (const candidate of candidates) {
          if (candidate.startsWith('\\\\') || candidate.startsWith('//')) {
            return {
              result: false,
              message: `${PRODUCT_NAME} requested permissions to read from ${toolPath}, which appears to be a UNC path that could access network resources.`,
            }
          }
        }
        for (const candidate of candidates) {
          if (hasSuspiciousWindowsPathPattern(candidate)) {
            return {
              result: false,
              message: `${PRODUCT_NAME} requested permissions to read from ${toolPath}, which contains a suspicious Windows path pattern that requires manual approval.`,
            }
          }
        }

        for (const candidate of candidates) {
          const deniedRule = matchPermissionRuleForPath({
            inputPath: candidate,
            toolPermissionContext: effectiveToolPermissionContext,
            operation: 'read',
            behavior: 'deny',
          })
          if (deniedRule) {
            return {
              result: false,
              message: `Permission to read ${toolPath} has been denied.`,
              shouldPromptUser: false,
            }
          }
        }

        for (const candidate of candidates) {
          const askedRule = matchPermissionRuleForPath({
            inputPath: candidate,
            toolPermissionContext: effectiveToolPermissionContext,
            operation: 'read',
            behavior: 'ask',
          })
          if (askedRule) {
            return {
              result: false,
              message: `${PRODUCT_NAME} requested permissions to read from ${toolPath}, but you haven't granted it yet.`,
            }
          }
        }

        const editDecision = checkEditPermissionForPath(toolPath)
        if (editDecision.result === true) {
          return { result: true }
        }

        if (
          isPathInWorkingDirectories(toolPath, effectiveToolPermissionContext)
        ) {
          return { result: true }
        }

        const specialReason = getSpecialAllowedReadReason({
          inputPath: toolPath,
          context,
        })
        if (specialReason) {
          return { result: true }
        }

        const allowRule = matchPermissionRuleForPath({
          inputPath: toolPath,
          toolPermissionContext: effectiveToolPermissionContext,
          operation: 'read',
          behavior: 'allow',
        })
        if (allowRule) {
          return { result: true }
        }

        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to read from ${toolPath}, but you haven't granted it yet.`,
          suggestions: suggestFilePermissionUpdates({
            inputPath: toolPath,
            operation: 'read',
            toolPermissionContext: effectiveToolPermissionContext,
          }),
        }
      }
      case FileEditTool:
      case FileWriteTool:
      case NotebookEditTool: {
        const targetPath =
          tool === NotebookEditTool
            ? typeof (input as any).notebook_path === 'string'
              ? (input as any).notebook_path
              : ''
            : typeof (input as any).file_path === 'string'
              ? (input as any).file_path
              : ''
        const toolPath = targetPath || getCwd()
        return checkEditPermissionForPath(toolPath)
      }
      case WebFetchTool: {
        const permissionKey = getPermissionKey(tool, input, null)
        const openParenIndex = permissionKey.indexOf('(')
        const actualRuleContent =
          openParenIndex !== -1 && permissionKey.endsWith(')')
            ? permissionKey.slice(openParenIndex + 1, -1)
            : ''
        const actualHostname = actualRuleContent.startsWith('domain:')
          ? actualRuleContent.slice('domain:'.length)
          : null

        const matchesWebFetchRule = (rule: string): boolean => {
          if (rule === WebFetchTool.name) return true
          const open = rule.indexOf('(')
          if (open === -1 || !rule.endsWith(')')) return false
          const name = rule.slice(0, open)
          if (name !== WebFetchTool.name) return false
          const ruleContent = rule.slice(open + 1, -1).trim()
          if (!ruleContent) return false
          if (ruleContent.startsWith('domain:') && actualHostname !== null) {
            const hostPattern = ruleContent.slice('domain:'.length).trim()
            if (!hostPattern) return false
            return minimatch(actualHostname, hostPattern, {
              nocase: true,
              dot: true,
            })
          }
          return ruleContent === actualRuleContent
        }

        if (effectiveDeniedTools.some(matchesWebFetchRule)) {
          return {
            result: false,
            message: `Permission to use ${tool.name} has been denied.`,
            shouldPromptUser: false,
          }
        }
        if (effectiveAskedTools.some(matchesWebFetchRule)) {
          return {
            result: false,
            message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
          }
        }
        if (effectiveAllowedTools.some(matchesWebFetchRule)) {
          return { result: true }
        }

        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
        }
      }
      case WebSearchTool: {
        const permissionKey = getPermissionKey(tool, input, null)
        const matchesWebSearchRule = (rule: string): boolean => {
          if (rule === WebSearchTool.name) return true
          return rule === permissionKey
        }

        if (effectiveDeniedTools.some(matchesWebSearchRule)) {
          return {
            result: false,
            message: `Permission to use ${tool.name} has been denied.`,
            shouldPromptUser: false,
          }
        }
        if (effectiveAskedTools.some(matchesWebSearchRule)) {
          return {
            result: false,
            message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
          }
        }
        if (effectiveAllowedTools.some(matchesWebSearchRule)) {
          return { result: true }
        }

        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
        }
      }
      default: {
        const permissionKey = getPermissionKey(tool, input, null)
        const matchesToolRule = (rule: string): boolean => {
          if (rule === permissionKey) return true

          const parsedTool = parseMcpToolName(permissionKey)
          if (!parsedTool) return false

          const parsedRule = parseMcpToolName(rule)
          if (!parsedRule) return false
          return (
            parsedRule.serverName === parsedTool.serverName &&
            parsedRule.toolName === '*'
          )
        }

        if (effectiveDeniedTools.some(matchesToolRule)) {
          return {
            result: false,
            message: `Permission to use ${tool.name} has been denied.`,
            shouldPromptUser: false,
          }
        }
        if (effectiveAskedTools.some(matchesToolRule)) {
          return {
            result: false,
            message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
          }
        }
        if (effectiveAllowedTools.some(matchesToolRule)) {
          return { result: true }
        }

        return {
          result: false,
          message: `${PRODUCT_NAME} requested permissions to use ${tool.name}, but you haven't granted it yet.`,
        }
      }
    }
  })()

  if (
    isDontAskMode &&
    permissionResult.result === false &&
    permissionResult.shouldPromptUser !== false
  ) {
    return dontAskDenied
  }

  if (
    shouldAvoidPermissionPrompts &&
    permissionResult.result === false &&
    permissionResult.shouldPromptUser !== false
  ) {
    return promptsUnavailableDenied
  }

  return permissionResult
}

function normalizeGlobPath(p: string): string {
  return p.replace(/\\/g, '/')
}

function resolveAbsolutePathForPermission(p: string): string {
  const trimmed = String(p || '').trim()
  if (!trimmed) return resolve(getCwd())
  return isAbsolute(trimmed) ? resolve(trimmed) : resolve(getCwd(), trimmed)
}

function resolvePermissionPathPattern(pattern: string): string {
  const trimmed = pattern.trim()
  if (!trimmed) return trimmed

  if (trimmed === '~') {
    return resolve(homedir())
  }
  if (trimmed.startsWith('~/') || trimmed.startsWith('~\\')) {
    return resolve(homedir(), trimmed.slice(2))
  }

  return isAbsolute(trimmed) ? resolve(trimmed) : resolve(getCwd(), trimmed)
}

function toolRuleMatchesPath(
  rule: string,
  toolName: string,
  absolutePath: string,
): boolean {
  if (rule === toolName) return true
  const openParenIndex = rule.indexOf('(')
  if (openParenIndex === -1 || !rule.endsWith(')')) return false

  const name = rule.slice(0, openParenIndex)
  if (name !== toolName) return false

  const ruleContent = rule.slice(openParenIndex + 1, -1).trim()
  if (!ruleContent) return false

  const absolutePattern = resolvePermissionPathPattern(ruleContent)
  return minimatch(
    normalizeGlobPath(absolutePath),
    normalizeGlobPath(absolutePattern),
    { dot: true, nocase: process.platform === 'win32' },
  )
}

function getSkillPrefixes(skillName: string): string[] {
  const parts = skillName
    .split(':')
    .map(p => p.trim())
    .filter(Boolean)
  if (parts.length <= 1) return []
  return parts.slice(0, -1).map((_, idx) => parts.slice(0, idx + 1).join(':'))
}
