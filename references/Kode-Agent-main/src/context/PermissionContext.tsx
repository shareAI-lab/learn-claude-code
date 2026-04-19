import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  ReactNode,
} from 'react'
import {
  PermissionMode,
  PermissionContext as IPermissionContext,
  getNextPermissionMode,
  MODE_CONFIGS,
} from '@kode-types/permissionMode'
import {
  getPermissionModeForConversationKey,
  setPermissionModeForConversationKey,
} from '@utils/permissions/permissionModeState'
import type {
  ToolPermissionContext as IToolPermissionContext,
  ToolPermissionContextUpdate,
} from '@kode-types/toolPermissionContext'
import { applyToolPermissionContextUpdate } from '@kode-types/toolPermissionContext'
import {
  applyToolPermissionContextUpdateForConversationKey,
  getToolPermissionContextForConversationKey,
  setToolPermissionContextForConversationKey,
} from '@utils/permissions/toolPermissionContextState'
import {
  enterPlanModeForConversationKey,
  exitPlanModeForConversationKey,
  setActivePlanConversationKey,
} from '@utils/plan/planMode'
import { getGlobalConfig, saveGlobalConfig } from '@utils/config'

interface PermissionContextValue {
  permissionContext: IPermissionContext
  toolPermissionContext: IToolPermissionContext
  currentMode: PermissionMode
  conversationKey: string
  cycleMode: () => void
  setMode: (mode: PermissionMode) => void
  applyToolPermissionUpdate: (update: ToolPermissionContextUpdate) => void
  isToolAllowed: (toolName: string) => boolean
  getModeConfig: () => (typeof MODE_CONFIGS)[PermissionMode]
}

const PermissionContext = createContext<PermissionContextValue | undefined>(
  undefined,
)

interface PermissionProviderProps {
  children?: ReactNode
  conversationKey: string
  isBypassPermissionsModeAvailable?: boolean
}

export function __applyPermissionModeSideEffectsForTests(args: {
  conversationKey: string
  previousMode: PermissionMode
  nextMode: PermissionMode
  recordPlanModeUse: boolean
  now?: () => number
}): void {
  const now = args.now ?? Date.now

  if (
    args.recordPlanModeUse &&
    args.previousMode !== args.nextMode &&
    args.nextMode === 'plan'
  ) {
    const config = getGlobalConfig()
    saveGlobalConfig({ ...(config as any), lastPlanModeUse: now() })
  }

  setPermissionModeForConversationKey({
    conversationKey: args.conversationKey,
    mode: args.nextMode,
  })

  if (args.previousMode !== 'plan' && args.nextMode === 'plan') {
    enterPlanModeForConversationKey(args.conversationKey)
  } else if (args.previousMode === 'plan' && args.nextMode !== 'plan') {
    exitPlanModeForConversationKey(args.conversationKey)
  }
}

export function PermissionProvider({
  children,
  conversationKey,
  isBypassPermissionsModeAvailable = false,
}: PermissionProviderProps) {
  const [toolPermissionContext, setToolPermissionContext] =
    useState<IToolPermissionContext>(() =>
      getToolPermissionContextForConversationKey({
        conversationKey,
        isBypassPermissionsModeAvailable,
      }),
    )
  const [permissionContext, setPermissionContext] =
    useState<IPermissionContext>(() => {
      const initialMode = getToolPermissionContextForConversationKey({
        conversationKey,
        isBypassPermissionsModeAvailable,
      }).mode
      const initialConfig = MODE_CONFIGS[initialMode]
      return {
        mode: initialMode,
        allowedTools: initialConfig.allowedTools,
        allowedPaths: [process.cwd()],
        restrictions: initialConfig.restrictions,
        metadata: {
          transitionCount: 0,
        },
      }
    })

  useEffect(() => {
    const toolCtx = getToolPermissionContextForConversationKey({
      conversationKey,
      isBypassPermissionsModeAvailable,
    })
    setToolPermissionContext(toolCtx)
    const config = MODE_CONFIGS[toolCtx.mode]
    setPermissionContext({
      mode: toolCtx.mode,
      allowedTools: config.allowedTools,
      allowedPaths: [process.cwd()],
      restrictions: config.restrictions,
      metadata: {
        transitionCount: 0,
      },
    })
  }, [conversationKey, isBypassPermissionsModeAvailable])

  useEffect(() => {
    setActivePlanConversationKey(conversationKey)
    if (permissionContext.mode === 'plan') {
      enterPlanModeForConversationKey(conversationKey)
    }
  }, [conversationKey, permissionContext.mode])

  const cycleMode = useCallback(() => {
    setPermissionContext(prev => {
      const nextMode = getNextPermissionMode(
        prev.mode,
        isBypassPermissionsModeAvailable,
      )
      const modeConfig = MODE_CONFIGS[nextMode]

      __applyPermissionModeSideEffectsForTests({
        conversationKey,
        previousMode: prev.mode,
        nextMode,
        recordPlanModeUse: true,
      })

      const updatedToolPermissionContext =
        applyToolPermissionContextUpdateForConversationKey({
          conversationKey,
          isBypassPermissionsModeAvailable,
          update: { type: 'setMode', mode: nextMode, destination: 'session' },
        })
      setToolPermissionContext(updatedToolPermissionContext)

      return {
        ...prev,
        mode: nextMode,
        allowedTools: modeConfig.allowedTools,
        restrictions: modeConfig.restrictions,
        metadata: {
          ...prev.metadata,
          previousMode: prev.mode,
          activatedAt: new Date().toISOString(),
          transitionCount: prev.metadata.transitionCount + 1,
        },
      }
    })
  }, [conversationKey, isBypassPermissionsModeAvailable])

  const setMode = useCallback(
    (mode: PermissionMode) => {
      setPermissionContext(prev => {
        const modeConfig = MODE_CONFIGS[mode]

        __applyPermissionModeSideEffectsForTests({
          conversationKey,
          previousMode: prev.mode,
          nextMode: mode,
          recordPlanModeUse: false,
        })

        const updatedToolPermissionContext =
          applyToolPermissionContextUpdateForConversationKey({
            conversationKey,
            isBypassPermissionsModeAvailable,
            update: { type: 'setMode', mode, destination: 'session' },
          })
        setToolPermissionContext(updatedToolPermissionContext)

        return {
          ...prev,
          mode,
          allowedTools: modeConfig.allowedTools,
          restrictions: modeConfig.restrictions,
          metadata: {
            ...prev.metadata,
            previousMode: prev.mode,
            activatedAt: new Date().toISOString(),
            transitionCount: prev.metadata.transitionCount + 1,
          },
        }
      })
    },
    [conversationKey],
  )

  const applyToolPermissionUpdate = useCallback(
    (update: ToolPermissionContextUpdate) => {
      setToolPermissionContext(prev => {
        const next = applyToolPermissionContextUpdate(prev, update)
        setToolPermissionContextForConversationKey({
          conversationKey,
          context: next,
        })
        return next
      })

      if (update.type === 'setMode') {
        setPermissionContext(prev => {
          const modeConfig = MODE_CONFIGS[update.mode]

          __applyPermissionModeSideEffectsForTests({
            conversationKey,
            previousMode: prev.mode,
            nextMode: update.mode,
            recordPlanModeUse: false,
          })

          return {
            ...prev,
            mode: update.mode,
            allowedTools: modeConfig.allowedTools,
            restrictions: modeConfig.restrictions,
            metadata: {
              ...prev.metadata,
              previousMode: prev.mode,
              activatedAt: new Date().toISOString(),
              transitionCount: prev.metadata.transitionCount + 1,
            },
          }
        })
      }
    },
    [conversationKey],
  )

  const isToolAllowed = useCallback(
    (toolName: string) => {
      const { allowedTools } = permissionContext

      if (allowedTools.includes('*')) {
        return true
      }

      return allowedTools.includes(toolName)
    },
    [permissionContext],
  )

  const getModeConfig = useCallback(() => {
    return MODE_CONFIGS[permissionContext.mode]
  }, [permissionContext.mode])

  const value: PermissionContextValue = {
    permissionContext,
    toolPermissionContext,
    currentMode: permissionContext.mode,
    conversationKey,
    cycleMode,
    setMode,
    applyToolPermissionUpdate,
    isToolAllowed,
    getModeConfig,
  }

  return (
    <PermissionContext.Provider value={value}>
      {children}
    </PermissionContext.Provider>
  )
}

export function usePermissionContext(): PermissionContextValue {
  const context = useContext(PermissionContext)
  if (context === undefined) {
    throw new Error(
      'usePermissionContext must be used within a PermissionProvider',
    )
  }
  return context
}

export function usePermissionMode(): [
  PermissionMode,
  (mode: PermissionMode) => void,
  () => void,
] {
  const { currentMode, setMode, cycleMode } = usePermissionContext()
  return [currentMode, setMode, cycleMode]
}
