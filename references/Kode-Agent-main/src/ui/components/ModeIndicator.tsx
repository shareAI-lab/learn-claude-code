import React from 'react'
import { Box, Text } from 'ink'
import { usePermissionContext } from '@context/PermissionContext'
import { getTheme, type Theme } from '@utils/theme'
import { getPermissionModeCycleShortcut } from '@utils/terminal/permissionModeCycleShortcut'
import type { PermissionMode } from '@kode-types/permissionMode'

interface ModeIndicatorProps {
  showTransitionCount?: boolean
}

export function ModeIndicator({
  showTransitionCount = false,
}: ModeIndicatorProps) {
  const { currentMode, permissionContext } = usePermissionContext()
  const theme = getTheme()
  const shortcut = getPermissionModeCycleShortcut()

  if (currentMode === 'default' && !showTransitionCount) {
    return null
  }

  const indicator = __getModeIndicatorDisplayForTests({
    mode: currentMode,
    shortcutDisplayText: shortcut.displayText,
    theme,
  })

  return (
    <Box flexDirection="row" justifyContent="space-between" width="100%">
      <Text color={indicator.color}>
        {indicator.mainText}
        {indicator.shortcutHintText ? (
          <Text dimColor>{indicator.shortcutHintText}</Text>
        ) : null}
      </Text>
      {showTransitionCount && (
        <Text color="gray" dimColor>
          Switches: {permissionContext.metadata.transitionCount}
        </Text>
      )}
    </Box>
  )
}

export function __getModeIndicatorDisplayForTests(args: {
  mode: PermissionMode
  shortcutDisplayText: string
  theme: Theme
}): {
  shouldRender: boolean
  color: string
  mainText: string
  shortcutHintText: string
} {
  if (args.mode === 'default') {
    return {
      shouldRender: false,
      color: args.theme.text,
      mainText: '',
      shortcutHintText: '',
    }
  }

  const icon = getModeIndicatorIcon(args.mode)
  const label = getModeIndicatorLabel(args.mode).toLowerCase()
  const color = getModeIndicatorColor(args.theme, args.mode)

  return {
    shouldRender: true,
    color,
    mainText: `${icon} ${label} on`,
    shortcutHintText: ` (${args.shortcutDisplayText} to cycle)`,
  }
}

function getModeIndicatorLabel(mode: PermissionMode): string {
  switch (mode) {
    case 'default':
      return 'Default'
    case 'plan':
      return 'Plan Mode'
    case 'acceptEdits':
      return 'Accept edits'
    case 'bypassPermissions':
      return 'Bypass Permissions'
    case 'dontAsk':
      return "Don't Ask"
  }
}

function getModeIndicatorIcon(mode: PermissionMode): string {
  switch (mode) {
    case 'default':
      return ''
    case 'plan':
      return '⏸'
    case 'acceptEdits':
    case 'bypassPermissions':
    case 'dontAsk':
      return '⏵⏵'
  }
}

function getModeIndicatorColor(theme: Theme, mode: PermissionMode): string {
  switch (mode) {
    case 'default':
      return theme.text
    case 'plan':
      return theme.planMode
    case 'acceptEdits':
      return theme.autoAccept
    case 'bypassPermissions':
    case 'dontAsk':
      return theme.error
  }
}

export function CompactModeIndicator() {
  const { currentMode } = usePermissionContext()
  const theme = getTheme()
  const shortcut = getPermissionModeCycleShortcut()

  if (currentMode === 'default') {
    return null
  }

  const indicator = __getModeIndicatorDisplayForTests({
    mode: currentMode,
    shortcutDisplayText: shortcut.displayText,
    theme,
  })

  return (
    <Text color={indicator.color}>
      {indicator.mainText}
      <Text dimColor>{indicator.shortcutHintText}</Text>
    </Text>
  )
}
