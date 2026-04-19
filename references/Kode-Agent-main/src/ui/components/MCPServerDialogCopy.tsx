import React from 'react'
import { Text } from 'ink'
import Link from 'ink-link'
import { PRODUCT_NAME, PRODUCT_COMMAND } from '@constants/product'

export function MCPServerDialogCopy(): React.ReactNode {
  return (
    <>
      <Text>
        MCP servers provide additional functionality to {PRODUCT_NAME}. They may
        execute code, make network requests, or access system resources via tool
        calls. All tool calls will require your explicit approval before
        execution. For more information, see{' '}
        <Link url="https://github.com/shareAI-lab/kode/blob/main/docs/mcp.md">
          MCP documentation
        </Link>
      </Text>

      <Text dimColor>
        Remember: You can always change these choices later by running `
        {PRODUCT_COMMAND} mcp reset-project-choices`
      </Text>
    </>
  )
}
