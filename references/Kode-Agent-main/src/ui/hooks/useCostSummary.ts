import { useEffect } from 'react'
import {
  formatTotalCost,
  getTotalAPIDuration,
  getTotalCost,
  getTotalDuration,
} from '@costTracker'
import {
  getCurrentProjectConfig,
  saveCurrentProjectConfig,
} from '@utils/config'
import { SESSION_ID } from '@utils/log'

export function useCostSummary(): void {
  useEffect(() => {
    const onExit = () => {
      process.stdout.write('\n' + formatTotalCost() + '\n')

      const projectConfig = getCurrentProjectConfig()
      saveCurrentProjectConfig({
        ...projectConfig,
        lastCost: getTotalCost(),
        lastAPIDuration: getTotalAPIDuration(),
        lastDuration: getTotalDuration(),
        lastSessionId: SESSION_ID,
      })
    }

    process.on('exit', onExit)
    return () => {
      process.off('exit', onExit)
    }
  }, [])
}
