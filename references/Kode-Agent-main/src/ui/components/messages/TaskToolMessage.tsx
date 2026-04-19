import React, { useEffect, useState, useMemo } from 'react'
import { Text } from 'ink'
import { getAgentByType } from '@utils/agent/loader'
import { getTheme } from '@utils/theme'

interface Props {
  agentType: string
  children: React.ReactNode
  bold?: boolean
}

const agentConfigCache = new Map<string, any>()

export function TaskToolMessage({ agentType, children, bold = true }: Props) {
  const theme = getTheme()
  const [agentConfig, setAgentConfig] = useState<any>(() => {
    return agentConfigCache.get(agentType) || null
  })

  useEffect(() => {
    if (agentConfigCache.has(agentType)) {
      setAgentConfig(agentConfigCache.get(agentType))
      return
    }

    let mounted = true
    getAgentByType(agentType)
      .then(config => {
        if (mounted) {
          agentConfigCache.set(agentType, config)
          setAgentConfig(config)
        }
      })
      .catch(() => {
        if (mounted) {
          agentConfigCache.set(agentType, null)
        }
      })

    return () => {
      mounted = false
    }
  }, [agentType])

  const color = useMemo(() => {
    return agentConfig?.color || theme.text
  }, [agentConfig?.color, theme.text])

  return (
    <Text color={color} bold={bold}>
      {children}
    </Text>
  )
}
