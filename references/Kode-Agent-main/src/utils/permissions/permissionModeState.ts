import type { ToolUseContext } from '@tool'
import type { PermissionMode } from '@kode-types/permissionMode'

const DEFAULT_CONVERSATION_KEY = 'default'

const permissionModeByConversationKey = new Map<string, PermissionMode>()

function getConversationKey(context?: Pick<ToolUseContext, 'options'>): string {
  const messageLogName =
    context?.options?.messageLogName ?? DEFAULT_CONVERSATION_KEY
  const forkNumber = context?.options?.forkNumber ?? 0
  return `${messageLogName}:${forkNumber}`
}

export function getPermissionModeForConversationKey(options: {
  conversationKey: string
  isBypassPermissionsModeAvailable: boolean
}): PermissionMode {
  const existing = permissionModeByConversationKey.get(options.conversationKey)
  if (existing) {
    if (
      existing === 'bypassPermissions' &&
      !options.isBypassPermissionsModeAvailable
    ) {
      permissionModeByConversationKey.set(options.conversationKey, 'default')
      return 'default'
    }
    return existing
  }

  permissionModeByConversationKey.set(options.conversationKey, 'default')
  return 'default'
}

export function setPermissionModeForConversationKey(options: {
  conversationKey: string
  mode: PermissionMode
}): void {
  permissionModeByConversationKey.set(options.conversationKey, options.mode)
}

export function getPermissionMode(context?: ToolUseContext): PermissionMode {
  const conversationKey = getConversationKey(context)
  const safeMode = context?.options?.safeMode ?? false

  const fromToolPermissionContext =
    context?.options?.toolPermissionContext?.mode
  if (
    fromToolPermissionContext === 'default' ||
    fromToolPermissionContext === 'acceptEdits' ||
    fromToolPermissionContext === 'plan' ||
    fromToolPermissionContext === 'dontAsk' ||
    fromToolPermissionContext === 'bypassPermissions'
  ) {
    if (fromToolPermissionContext === 'bypassPermissions' && safeMode) {
      return 'default'
    }
    return fromToolPermissionContext
  }

  const override = context?.options?.permissionMode
  if (
    override === 'default' ||
    override === 'acceptEdits' ||
    override === 'plan' ||
    override === 'dontAsk' ||
    override === 'bypassPermissions'
  ) {
    if (override === 'bypassPermissions' && safeMode) {
      return 'default'
    }
    return override
  }

  return getPermissionModeForConversationKey({
    conversationKey,
    isBypassPermissionsModeAvailable: !safeMode,
  })
}

export function setPermissionMode(
  context: ToolUseContext,
  mode: PermissionMode,
): void {
  const conversationKey = getConversationKey(context)
  permissionModeByConversationKey.set(conversationKey, mode)
}

export function __resetPermissionModeStateForTests(): void {
  permissionModeByConversationKey.clear()
}
