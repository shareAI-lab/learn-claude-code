import type {
  ToolPermissionContext,
  ToolPermissionContextUpdate,
} from '@kode-types/toolPermissionContext'
import { applyToolPermissionContextUpdate } from '@kode-types/toolPermissionContext'
import { loadToolPermissionContextFromDisk } from '@utils/permissions/toolPermissionSettings'

const toolPermissionContextByConversationKey = new Map<
  string,
  ToolPermissionContext
>()

export function getToolPermissionContextForConversationKey(options: {
  conversationKey: string
  isBypassPermissionsModeAvailable: boolean
}): ToolPermissionContext {
  const existing = toolPermissionContextByConversationKey.get(
    options.conversationKey,
  )
  if (existing) {
    let next = existing

    if (
      next.isBypassPermissionsModeAvailable !==
      options.isBypassPermissionsModeAvailable
    ) {
      next = {
        ...next,
        isBypassPermissionsModeAvailable:
          options.isBypassPermissionsModeAvailable,
      }
    }

    if (
      !options.isBypassPermissionsModeAvailable &&
      next.mode === 'bypassPermissions'
    ) {
      next = { ...next, mode: 'default' }
    }

    if (next !== existing) {
      toolPermissionContextByConversationKey.set(options.conversationKey, next)
    }

    return next
  }

  const initial = loadToolPermissionContextFromDisk({
    isBypassPermissionsModeAvailable: options.isBypassPermissionsModeAvailable,
  })
  toolPermissionContextByConversationKey.set(options.conversationKey, initial)
  return initial
}

export function setToolPermissionContextForConversationKey(options: {
  conversationKey: string
  context: ToolPermissionContext
}): void {
  toolPermissionContextByConversationKey.set(
    options.conversationKey,
    options.context,
  )
}

export function applyToolPermissionContextUpdateForConversationKey(options: {
  conversationKey: string
  isBypassPermissionsModeAvailable: boolean
  update: ToolPermissionContextUpdate
}): ToolPermissionContext {
  const prev = getToolPermissionContextForConversationKey({
    conversationKey: options.conversationKey,
    isBypassPermissionsModeAvailable: options.isBypassPermissionsModeAvailable,
  })
  const next = applyToolPermissionContextUpdate(prev, options.update)
  toolPermissionContextByConversationKey.set(options.conversationKey, next)
  return next
}

export function __resetToolPermissionContextStateForTests(): void {
  toolPermissionContextByConversationKey.clear()
}
