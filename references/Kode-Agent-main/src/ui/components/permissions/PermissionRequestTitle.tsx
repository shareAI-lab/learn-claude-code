import * as React from 'react'
import { Box, Text } from 'ink'
import { getTheme } from '@utils/theme'

export type RiskScoreCategory = 'low' | 'moderate' | 'high'

export function categoryForRiskScore(riskScore: number): RiskScoreCategory {
  return riskScore >= 70 ? 'high' : riskScore >= 30 ? 'moderate' : 'low'
}

function colorSchemeForRiskScoreCategory(category: RiskScoreCategory): {
  highlightColor: string
  textColor: string
} {
  const theme = getTheme()
  switch (category) {
    case 'low':
      return {
        highlightColor: theme.success,
        textColor: theme.permission,
      }
    case 'moderate':
      return {
        highlightColor: theme.warning,
        textColor: theme.warning,
      }
    case 'high':
      return {
        highlightColor: theme.error,
        textColor: theme.error,
      }
  }
}

export function textColorForRiskScore(riskScore: number | null): string {
  if (riskScore === null) {
    return getTheme().permission
  }
  const category = categoryForRiskScore(riskScore)
  return colorSchemeForRiskScoreCategory(category).textColor
}

export function PermissionRiskScore({
  riskScore,
}: {
  riskScore: number
}): React.ReactNode {
  const category = categoryForRiskScore(riskScore)
  return <Text color={textColorForRiskScore(riskScore)}>Risk: {category}</Text>
}

type Props = {
  title: string
  riskScore: number | null
}

export function PermissionRequestTitle({
  title,
  riskScore,
}: Props): React.ReactNode {
  return (
    <Box flexDirection="column">
      <Text bold color={getTheme().permission}>
        {title}
      </Text>
      {riskScore !== null && <PermissionRiskScore riskScore={riskScore} />}
    </Box>
  )
}
