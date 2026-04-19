import { Box, Text } from 'ink'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { getTheme } from '@utils/theme'
import {
  getRequestStatus,
  subscribeRequestStatus,
  type RequestStatus,
} from '@utils/session/requestStatus'

const CHARACTERS =
  process.platform === 'darwin'
    ? ['·', '✢', '✳', '∗', '✻', '✽']
    : ['·', '✢', '*', '∗', '✻', '✽']

function getLabel(status: RequestStatus): string {
  switch (status.kind) {
    case 'thinking':
      return 'Thinking'
    case 'streaming':
      return 'Streaming'
    case 'tool':
      return status.detail ? `Running tool: ${status.detail}` : 'Running tool'
    case 'idle':
      return 'Working'
  }
}

export function RequestStatusIndicator(): React.ReactNode {
  const frames = useMemo(
    () => [...CHARACTERS, ...[...CHARACTERS].reverse()],
    [],
  )
  const theme = getTheme()

  const [frame, setFrame] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [status, setStatus] = useState<RequestStatus>(() => getRequestStatus())

  const requestStartTime = useRef<number | null>(null)

  useEffect(() => {
    return subscribeRequestStatus(next => {
      setStatus(next)
      if (next.kind !== 'idle' && requestStartTime.current === null) {
        requestStartTime.current = Date.now()
      }
      if (next.kind === 'idle') {
        requestStartTime.current = null
        setElapsedTime(0)
      }
    })
  }, [])

  useEffect(() => {
    const timer = setInterval(() => {
      setFrame(f => (f + 1) % frames.length)
    }, 120)
    return () => clearInterval(timer)
  }, [frames.length])

  useEffect(() => {
    const timer = setInterval(() => {
      if (requestStartTime.current === null) {
        setElapsedTime(0)
        return
      }
      setElapsedTime(Math.floor((Date.now() - requestStartTime.current) / 1000))
    }, 250)
    return () => clearInterval(timer)
  }, [])

  return (
    <Box flexDirection="row" marginTop={1}>
      <Box flexWrap="nowrap" height={1} width={2}>
        <Text color={theme.kode}>{frames[frame]}</Text>
      </Box>
      <Text color={theme.kode}>{getLabel(status)}… </Text>
      <Text color={theme.secondaryText}>
        ({elapsedTime}s · <Text bold>esc</Text> to interrupt)
      </Text>
    </Box>
  )
}
