import React, { useEffect, useState } from 'react'
import { CACHE_PATHS } from '@utils/log'
import { LogSelector } from '@components/LogSelector'
import type { LogOption, LogListProps } from '@kode-types/logs'
import { loadLogList } from '@utils/log'
import { logError } from '@utils/log'

type Props = LogListProps & {
  type: 'messages' | 'errors'
  logNumber?: number
}

export function LogList({ context, type, logNumber }: Props): React.ReactNode {
  const [logs, setLogs] = useState<LogOption[]>([])
  const [didSelectLog, setDidSelectLog] = useState(false)

  useEffect(() => {
    loadLogList(
      type === 'messages' ? CACHE_PATHS.messages() : CACHE_PATHS.errors(),
    )
      .then(logs => {
        if (logNumber !== undefined) {
          const log = logs[logNumber >= 0 ? logNumber : 0]
          if (log) {
            console.log(JSON.stringify(log.messages, null, 2))
            process.exit(0)
          } else {
            console.error('No log found at index', logNumber)
            process.exit(1)
          }
        }

        setLogs(logs)
      })
      .catch(error => {
        logError(error)
        if (logNumber !== undefined) {
          process.exit(1)
        } else {
          context.unmount?.()
        }
      })
  }, [context, type, logNumber])

  function onSelect(index: number): void {
    const log = logs[index]
    if (!log) {
      return
    }
    setDidSelectLog(true)
    setTimeout(() => {
      console.log(JSON.stringify(log.messages, null, 2))
      process.exit(0)
    }, 100)
  }

  if (logNumber !== undefined) {
    return null
  }

  if (didSelectLog) {
    return null
  }

  return <LogSelector logs={logs} onSelect={onSelect} />
}
