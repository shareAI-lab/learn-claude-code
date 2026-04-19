import type { Command } from '@commands'
import { formatTotalCost } from '@costTracker'

const cost = {
  type: 'local',
  name: 'cost',
  description: 'Show the total cost and duration of the current session',
  isEnabled: true,
  isHidden: false,
  async call() {
    return formatTotalCost()
  },
  userFacingName() {
    return 'cost'
  },
} satisfies Command

export default cost
