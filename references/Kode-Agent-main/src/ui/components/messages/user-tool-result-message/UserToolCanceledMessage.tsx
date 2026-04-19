import { Text } from 'ink'
import * as React from 'react'
import { getTheme } from '@utils/theme'

export function UserToolCanceledMessage(): React.ReactNode {
  return (
    <Text>
      &nbsp;&nbsp;⎿ &nbsp;
      <Text color={getTheme().error}>Interrupted by user</Text>
    </Text>
  )
}
