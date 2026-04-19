// Permission mode types retained for compatibility with earlier agent implementations
export type PermissionMode =
  | 'default'
  | 'acceptEdits'
  | 'plan'
  | 'bypassPermissions'

export interface PermissionContext {
  mode: PermissionMode
  allowedTools: string[]
  allowedPaths: string[]
  restrictions: {
    readOnly: boolean
    requireConfirmation: boolean
    bypassValidation: boolean
  }
  metadata: {
    activatedAt?: string
    previousMode?: PermissionMode
    transitionCount: number
  }
}

export interface ModeConfig {
  name: PermissionMode
  label: string
  icon: string
  color: string
  description: string
  allowedTools: string[]
  restrictions: {
    readOnly: boolean
    requireConfirmation: boolean
    bypassValidation: boolean
  }
}

// Mode configuration preserved for Claude Code parity
export const MODE_CONFIGS: Record<PermissionMode, ModeConfig> = {
  default: {
    name: 'default',
    label: 'DEFAULT',
    icon: '🔒',
    color: 'blue',
    description: 'Standard permission checking',
    allowedTools: ['*'],
    restrictions: {
      readOnly: false,
      requireConfirmation: true,
      bypassValidation: false,
    },
  },
  acceptEdits: {
    name: 'acceptEdits',
    label: 'ACCEPT EDITS',
    icon: '✅',
    color: 'green',
    description: 'Auto-approve edit operations',
    allowedTools: ['*'],
    restrictions: {
      readOnly: false,
      requireConfirmation: false,
      bypassValidation: false,
    },
  },
  plan: {
    name: 'plan',
    label: 'PLAN MODE',
    icon: '📝',
    color: 'yellow',
    description: 'Research and planning - read-only tools only',
    allowedTools: [
      'Read',
      'Grep',
      'Glob',
      'LS',
      'WebSearch',
      'WebFetch',
      'NotebookRead',
      'exit_plan_mode',
    ],
    restrictions: {
      readOnly: true,
      requireConfirmation: true,
      bypassValidation: false,
    },
  },
  bypassPermissions: {
    name: 'bypassPermissions',
    label: 'BYPASS PERMISSIONS',
    icon: '🔓',
    color: 'red',
    description: 'All permissions bypassed',
    allowedTools: ['*'],
    restrictions: {
      readOnly: false,
      requireConfirmation: false,
      bypassValidation: true,
    },
  },
}

// Mode cycling function preserved from the Claude Code workflow
export function getNextPermissionMode(
  currentMode: PermissionMode,
  isBypassAvailable: boolean = true,
): PermissionMode {
  switch (currentMode) {
    case 'default':
      return 'acceptEdits'
    case 'acceptEdits':
      return 'plan'
    case 'plan':
      return isBypassAvailable ? 'bypassPermissions' : 'default'
    case 'bypassPermissions':
      return 'default'
    default:
      return 'default'
  }
}
