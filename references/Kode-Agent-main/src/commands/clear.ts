import { Command } from '@commands'
import { getMessagesSetter } from '@messages'
import { getContext } from '@context'
import { getCodeStyle } from '@utils/config/style'
import { clearTerminal } from '@utils/terminal'
import { getOriginalCwd, setCwd } from '@utils/state'
import { Message } from '@query'
import { resetReminderSession } from '@services/systemReminder'
import { resetFileFreshnessSession } from '@services/fileFreshness'

export async function clearConversation(context: {
  setForkConvoWithMessagesOnTheNextRender: (
    forkConvoWithMessages: Message[],
  ) => void
}) {
  await clearTerminal()
  getMessagesSetter()([])
  context.setForkConvoWithMessagesOnTheNextRender([])
  getContext.cache.clear?.()
  getCodeStyle.cache.clear?.()
  await setCwd(getOriginalCwd())

  resetReminderSession()
  resetFileFreshnessSession()
}

const clear = {
  type: 'local',
  name: 'clear',
  description: 'Clear conversation history and free up context',
  isEnabled: true,
  isHidden: false,
  async call(_, context) {
    clearConversation(context)
    return ''
  },
  userFacingName() {
    return 'clear'
  },
} satisfies Command

export default clear
