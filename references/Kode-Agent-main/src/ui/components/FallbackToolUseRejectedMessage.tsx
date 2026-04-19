import * as React from 'react'
import { getTheme } from '@utils/theme'
import { Text } from 'ink'
import { PRODUCT_NAME } from '@constants/product'

export function FallbackToolUseRejectedMessage(): React.ReactNode {
  return (
    <Text>
      &nbsp;&nbsp;⎿ &nbsp;
      <Text color={getTheme().error}>
        No (tell {PRODUCT_NAME} what to do differently)
      </Text>
    </Text>
  )
}
