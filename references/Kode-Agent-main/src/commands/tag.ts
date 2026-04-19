import { Command } from '@commands'
import { getKodeAgentSessionId } from '@utils/protocol/kodeAgentSessionId'
import { appendSessionTagRecord } from '@utils/protocol/kodeAgentSessionLog'

const tag = {
  type: 'local',
  name: 'tag',
  description: 'Set a tag for the current session',
  isEnabled: true,
  isHidden: false,
  userFacingName() {
    return 'tag'
  },
  async call(args, _context) {
    const value = args.trim()
    if (!value) return 'Usage: /tag <tag>'

    appendSessionTagRecord({
      sessionId: getKodeAgentSessionId(),
      tag: value,
    })

    return `Session tagged as: ${value}`
  },
} satisfies Command

export default tag
