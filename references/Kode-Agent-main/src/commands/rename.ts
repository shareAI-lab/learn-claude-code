import { Command } from '@commands'
import { getKodeAgentSessionId } from '@utils/protocol/kodeAgentSessionId'
import { appendSessionCustomTitleRecord } from '@utils/protocol/kodeAgentSessionLog'

const rename = {
  type: 'local',
  name: 'rename',
  description: 'Set a custom title for the current session',
  isEnabled: true,
  isHidden: false,
  userFacingName() {
    return 'rename'
  },
  async call(args, _context) {
    const customTitle = args.trim()
    if (!customTitle) return 'Usage: /rename <title>'

    appendSessionCustomTitleRecord({
      sessionId: getKodeAgentSessionId(),
      customTitle,
    })

    return `Session renamed to: ${customTitle}`
  },
} satisfies Command

export default rename
