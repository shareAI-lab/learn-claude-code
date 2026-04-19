import React from 'react'
import { AgentsUI } from './agents/ui'

export default {
  name: 'agents',
  description: 'Manage agent configurations',
  type: 'local-jsx' as const,
  isEnabled: true,
  isHidden: false,

  async call(onExit: (message?: string) => void) {
    return <AgentsUI onExit={onExit} />
  },

  userFacingName() {
    return 'agents'
  },
}
