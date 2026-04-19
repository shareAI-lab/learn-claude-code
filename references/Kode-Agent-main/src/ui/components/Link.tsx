import InkLink from 'ink-link'
import { Text } from 'ink'
import React from 'react'
import { env } from '@utils/config/env'

type LinkProps = {
  url: string
  children?: React.ReactNode
}

const LINK_SUPPORTING_TERMINALS = ['iTerm.app', 'WezTerm', 'Hyper', 'VSCode']

export default function Link({ url, children }: LinkProps): React.ReactNode {
  const supportsLinks = LINK_SUPPORTING_TERMINALS.includes(env.terminal ?? '')

  const displayContent = children || url

  if (supportsLinks || displayContent !== url) {
    return (
      <InkLink url={url}>
        <Text>{displayContent}</Text>
      </InkLink>
    )
  } else {
    return <Text underline>{displayContent}</Text>
  }
}
